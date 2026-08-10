"""Local-first chatbot API with deterministic answers and Ollama streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.services.chat_auth import (
    ChatSession,
    RateLimitError,
    SessionBackendError,
    SessionError,
    create_session,
    enforce_rate_limit,
    local_access_enabled,
    revoke_session,
    verify_session,
)
from api.services.entra_auth import EntraIdentity, require_entra_identity
from api.services.chat_guardrails import (
    GuardrailDecision,
    guard_model_output,
    guard_user_message,
)
from api.services.deterministic_chat import DeterministicAnswer, answer_deterministically
from api.services.llm_provider import build_llm_provider
from api.services.ollama_provider import GenerationResult, ProviderError, SYSTEM_PROMPT_VERSION
from api.services.operational_context import build_operational_context
from api.services.chat_cache import context_fingerprint, response_cache, response_cache_key
from api.services.chat_runtime import (
    chat_observability,
    conversation_memory,
    feedback_registry,
    identity_namespace,
)
from api.services.conversation_store import ConversationNotFound, conversation_store

router = APIRouter(prefix="/chat", tags=["Chatbot"])
provider = build_llm_provider()
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


DashboardFilterKey = Annotated[str, Field(min_length=1, max_length=48)]
DashboardFilterValue = Annotated[str, Field(max_length=120)]


class DashboardContextSnapshot(BaseModel):
    route: Literal["/gestao", "/monitoramento", "/tecnico", "/modelos"] = "/gestao"
    label: str = Field(default="GESTÃO", min_length=1, max_length=64)
    filters: dict[DashboardFilterKey, DashboardFilterValue] = Field(
        default_factory=dict,
        max_length=8,
    )


class ChatRequest(BaseModel):
    # Integrated board-level analyses are naturally longer than a quick chat
    # question. Keep an explicit ceiling to limit context flooding while
    # allowing a complete, structured request.
    message: str = Field(min_length=1, max_length=6000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    conversation_id: str = Field(default="", max_length=64, pattern=r"^[A-Za-z0-9_-]*$")
    analysis_mode: Literal["fast", "deep"] = "fast"
    dashboard_context: DashboardContextSnapshot | None = None


class ChatResponse(BaseModel):
    reply: str
    reasoning: str | None = None
    elapsed_ms: int
    mode: Literal["deterministic", "llm"]
    provider: str
    model: str | None = None
    badge: dict[str, str] | None = None
    action: dict[str, str] | None = None
    suggestions: list[str] = Field(default_factory=list)
    used_pro: bool = False
    response_id: str
    analysis_mode: Literal["fast", "deep"] = "fast"
    sources: list[dict[str, str]] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    cache: dict[str, Any] = Field(default_factory=dict)


class FeedbackRequest(BaseModel):
    response_id: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    rating: Literal["up", "down"]
    reason: str = Field(default="", max_length=240)


class ConversationResetRequest(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class ConversationCreateRequest(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    dashboard_context: DashboardContextSnapshot | None = None


class ConversationUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    pinned: bool | None = None
    dashboard_context: DashboardContextSnapshot | None = None


def _session_from_header(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> ChatSession:
    # The global API middleware already verified this request. Reusing its
    # result avoids a second authorization-database lookup per route.
    existing = getattr(request.state, "session", None)
    if isinstance(existing, ChatSession):
        return existing
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sessão do chatbot ausente.")
    try:
        return verify_session(authorization.split(" ", 1)[1].strip())
    except SessionBackendError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SessionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _history(req: ChatRequest) -> list[dict[str, str]]:
    """Bound client-supplied context so it cannot crowd out the official prompt."""
    remaining = 6_000
    selected: list[dict[str, str]] = []
    for item in reversed(req.history[-4:]):
        if remaining <= 0:
            break
        content = item.content[:remaining]
        selected.append({"role": item.role, "content": content})
        remaining -= len(content)
    return list(reversed(selected))


def _bound_history(items: list[dict[str, str]]) -> list[dict[str, str]]:
    remaining = 8_000
    candidates = items[-6:]
    if len(items) > 6 and str(items[0].get("content", "")).startswith("Resumo automático"):
        candidates = [items[0], *items[-5:]]
    selected: list[dict[str, str]] = []
    for item in reversed(candidates):
        if remaining <= 0:
            break
        content = str(item.get("content", ""))[:remaining]
        role = str(item.get("role", ""))
        if content and role in {"user", "assistant"}:
            selected.append({"role": role, "content": content})
            remaining -= len(content)
    return list(reversed(selected))


async def _request_history(req: ChatRequest, session: ChatSession) -> list[dict[str, str]]:
    namespace = identity_namespace(session.tenant_id, session.object_id)
    if req.conversation_id:
        archived = await asyncio.to_thread(conversation_store.history, namespace, req.conversation_id)
        if archived:
            return _bound_history(archived)
        stored = await conversation_memory.get(
            namespace,
            req.conversation_id,
        )
        if stored:
            return _bound_history(stored)
    return _history(req)


def _dashboard_context(req: ChatRequest) -> dict[str, Any] | None:
    if req.dashboard_context is None:
        return None
    return req.dashboard_context.model_dump()


async def _context_for_request(
    req: ChatRequest,
    session: ChatSession,
    context: dict[str, Any],
) -> dict[str, Any]:
    interface_state = _dashboard_context(req)
    if interface_state is None and req.conversation_id:
        namespace = identity_namespace(session.tenant_id, session.object_id)
        try:
            archived = await asyncio.to_thread(
                conversation_store.get,
                namespace,
                req.conversation_id,
            )
            interface_state = archived.get("dashboard_context")
        except ConversationNotFound:
            pass
    if not interface_state:
        return context
    return {**context, "interface_state": interface_state}


def _deterministic_reasoning() -> str:
    return (
        "Roteamento: consulta factual reconhecida. Fonte: snapshot canônico dos artefatos locais. "
        "Checagem: valores retornados sem geração ou interpretação de LLM."
    )


def _answer_payload(
    answer: DeterministicAnswer,
    elapsed_ms: int,
    reasoning: str | None = None,
    *,
    response_id: str,
    analysis_mode: Literal["fast", "deep"] = "fast",
) -> dict:
    return {
        "reply": answer.reply,
        "reasoning": reasoning or _deterministic_reasoning(),
        "elapsed_ms": elapsed_ms,
        "mode": "deterministic",
        "provider": "outputs",
        "model": None,
        "badge": answer.badge or None,
        "action": answer.action,
        "suggestions": answer.suggestions,
        "used_pro": False,
        "response_id": response_id,
        "analysis_mode": analysis_mode,
        "sources": [{
            "id": "versioned_outputs",
            "label": "Artefatos operacionais versionados",
            "kind": "official_snapshot",
        }],
        "usage": {},
        "cache": {"hit": False, "kind": "bypass"},
    }


def _guardrail_answer(decision: GuardrailDecision) -> DeterministicAnswer:
    return DeterministicAnswer(
        reply=decision.reply,
        badge={"label": "ESCOPO PROTEGIDO", "tone": "purple"},
        suggestions=["Status das metas", "Cluster mais crítico", "Fatores de risco"],
    )


def _guardrail_reasoning(decision: GuardrailDecision) -> str:
    return (
        f"Proteção determinística aplicada antes do acesso ao contexto analítico. "
        f"Categoria: {decision.category}."
    )


def _provider_badge() -> dict[str, str]:
    if provider.name == "openai":
        return {"label": "GPT-5.6 LUNA", "tone": "green"}
    return {"label": "GEMMA LOCAL", "tone": "purple"}


def _event(event_type: str, **payload) -> bytes:
    return (json.dumps({"type": event_type, **payload}, ensure_ascii=False) + "\n").encode("utf-8")


def _provider_result(result: GenerationResult | tuple[str, str]) -> dict[str, Any]:
    if isinstance(result, GenerationResult):
        return {
            "reply": result.answer,
            "reasoning": result.reasoning,
            "sources": [dict(source) for source in result.sources],
            "usage": dict(result.usage or {}),
        }
    reply, reasoning = result
    return {"reply": reply, "reasoning": reasoning, "sources": [], "usage": {}}


def _cached_answer(value: dict[str, Any], kind: str) -> dict[str, Any]:
    """Do not report or count the original generation tokens on a cache hit."""
    original_usage = value.get("usage", {})
    saved_tokens = sum(
        int(original_usage.get(field, 0) or 0)
        for field in ("input_tokens", "output_tokens", "reasoning_tokens")
    )
    return {
        **value,
        "usage": {"saved_tokens": saved_tokens} if saved_tokens else {},
        "cache": {"hit": True, "kind": kind},
    }


async def _analytical_answer(
    req: ChatRequest,
    session: ChatSession,
    context: dict[str, Any],
    history: list[dict[str, str]],
) -> dict[str, Any]:
    namespace = identity_namespace(session.tenant_id, session.object_id)
    fingerprint = context_fingerprint(
        context,
        prompt_version=SYSTEM_PROMPT_VERSION,
        provider=provider.name,
        model=provider.model,
    )
    key = response_cache_key(
        namespace=namespace,
        message=req.message,
        history=history,
        analysis_mode=req.analysis_mode,
        fingerprint=fingerprint,
    )
    lookup = await response_cache.get(
        key,
        namespace=namespace,
        message=req.message,
        history=history,
        analysis_mode=req.analysis_mode,
        fingerprint=fingerprint,
    )
    if lookup:
        return _cached_answer(lookup.value, lookup.kind)

    async with response_cache.singleflight(key):
        # A matching request may have completed while this one waited.
        lookup = await response_cache.get(
            key,
            namespace=namespace,
            message=req.message,
            history=history,
            analysis_mode=req.analysis_mode,
            fingerprint=fingerprint,
            count_miss=False,
        )
        if lookup:
            return _cached_answer(lookup.value, lookup.kind)

        generated = await provider.generate(
            req.message,
            history,
            context,
            analysis_mode=req.analysis_mode,
        )
        value = _provider_result(generated)
        guarded_output = guard_model_output(value["reply"], value["reasoning"])
        if guarded_output.blocked:
            logger.warning("chat_output_blocked category=%s", guarded_output.category)
        value["reply"] = guarded_output.reply
        value["reasoning"] = guarded_output.reasoning or ""
        await response_cache.set(
            key,
            value,
            namespace=namespace,
            message=req.message,
            history=history,
            analysis_mode=req.analysis_mode,
            fingerprint=fingerprint,
        )
        return {**value, "cache": {"hit": False, "kind": "miss"}}


async def _remember_and_register(
    req: ChatRequest,
    session: ChatSession,
    response_id: str,
    payload: dict[str, Any],
) -> None:
    namespace = identity_namespace(session.tenant_id, session.object_id)
    await conversation_memory.append_exchange(
        namespace,
        req.conversation_id,
        req.message,
        str(payload["reply"]),
    )
    if req.conversation_id:
        metadata_value = {
            "reasoning": str(payload.get("reasoning") or "")[:1_200],
            "elapsed_ms": int(payload.get("elapsed_ms", 0) or 0),
            "mode": payload.get("mode", "llm"),
            "provider": payload.get("provider", provider.name),
            "model": payload.get("model"),
            "badge": payload.get("badge"),
            "action": payload.get("action"),
            "suggestions": payload.get("suggestions", []),
            "analysis_mode": req.analysis_mode,
            "sources": payload.get("sources", []),
            "usage": payload.get("usage", {}),
            "cache": payload.get("cache", {}),
        }
        try:
            await asyncio.to_thread(
                conversation_store.append_exchange,
                namespace,
                req.conversation_id,
                req.message,
                str(payload["reply"]),
                response_id=response_id,
                metadata_value=metadata_value,
                dashboard_context=_dashboard_context(req),
            )
        except Exception as exc:
            # The analytical response remains available if the optional archive fails.
            logger.error("chat_conversation_persist_failed error=%s", type(exc).__name__)
    await feedback_registry.register(response_id, namespace, {
        "mode": payload.get("mode", "llm"),
        "analysis_mode": req.analysis_mode,
        "provider": payload.get("provider", provider.name),
        "cache_kind": payload.get("cache", {}).get("kind", "bypass"),
    })


@router.post("/session")
async def start_session(
    identity: Annotated[EntraIdentity, Depends(require_entra_identity)],
):
    """Exchange a validated Entra identity for a short Predictfy session."""
    try:
        token, session = create_session(
            identity.email,
            object_id=identity.object_id,
            tenant_id=identity.tenant_id,
        )
    except SessionBackendError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SessionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        llm_status = await provider.acquire_session()
    except ProviderError as exc:
        # Factual answers remain available even when the analytical provider is unavailable.
        llm_status = {
            "available": False,
            "loaded": False,
            "provider": provider.name,
            "model": provider.model,
            "detail": str(exc),
        }

    context = build_operational_context()
    cluster_summary = context.get("clusters", {}).get("resumo", {})
    dataset = context.get("operacional", {}).get("dataset", {})
    return {
        "allowed": True,
        "email": session.email,
        "role": session.role,
        "permissions": list(session.permissions),
        "is_owner": session.is_owner,
        "token": token,
        "expires_at": session.expires_at,
        "access_mode": "local-dev" if local_access_enabled() and not session.is_owner else "entra-rbac",
        "llm_status": llm_status,
        "welcome": (
            f"SYSTEM READY. Monitorando {cluster_summary.get('n_clusters', 0)} clusters · "
            f"{dataset.get('subset_kpi_aproximado', 0):,} incidentes KPI. "
            "Contexto 2023–2025 carregado. Como posso ajudar?"
        ).replace(",", "."),
    }


@router.get("/session")
async def current_session(session: Annotated[ChatSession, Depends(_session_from_header)]):
    """Validate the current Predictfy session and return its public identity."""
    return {
        "authenticated": True,
        "email": session.email,
        "expires_at": session.expires_at,
        "role": session.role,
        "permissions": list(session.permissions),
        "is_owner": session.is_owner,
    }


@router.delete("/session")
async def end_session(session: Annotated[ChatSession, Depends(_session_from_header)]):
    """End a chat session and release provider resources when applicable."""
    try:
        await asyncio.to_thread(revoke_session, session)
    except SessionBackendError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SessionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        lifecycle = await provider.release_session()
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ended": True, "email": session.email, **lifecycle}


@router.get("/status")
async def chat_status():
    """Report whether the configured analytical provider is reachable."""
    return await provider.health()


@router.get("/metrics")
async def chat_metrics(session: Annotated[ChatSession, Depends(_session_from_header)]):
    """Return aggregate, prompt-free operational telemetry for the chatbot."""
    del session
    return {
        "runtime": chat_observability.public_stats(),
        "cache": response_cache.public_stats(),
        "memory": conversation_memory.public_stats(),
    }


@router.get("/conversations")
async def list_conversations(
    session: Annotated[ChatSession, Depends(_session_from_header)],
    q: Annotated[str, Query(max_length=120)] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 80,
):
    namespace = identity_namespace(session.tenant_id, session.object_id)
    items = await asyncio.to_thread(conversation_store.list, namespace, q, limit)
    return {"conversations": items, "count": len(items)}


@router.post("/conversations")
async def create_conversation(
    req: ConversationCreateRequest,
    session: Annotated[ChatSession, Depends(_session_from_header)],
):
    namespace = identity_namespace(session.tenant_id, session.object_id)
    conversation = await asyncio.to_thread(
        conversation_store.ensure,
        namespace,
        req.conversation_id,
        req.dashboard_context.model_dump() if req.dashboard_context else None,
    )
    return conversation


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    session: Annotated[ChatSession, Depends(_session_from_header)],
):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", conversation_id):
        raise HTTPException(status_code=422, detail="Identificador de conversa inválido.")
    namespace = identity_namespace(session.tenant_id, session.object_id)
    try:
        return await asyncio.to_thread(conversation_store.get, namespace, conversation_id)
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    req: ConversationUpdateRequest,
    session: Annotated[ChatSession, Depends(_session_from_header)],
):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", conversation_id):
        raise HTTPException(status_code=422, detail="Identificador de conversa inválido.")
    namespace = identity_namespace(session.tenant_id, session.object_id)
    try:
        return await asyncio.to_thread(
            conversation_store.update,
            namespace,
            conversation_id,
            title=req.title,
            pinned=req.pinned,
            dashboard_context=(
                req.dashboard_context.model_dump() if req.dashboard_context else None
            ),
        )
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    session: Annotated[ChatSession, Depends(_session_from_header)],
):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", conversation_id):
        raise HTTPException(status_code=422, detail="Identificador de conversa inválido.")
    namespace = identity_namespace(session.tenant_id, session.object_id)
    deleted = await asyncio.to_thread(conversation_store.delete, namespace, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    await conversation_memory.clear(namespace, conversation_id)
    return {"deleted": True, "conversation_id": conversation_id}


@router.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    session: Annotated[ChatSession, Depends(_session_from_header)],
):
    try:
        await enforce_rate_limit(f"{session.email}:feedback")
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    namespace = identity_namespace(session.tenant_id, session.object_id)
    accepted = await feedback_registry.submit(
        req.response_id,
        namespace,
        req.rating,
        req.reason,
    )
    if not accepted:
        archived_metadata = await asyncio.to_thread(
            conversation_store.response_metadata,
            namespace,
            req.response_id,
        )
        if archived_metadata is not None:
            await feedback_registry.register(req.response_id, namespace, archived_metadata)
            accepted = await feedback_registry.submit(
                req.response_id,
                namespace,
                req.rating,
                req.reason,
            )
    if not accepted:
        raise HTTPException(status_code=404, detail="Resposta não encontrada ou feedback expirado.")
    chat_observability.record_feedback(req.rating)
    return {"accepted": True, "rating": req.rating}


@router.delete("/conversation")
async def reset_conversation(
    req: ConversationResetRequest,
    session: Annotated[ChatSession, Depends(_session_from_header)],
):
    await conversation_memory.clear(
        identity_namespace(session.tenant_id, session.object_id),
        req.conversation_id,
    )
    return {"cleared": True, "conversation_id": req.conversation_id}


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, session: Annotated[ChatSession, Depends(_session_from_header)]):
    """Non-streaming compatibility endpoint used by tests and API clients."""
    try:
        await enforce_rate_limit(session.email)
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    started = time.perf_counter()
    response_id = uuid.uuid4().hex
    history = await _request_history(req, session)
    guarded = guard_user_message(req.message)
    if guarded:
        logger.warning("chat_guardrail_blocked category=%s", guarded.category)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        payload = _answer_payload(
            _guardrail_answer(guarded),
            elapsed_ms,
            _guardrail_reasoning(guarded),
            response_id=response_id,
            analysis_mode=req.analysis_mode,
        )
        await _remember_and_register(req, session, response_id, payload)
        chat_observability.record(
            mode="deterministic",
            analysis_mode=req.analysis_mode,
            elapsed_ms=elapsed_ms,
            cache_kind="bypass",
        )
        return payload

    context = build_operational_context()
    context = await _context_for_request(req, session, context)
    deterministic = answer_deterministically(req.message, context)
    if deterministic:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        payload = _answer_payload(
            deterministic,
            elapsed_ms,
            response_id=response_id,
            analysis_mode=req.analysis_mode,
        )
        await _remember_and_register(req, session, response_id, payload)
        chat_observability.record(
            mode="deterministic",
            analysis_mode=req.analysis_mode,
            elapsed_ms=elapsed_ms,
            cache_kind="bypass",
        )
        return payload

    try:
        generated = await _analytical_answer(req, session, context, history)
    except ProviderError as exc:
        chat_observability.record(
            mode="llm",
            analysis_mode=req.analysis_mode,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
            error=True,
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    payload = {
        **generated,
        "reasoning": generated.get("reasoning") or None,
        "elapsed_ms": elapsed_ms,
        "mode": "llm",
        "provider": provider.name,
        "model": provider.model,
        "badge": _provider_badge(),
        "action": None,
        "suggestions": [],
        "used_pro": req.analysis_mode == "deep",
        "response_id": response_id,
        "analysis_mode": req.analysis_mode,
    }
    await _remember_and_register(req, session, response_id, payload)
    chat_observability.record(
        mode="llm",
        analysis_mode=req.analysis_mode,
        elapsed_ms=elapsed_ms,
        cache_kind=generated.get("cache", {}).get("kind", "miss"),
        usage=generated.get("usage", {}),
    )
    return ChatResponse(**payload)


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    request: Request,
    session: Annotated[ChatSession, Depends(_session_from_header)],
):
    """Stream newline-delimited JSON events so the UI stays responsive on laptop hardware."""
    try:
        await enforce_rate_limit(session.email)
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    started = time.perf_counter()
    response_id = uuid.uuid4().hex
    history = await _request_history(req, session)
    guarded = guard_user_message(req.message)
    context = build_operational_context() if guarded is None else None
    if context is not None:
        context = await _context_for_request(req, session, context)
    deterministic = (
        _guardrail_answer(guarded)
        if guarded
        else answer_deterministically(req.message, context or {})
    )

    async def events() -> AsyncIterator[bytes]:
        if deterministic:
            yield _event(
                "meta",
                mode="deterministic",
                provider="outputs",
                model=None,
                badge=deterministic.badge or None,
                action=deterministic.action,
                suggestions=deterministic.suggestions,
                response_id=response_id,
                analysis_mode=req.analysis_mode,
            )
            yield _event("status", phase="evidence", label="Consultando o snapshot operacional")
            reasoning = _guardrail_reasoning(guarded) if guarded else _deterministic_reasoning()
            if guarded:
                logger.warning("chat_guardrail_blocked category=%s", guarded.category)
            yield _event("reasoning", delta=reasoning)
            yield _event("status", phase="answer", label="Resposta factual validada")
            yield _event("token", delta=deterministic.reply)
            sources = [{
                "id": "versioned_outputs",
                "label": "Artefatos operacionais versionados",
                "kind": "official_snapshot",
            }]
            yield _event("sources", items=sources)
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            payload = {
                "reply": deterministic.reply,
                "reasoning": reasoning,
                "elapsed_ms": elapsed_ms,
                "mode": "deterministic",
                "provider": "outputs",
                "model": None,
                "badge": deterministic.badge or None,
                "action": deterministic.action,
                "suggestions": deterministic.suggestions,
                "sources": sources,
                "usage": {},
                "cache": {"hit": False, "kind": "bypass"},
            }
            await _remember_and_register(req, session, response_id, payload)
            chat_observability.record(
                mode="deterministic",
                analysis_mode=req.analysis_mode,
                elapsed_ms=elapsed_ms,
                cache_kind="bypass",
            )
            yield _event(
                "done",
                elapsed_ms=elapsed_ms,
                response_id=response_id,
                sources=sources,
                usage={},
                cache={"hit": False, "kind": "bypass"},
            )
            return

        yield _event(
            "meta",
            mode="llm",
            provider=provider.name,
            model=provider.model,
            badge=_provider_badge(),
            action=None,
            suggestions=[],
            response_id=response_id,
            analysis_mode=req.analysis_mode,
        )
        yield _event("status", phase="evidence", label="Consultando evidências e modelos relevantes")
        try:
            if await request.is_disconnected():
                return
            generated = await _analytical_answer(
                req,
                session,
                context or {},
                history,
            )
            cache_info = generated.get("cache", {"hit": False, "kind": "miss"})
            if cache_info.get("hit"):
                yield _event("status", phase="cache", label="Resposta validada recuperada do cache")
            if generated.get("reasoning"):
                yield _event("reasoning", delta=generated["reasoning"])
            yield _event("status", phase="answer", label="Análise concluída; resposta validada")
            yield _event("token", delta=generated["reply"])
            sources = generated.get("sources", [])
            if sources:
                yield _event("sources", items=sources)
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            payload = {
                **generated,
                "mode": "llm",
                "provider": provider.name,
                "model": provider.model,
                "badge": _provider_badge(),
                "action": None,
                "suggestions": [],
                "elapsed_ms": elapsed_ms,
            }
            await _remember_and_register(req, session, response_id, payload)
            chat_observability.record(
                mode="llm",
                analysis_mode=req.analysis_mode,
                elapsed_ms=elapsed_ms,
                cache_kind=cache_info.get("kind", "miss"),
                usage=generated.get("usage", {}),
            )
            yield _event(
                "done",
                elapsed_ms=elapsed_ms,
                response_id=response_id,
                sources=sources,
                usage=generated.get("usage", {}),
                cache=cache_info,
            )
        except ProviderError as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            chat_observability.record(
                mode="llm",
                analysis_mode=req.analysis_mode,
                elapsed_ms=elapsed_ms,
                error=True,
            )
            yield _event(
                "error",
                detail=str(exc),
                elapsed_ms=elapsed_ms,
            )

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
