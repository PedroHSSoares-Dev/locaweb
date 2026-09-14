"""Short signed session issued only after Microsoft Entra verification.

The Entra access token is exchanged once; the resulting Predictfy session
protects every API route and revalidates the bound identity, role, status and
session version in the authorization database on every request.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass

from api.services.shared_redis import shared_redis
from api.services.user_store import (
    UserAccess,
    UserConflict,
    UserNotFound,
    UserStoreUnavailable,
    user_store,
)


EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_requests: dict[str, deque[float]] = defaultdict(deque)


class SessionError(ValueError):
    pass


class SessionBackendError(SessionError):
    """Authorization could not be safely checked due to backend failure."""


class RateLimitError(ValueError):
    pass


@dataclass(frozen=True)
class ChatSession:
    email: str
    expires_at: int
    object_id: str = ""
    tenant_id: str = ""
    user_id: str = ""
    role: str = "member"
    permissions: tuple[str, ...] = ("chat:use",)
    session_version: int = 1
    is_owner: bool = False
    token_id: str = ""
    auth_mode: str = "entra-rbac"


def _secret() -> bytes:
    value = os.getenv("CHAT_SESSION_SECRET", "predictfy-local-development-only")
    return value.encode("utf-8")


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _allowed_emails() -> set[str]:
    return {
        email.strip().lower()
        for email in os.getenv("ALLOWED_EMAILS", "").split(",")
        if email.strip()
    }


def local_access_enabled() -> bool:
    return os.getenv("CHAT_ALLOW_LOCAL_DEV", "true").lower() in {"1", "true", "yes", "on"}


def local_auth_bypass_enabled() -> bool:
    """Return whether the explicit, loopback-only development login is enabled."""
    return os.getenv("CHAT_LOCAL_AUTH_BYPASS", "false").lower() in {"1", "true", "yes", "on"}


def _signed_token(session: ChatSession, *, version: int = 3, dev: bool = False) -> str:
    payload_data = {
        "email": session.email,
        "exp": session.expires_at,
        "oid": session.object_id,
        "tid": session.tenant_id,
        "uid": session.user_id,
        "sv": session.session_version,
        "jti": session.token_id,
        "v": version,
    }
    if dev:
        payload_data["dev"] = True
    payload = _encode(json.dumps(payload_data, separators=(",", ":")).encode())
    signature = _encode(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def _session_from_access(access: UserAccess, expires_at: int, token_id: str = "") -> ChatSession:
    return ChatSession(
        email=access.email,
        expires_at=expires_at,
        object_id=access.object_id,
        tenant_id=access.tenant_id,
        user_id=access.id,
        role=access.role,
        permissions=access.permissions,
        session_version=access.session_version,
        is_owner=access.is_owner,
        token_id=token_id,
    )


def create_session(
    email: str,
    *,
    object_id: str = "",
    tenant_id: str = "",
) -> tuple[str, ChatSession]:
    normalized = email.strip().lower()
    if not EMAIL_RE.match(normalized):
        raise SessionError("Acesso não autorizado.")
    if not object_id.strip() or not tenant_id.strip():
        raise SessionError("Identidade Microsoft incompleta.")

    bootstrap_emails = _allowed_emails()
    try:
        access = user_store.authorize_login(
            normalized,
            object_id,
            tenant_id,
            bootstrap_emails=bootstrap_emails,
            allow_local_unlisted=local_access_enabled() and not bootstrap_emails,
        )
    except (UserNotFound, UserConflict) as exc:
        # Deliberately generic: do not disclose invitation, status, or binding state.
        raise SessionError("Acesso não autorizado.") from exc
    except UserStoreUnavailable as exc:
        raise SessionBackendError("Serviço de autorização temporariamente indisponível.") from exc

    ttl_minutes = max(5, int(os.getenv("CHAT_SESSION_TTL_MINUTES", "480")))
    session = _session_from_access(
        access,
        int(time.time()) + ttl_minutes * 60,
        token_id=str(uuid.uuid4()),
    )
    return _signed_token(session), session


def create_local_dev_session() -> tuple[str, ChatSession]:
    """Create a DB-independent admin session for an explicitly enabled local server."""
    if not local_auth_bypass_enabled():
        raise SessionError("Bypass local desativado.")

    configured_email = os.getenv("CHAT_LOCAL_AUTH_EMAIL", "pedrohssoares@live.com")
    email = configured_email.strip().lower()
    if not EMAIL_RE.fullmatch(email):
        raise SessionError("CHAT_LOCAL_AUTH_EMAIL inválido.")

    ttl_minutes = max(5, min(120, int(os.getenv("CHAT_LOCAL_AUTH_TTL_MINUTES", "60"))))
    session = ChatSession(
        email=email,
        expires_at=int(time.time()) + ttl_minutes * 60,
        object_id="predictfy-local-bypass",
        tenant_id="local-development",
        user_id=f"local-dev:{email}",
        role="admin",
        permissions=("chat:use", "users:read", "users:write", "usage:read"),
        session_version=1,
        is_owner=True,
        token_id=str(uuid.uuid4()),
        auth_mode="local-bypass",
    )
    return _signed_token(session, version=4, dev=True), session


def verify_session(token: str) -> ChatSession:
    try:
        payload, supplied_signature = token.split(".", 1)
        expected_signature = _encode(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise SessionError("Sessão inválida.")
        raw = json.loads(_decode(payload))
        version = int(raw.get("v", 0))
        is_local_bypass = version == 4 and raw.get("dev") is True
        if version != 3 and not is_local_bypass:
            raise SessionError("Sessão anterior ao SSO não é mais válida.")
        email = str(raw["email"])
        expires_at = int(raw["exp"])
        object_id = str(raw.get("oid", ""))
        tenant_id = str(raw.get("tid", ""))
        session_version = int(raw.get("sv", 0))
        user_id = str(raw.get("uid", ""))
        token_id = str(raw.get("jti", ""))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, SessionError):
            raise
        raise SessionError("Sessão inválida.") from exc

    if expires_at <= int(time.time()):
        raise SessionError("Sessão expirada.")
    if not object_id or not tenant_id or not user_id or not token_id:
        raise SessionError("Sessão sem identidade Microsoft.")
    if is_local_bypass:
        if not local_auth_bypass_enabled():
            raise SessionError("Bypass local desativado.")
        if not EMAIL_RE.fullmatch(email) or user_id != f"local-dev:{email}":
            raise SessionError("Sessão local inválida.")
        return ChatSession(
            email=email,
            expires_at=expires_at,
            object_id=object_id,
            tenant_id=tenant_id,
            user_id=user_id,
            role="admin",
            permissions=("chat:use", "users:read", "users:write", "usage:read"),
            session_version=session_version,
            is_owner=True,
            token_id=token_id,
            auth_mode="local-bypass",
        )
    try:
        access = user_store.authorize_session(
            user_id,
            object_id,
            tenant_id,
            session_version,
            bootstrap_emails=_allowed_emails(),
            allow_local_unlisted=local_access_enabled() and not _allowed_emails(),
            email=email,
        )
    except UserNotFound as exc:
        raise SessionError(str(exc)) from exc
    except UserStoreUnavailable as exc:
        raise SessionBackendError("Serviço de autorização temporariamente indisponível.") from exc
    return _session_from_access(access, expires_at, token_id)


def revoke_session(session: ChatSession) -> None:
    if session.auth_mode == "local-bypass":
        return
    try:
        user_store.revoke_session(
            session.user_id,
            session.object_id,
            session.tenant_id,
            session.session_version,
            session.email,
        )
    except UserNotFound as exc:
        raise SessionError("Acesso não autorizado.") from exc
    except UserStoreUnavailable as exc:
        raise SessionBackendError("Serviço de autorização temporariamente indisponível.") from exc


def record_session_usage(
    session: ChatSession,
    *,
    response_id: str,
    provider: str,
    model: str | None,
    response_mode: str,
    analysis_mode: str,
    usage: dict,
    cache_hit: bool,
) -> bool:
    """Associate content-free model counters with the authenticated app user."""
    if session.auth_mode == "local-bypass":
        return False
    return user_store.record_usage(
        response_id=response_id,
        user_id=session.user_id,
        provider=provider,
        model=model,
        response_mode=response_mode,
        analysis_mode=analysis_mode,
        usage=usage,
        cache_hit=cache_hit,
    )


async def enforce_rate_limit(identity: str) -> None:
    """Enforce a shared limit through Redis, with a safe local fallback."""
    limit = max(1, int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "20")))
    epoch_now = int(time.time())
    bucket = epoch_now // 60
    identity_hash = hashlib.sha256(identity.strip().lower().encode()).hexdigest()[:24]
    distributed_count = await shared_redis.increment_window(
        f"predictfy:chat:rate:{identity_hash}:{bucket}",
        70,
    )
    if distributed_count is not None:
        if distributed_count > limit:
            raise RateLimitError("Limite de consultas atingido. Aguarde um minuto.")
        return

    now = time.monotonic()
    window = _requests[identity]
    while window and now - window[0] >= 60:
        window.popleft()
    if len(window) >= limit:
        raise RateLimitError("Limite de consultas atingido. Aguarde um minuto.")
    window.append(now)
