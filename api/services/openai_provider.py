"""OpenAI Responses API provider using the same safe structured-output parser."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any, Literal

import httpx

from api.services.chat_tools import CHAT_TOOLS, TOOL_SOURCE_LABELS, execute_chat_tool
from api.services.ollama_provider import (
    SYSTEM_PROMPT,
    GenerationResult,
    OllamaProvider,
    ProviderError,
    _compact_context,
    parse_structured_text,
)


def _event_error_detail(event: dict[str, Any]) -> str:
    """Extract an upstream error without assuming optional objects are dictionaries."""
    error = event.get("error")
    response = event.get("response")
    response_error = response.get("error") if isinstance(response, dict) else None
    direct_message = error.get("message") if isinstance(error, dict) else None
    response_message = response_error.get("message") if isinstance(response_error, dict) else None
    incomplete = event.get("incomplete_details")
    if not isinstance(incomplete, dict) and isinstance(response, dict):
        incomplete = response.get("incomplete_details")
    incomplete_reason = incomplete.get("reason") if isinstance(incomplete, dict) else None
    if incomplete_reason == "max_output_tokens":
        return "A análise excedeu o limite de tokens de saída do Luna."
    return str(
        direct_message
        or response_message
        or (f"A geração foi interrompida: {incomplete_reason}." if incomplete_reason else None)
        or "A geração do GPT-5.6 Luna não foi concluída."
    )[:500]


def _is_complex_request(message: str) -> bool:
    """Identify explicitly integrated analyses without raising cost for ordinary chat."""
    normalized = message.lower()
    signals = (
        "conselho executivo",
        "quatro trimestres",
        "cenário baixo",
        "cenario baixo",
        "verifique matematicamente",
        "procure contradições",
        "plano de ação",
        "acoes priorizadas",
        "ações priorizadas",
        "tabela",
    )
    return len(message) >= 1_800 or sum(signal in normalized for signal in signals) >= 4


class OpenAIProvider(OllamaProvider):
    """GPT provider that reuses the audited analysis/answer stream parser."""

    name = "openai"

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
        self.timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "120"))
        self.reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", "low")
        self.deep_reasoning_effort = os.getenv("OPENAI_DEEP_REASONING_EFFORT", "medium")
        self.max_output_tokens = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "800"))
        configured_complex = int(os.getenv("OPENAI_COMPLEX_MAX_OUTPUT_TOKENS", "1800"))
        self.complex_max_output_tokens = min(max(configured_complex, self.max_output_tokens), 3_200)
        configured_retry = int(os.getenv("OPENAI_RETRY_MAX_OUTPUT_TOKENS", "3200"))
        self.retry_max_output_tokens = min(max(configured_retry, self.complex_max_output_tokens), 4_000)
        configured_deep = int(os.getenv("OPENAI_DEEP_MAX_OUTPUT_TOKENS", "2200"))
        self.deep_max_output_tokens = min(max(configured_deep, self.max_output_tokens), 4_000)
        self.max_tool_rounds = min(max(int(os.getenv("OPENAI_MAX_TOOL_ROUNDS", "3")), 1), 4)
        self.max_tool_calls = min(max(int(os.getenv("OPENAI_MAX_TOOL_CALLS", "6")), 1), 8)

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(
        self,
        message: str,
        history: list[dict[str, str]],
        context: dict[str, Any],
        *,
        stream: bool,
        enable_tools: bool = False,
        input_items: list[dict[str, Any]] | None = None,
        tool_choice: str = "required",
        analysis_mode: Literal["fast", "deep"] = "fast",
    ) -> dict[str, Any]:
        # Tool-enabled requests receive only the immutable operational core. Detailed
        # evidence must be requested through a whitelisted read-only function.
        compact_context = _compact_context(context, "" if enable_tools else message)
        instructions = SYSTEM_PROMPT.format(
            context=json.dumps(compact_context, ensure_ascii=False, separators=(",", ":"))
        )
        if input_items is None:
            input_messages: list[dict[str, Any]] = [
                {"role": item["role"], "content": item["content"]}
                for item in history[-6:]
            ]
            input_messages.append({"role": "user", "content": message})
        else:
            input_messages = input_items
        complex_request = _is_complex_request(message)
        deep = analysis_mode == "deep"
        output_budget = self.complex_max_output_tokens if complex_request else self.max_output_tokens
        if deep:
            output_budget = max(output_budget, self.deep_max_output_tokens)
        payload: dict[str, Any] = {
            "model": self.model,
            "instructions": instructions,
            "input": input_messages,
            "reasoning": {"effort": self.deep_reasoning_effort if deep else self.reasoning_effort},
            "text": {"verbosity": "medium" if (complex_request or deep) else "low"},
            "max_output_tokens": output_budget,
            "stream": stream,
            "store": False,
        }
        if enable_tools:
            payload.update({
                "tools": CHAT_TOOLS,
                "tool_choice": tool_choice,
                "parallel_tool_calls": True,
            })
        return payload

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            body = response.json()
            message = body.get("error", {}).get("message")
        except (ValueError, AttributeError):
            message = None
        return str(message or response.reason_phrase or "erro desconhecido")[:500]

    async def health(self) -> dict[str, Any]:
        if not self.api_key:
            return {
                "available": False,
                "server_available": False,
                "loaded": False,
                "provider": self.name,
                "model": self.model,
                "models": [],
                "detail": "OPENAI_API_KEY não configurada.",
            }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"{self.base_url}/models/{self.model}",
                    headers=self._headers,
                )
            if response.is_success:
                return {
                    "available": True,
                    "server_available": True,
                    "loaded": True,
                    "provider": self.name,
                    "model": self.model,
                    "models": [self.model],
                }
            return {
                "available": False,
                "server_available": True,
                "loaded": False,
                "provider": self.name,
                "model": self.model,
                "models": [],
                "detail": self._error_detail(response),
            }
        except httpx.HTTPError as exc:
            return {
                "available": False,
                "server_available": False,
                "loaded": False,
                "provider": self.name,
                "model": self.model,
                "models": [],
                "detail": f"OpenAI indisponível: {type(exc).__name__}",
            }

    async def acquire_session(self) -> dict[str, Any]:
        status = await self.health()
        if not status.get("available"):
            raise ProviderError(status.get("detail", "GPT-5.6 Luna indisponível."))
        return status

    async def release_session(self) -> dict[str, Any]:
        return {
            "released": True,
            "model": self.model,
            "model_unloaded": False,
            "managed_server_stopped": False,
        }

    async def _raw_stream(
        self,
        message: str,
        history: list[dict[str, str]],
        context: dict[str, Any],
    ) -> AsyncIterator[str]:
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY não configurada.")

        timeout = httpx.Timeout(self.timeout, connect=10)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/responses",
                    headers=self._headers,
                    json=self._payload(
                        message,
                        history,
                        context,
                        stream=True,
                        enable_tools=False,
                    ),
                ) as response:
                    if not response.is_success:
                        await response.aread()
                        raise ProviderError(
                            f"OpenAI API {response.status_code}: {self._error_detail(response)}"
                        )

                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw = line.removeprefix("data:").strip()
                        if not raw or raw == "[DONE]":
                            continue
                        event = json.loads(raw)
                        if not isinstance(event, dict):
                            raise ProviderError("A OpenAI retornou um evento de streaming inválido.")
                        event_type = event.get("type")
                        if event_type == "response.output_text.delta":
                            delta = event.get("delta", "")
                            if delta:
                                yield delta
                        elif event_type in {"error", "response.failed", "response.incomplete"}:
                            raise ProviderError(_event_error_detail(event))
        except ProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise ProviderError("O GPT-5.6 Luna excedeu o tempo limite da consulta.") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Não foi possível acessar a OpenAI: {type(exc).__name__}.") from exc
        except json.JSONDecodeError as exc:
            raise ProviderError("A OpenAI retornou um evento de streaming inválido.") from exc

    async def _create_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create one non-streaming Responses API turn."""
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY não configurada.")

        timeout = httpx.Timeout(self.timeout, connect=10)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/responses",
                    headers=self._headers,
                    json=payload,
                )
            if not response.is_success:
                raise ProviderError(
                    f"OpenAI API {response.status_code}: {self._error_detail(response)}"
                )
            body = response.json()
            if not isinstance(body, dict):
                raise ProviderError("A OpenAI retornou uma resposta inválida.")
            return body
        except ProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise ProviderError("O GPT-5.6 Luna excedeu o tempo limite da consulta.") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Não foi possível acessar a OpenAI: {type(exc).__name__}.") from exc
        except ValueError as exc:
            raise ProviderError("A OpenAI retornou uma resposta JSON inválida.") from exc

    async def _create_response_with_token_retry(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Retry once only when the provider explicitly exhausts output tokens."""
        response = await self._create_response(payload)
        accumulated_usage = self._extract_usage(response)
        details = response.get("incomplete_details")
        reason = details.get("reason") if isinstance(details, dict) else None
        current_budget = int(payload.get("max_output_tokens", self.max_output_tokens))
        if (
            response.get("status") == "incomplete"
            and reason == "max_output_tokens"
            and current_budget < self.retry_max_output_tokens
        ):
            retry_payload = {
                **payload,
                "max_output_tokens": min(current_budget * 2, self.retry_max_output_tokens),
            }
            retried = await self._create_response(retry_payload)
            retried["_predictfy_usage"] = self._merge_usage(
                accumulated_usage,
                self._extract_usage(retried),
            )
            return retried
        response["_predictfy_usage"] = accumulated_usage
        return response

    @staticmethod
    def _extract_usage(response: dict[str, Any]) -> dict[str, int]:
        usage = response.get("usage")
        if not isinstance(usage, dict):
            return {}
        input_details = usage.get("input_tokens_details")
        output_details = usage.get("output_tokens_details")
        return {
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
            "cached_tokens": int(
                input_details.get("cached_tokens", 0) if isinstance(input_details, dict) else 0
            ),
            "reasoning_tokens": int(
                output_details.get("reasoning_tokens", 0) if isinstance(output_details, dict) else 0
            ),
        }

    @staticmethod
    def _merge_usage(*items: dict[str, int]) -> dict[str, int]:
        fields = ("input_tokens", "output_tokens", "cached_tokens", "reasoning_tokens")
        return {field: sum(int(item.get(field, 0) or 0) for item in items) for field in fields}

    @staticmethod
    def _response_text(response: dict[str, Any]) -> str:
        parts: list[str] = []
        for item in response.get("output", []):
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str):
                        parts.append(text)
        return "".join(parts).strip()

    @staticmethod
    def _tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            item
            for item in response.get("output", [])
            if isinstance(item, dict) and item.get("type") == "function_call"
        ]

    def _finalize_tool_answer(
        self,
        response: dict[str, Any],
        used_tools: list[str],
        usage: dict[str, int] | None = None,
    ) -> GenerationResult:
        raw_text = self._response_text(response)
        reasoning, answer = parse_structured_text(raw_text)
        if not answer:
            detail = _event_error_detail(response)
            raise ProviderError(detail if response.get("status") != "completed" else "O Luna não retornou uma resposta final válida.")

        labels = list(dict.fromkeys(
            TOOL_SOURCE_LABELS[name]
            for name in used_tools
            if name in TOOL_SOURCE_LABELS
        ))
        if labels:
            audit = f"Fontes consultadas: {', '.join(labels)}."
            reasoning = f"{audit} {reasoning}".strip()[:1_200]
        sources = tuple({
            "id": name,
            "label": TOOL_SOURCE_LABELS[name],
            "kind": "read_only_tool",
        } for name in dict.fromkeys(used_tools) if name in TOOL_SOURCE_LABELS)
        return GenerationResult(
            answer=answer,
            reasoning=reasoning,
            sources=sources,
            usage=usage or {},
        )

    async def generate(
        self,
        message: str,
        history: list[dict[str, str]],
        context: dict[str, Any],
        analysis_mode: Literal["fast", "deep"] = "fast",
    ) -> GenerationResult:
        """Let Luna select bounded read-only evidence, then produce the guarded answer."""
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY não configurada.")

        running_input: list[dict[str, Any]] | None = None
        used_tools: list[str] = []
        total_calls = 0
        usage_totals: dict[str, int] = {}
        tool_rounds = self.max_tool_rounds if analysis_mode == "deep" else min(2, self.max_tool_rounds)

        for round_index in range(tool_rounds):
            payload = self._payload(
                message,
                history,
                context,
                stream=False,
                enable_tools=True,
                input_items=running_input,
                tool_choice="required" if round_index == 0 else "auto",
                analysis_mode=analysis_mode,
            )
            if running_input is None:
                running_input = list(payload["input"])

            response = await self._create_response_with_token_retry(payload)
            usage_totals = self._merge_usage(
                usage_totals,
                response.get("_predictfy_usage", {}),
            )
            tool_calls = self._tool_calls(response)
            if not tool_calls:
                return self._finalize_tool_answer(response, used_tools, usage_totals)

            # The Responses API requires replaying the complete model output,
            # including reasoning items, before supplying function results.
            running_input.extend(response.get("output", []))
            for call in tool_calls:
                name = str(call.get("name", ""))
                call_id = call.get("call_id")
                if not isinstance(call_id, str) or not call_id:
                    raise ProviderError("O Luna retornou uma chamada de ferramenta sem identificador.")

                if total_calls >= self.max_tool_calls:
                    result: dict[str, Any] = {
                        "erro": "limite de consultas atingido; responda com as evidências já obtidas"
                    }
                else:
                    total_calls += 1
                    try:
                        arguments = json.loads(call.get("arguments", "{}"))
                        if not isinstance(arguments, dict):
                            raise ValueError("Argumentos devem ser um objeto JSON.")
                        result = execute_chat_tool(name, arguments, context)
                        used_tools.append(name)
                    except (json.JSONDecodeError, TypeError, ValueError) as exc:
                        result = {"erro": str(exc)[:240]}

                running_input.append({
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                })

        # Tool rounds are bounded to control cost and prevent loops. Luna gets one
        # final turn with the tools visible but disabled so it must use collected evidence.
        final_payload = self._payload(
            message,
            history,
            context,
            stream=False,
            enable_tools=True,
            input_items=running_input,
            tool_choice="none",
            analysis_mode=analysis_mode,
        )
        final_response = await self._create_response_with_token_retry(final_payload)
        usage_totals = self._merge_usage(
            usage_totals,
            final_response.get("_predictfy_usage", {}),
        )
        return self._finalize_tool_answer(final_response, used_tools, usage_totals)
