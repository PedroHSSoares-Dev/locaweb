"""Short-term memory, observability and explicit feedback for the chatbot."""

from __future__ import annotations

import hashlib
import os
import threading
import time
from collections import Counter, OrderedDict
from dataclasses import dataclass
from typing import Any

from api.services.shared_redis import shared_redis


def identity_namespace(tenant_id: str, object_id: str) -> str:
    """Create a stable, non-identifying namespace for private runtime state."""
    material = f"{tenant_id.strip().lower()}:{object_id.strip().lower()}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


@dataclass
class _Conversation:
    expires_at: float
    messages: list[dict[str, str]]


class ConversationMemory:
    def __init__(self) -> None:
        self.ttl_seconds = max(300, int(os.getenv("CHAT_MEMORY_TTL_SECONDS", "28800")))
        self.max_conversations = max(16, int(os.getenv("CHAT_MEMORY_MAX_CONVERSATIONS", "256")))
        self.max_messages = max(2, min(20, int(os.getenv("CHAT_MEMORY_MAX_MESSAGES", "8"))))
        self._items: OrderedDict[str, _Conversation] = OrderedDict()

    def _key(self, namespace: str, conversation_id: str) -> str:
        digest = hashlib.sha256(f"{namespace}:{conversation_id}".encode()).hexdigest()
        return f"predictfy:chat:memory:{digest}"

    async def get(self, namespace: str, conversation_id: str) -> list[dict[str, str]]:
        if not conversation_id:
            return []
        key = self._key(namespace, conversation_id)
        now = time.monotonic()
        local = self._items.get(key)
        if local and local.expires_at > now:
            self._items.move_to_end(key)
            return [dict(item) for item in local.messages]
        if local:
            self._items.pop(key, None)
        shared = await shared_redis.get_json(key)
        if isinstance(shared, list):
            messages = [
                {"role": str(item.get("role", "")), "content": str(item.get("content", ""))}
                for item in shared
                if isinstance(item, dict) and item.get("role") in {"user", "assistant"}
            ][-self.max_messages:]
            if messages:
                self._remember(key, messages)
            return messages
        return []

    def _remember(self, key: str, messages: list[dict[str, str]]) -> None:
        self._items[key] = _Conversation(time.monotonic() + self.ttl_seconds, messages)
        self._items.move_to_end(key)
        while len(self._items) > self.max_conversations:
            self._items.popitem(last=False)

    async def append_exchange(
        self,
        namespace: str,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        if not conversation_id:
            return
        key = self._key(namespace, conversation_id)
        messages = await self.get(namespace, conversation_id)
        messages.extend((
            {"role": "user", "content": user_message[:6000]},
            {"role": "assistant", "content": assistant_message[:6000]},
        ))
        messages = messages[-self.max_messages:]
        self._remember(key, messages)
        await shared_redis.set_json(key, messages, self.ttl_seconds)

    async def clear(self, namespace: str, conversation_id: str) -> None:
        if not conversation_id:
            return
        key = self._key(namespace, conversation_id)
        self._items.pop(key, None)
        await shared_redis.delete(key)

    def public_stats(self) -> dict[str, Any]:
        return {
            "ttl_seconds": self.ttl_seconds,
            "active_local_conversations": len(self._items),
            "max_messages_per_conversation": self.max_messages,
            "shared_backend": shared_redis.configured,
        }


class ChatObservability:
    """Process-local aggregate telemetry; never stores prompts or answers."""

    def __init__(self) -> None:
        self.started_at = int(time.time())
        self._counters: Counter[str] = Counter()
        self._latency_ms = 0
        self._lock = threading.Lock()

    def record(
        self,
        *,
        mode: str,
        analysis_mode: str,
        elapsed_ms: int,
        cache_kind: str = "miss",
        usage: dict[str, int] | None = None,
        error: bool = False,
    ) -> None:
        usage = usage or {}
        with self._lock:
            self._counters["requests"] += 1
            self._counters[f"route:{mode}"] += 1
            self._counters[f"analysis:{analysis_mode}"] += 1
            self._counters[f"cache:{cache_kind}"] += 1
            if error:
                self._counters["errors"] += 1
            for field in ("input_tokens", "output_tokens", "cached_tokens", "reasoning_tokens"):
                self._counters[f"tokens:{field}"] += int(usage.get(field, 0) or 0)
            self._latency_ms += max(0, int(elapsed_ms))

    def record_feedback(self, rating: str) -> None:
        with self._lock:
            self._counters[f"feedback:{rating}"] += 1

    def public_stats(self) -> dict[str, Any]:
        with self._lock:
            requests = int(self._counters["requests"])
            return {
                "since_epoch": self.started_at,
                "requests": requests,
                "errors": int(self._counters["errors"]),
                "average_latency_ms": round(self._latency_ms / requests) if requests else 0,
                "routes": {
                    "deterministic": int(self._counters["route:deterministic"]),
                    "llm": int(self._counters["route:llm"]),
                },
                "analysis_modes": {
                    "fast": int(self._counters["analysis:fast"]),
                    "deep": int(self._counters["analysis:deep"]),
                },
                "cache": {
                    key.removeprefix("cache:"): int(value)
                    for key, value in self._counters.items()
                    if key.startswith("cache:")
                },
                "tokens": {
                    key.removeprefix("tokens:"): int(value)
                    for key, value in self._counters.items()
                    if key.startswith("tokens:")
                },
                "feedback": {
                    "up": int(self._counters["feedback:up"]),
                    "down": int(self._counters["feedback:down"]),
                },
            }


class FeedbackRegistry:
    """Accept feedback only for recent responses issued to the same identity."""

    def __init__(self) -> None:
        self.ttl_seconds = max(300, int(os.getenv("CHAT_FEEDBACK_TTL_SECONDS", "86400")))
        self.max_entries = max(100, int(os.getenv("CHAT_FEEDBACK_MAX_ENTRIES", "2000")))
        self._responses: OrderedDict[str, tuple[float, str, dict[str, Any]]] = OrderedDict()
        self._feedback: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def _response_key(self, response_id: str) -> str:
        return f"predictfy:chat:feedback-response:{response_id}"

    async def register(self, response_id: str, namespace: str, metadata: dict[str, Any]) -> None:
        with self._lock:
            self._responses[response_id] = (time.monotonic() + self.ttl_seconds, namespace, metadata)
            self._responses.move_to_end(response_id)
            while len(self._responses) > self.max_entries:
                self._responses.popitem(last=False)
        await shared_redis.set_json(
            self._response_key(response_id),
            {"namespace": namespace, "metadata": metadata},
            self.ttl_seconds,
        )

    async def submit(
        self,
        response_id: str,
        namespace: str,
        rating: str,
        reason: str = "",
    ) -> bool:
        with self._lock:
            record = self._responses.get(response_id)
        if not record or record[0] <= time.monotonic():
            shared = await shared_redis.get_json(self._response_key(response_id))
            if isinstance(shared, dict) and isinstance(shared.get("metadata"), dict):
                record = (
                    time.monotonic() + self.ttl_seconds,
                    str(shared.get("namespace", "")),
                    shared["metadata"],
                )
        if not record or record[1] != namespace:
            return False
        with self._lock:
            self._feedback[response_id] = {
                "rating": rating,
                "reason": reason[:240],
                "recorded_at": int(time.time()),
                **record[2],
            }
            self._feedback.move_to_end(response_id)
            while len(self._feedback) > self.max_entries:
                self._feedback.popitem(last=False)
            feedback = dict(self._feedback[response_id])
        await shared_redis.set_json(
            f"predictfy:chat:feedback:{response_id}",
            feedback,
            self.ttl_seconds,
        )
        return True


conversation_memory = ConversationMemory()
chat_observability = ChatObservability()
feedback_registry = FeedbackRegistry()
