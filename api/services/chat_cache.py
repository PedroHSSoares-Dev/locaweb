"""Versioned response cache with local single-flight and safe similarity reuse."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import time
import unicodedata
from collections import Counter, OrderedDict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator

from api.services.shared_redis import shared_redis


_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_SENSITIVE_TOKEN_RE = re.compile(r"\b(?:p[1-5]|\d+(?:[.,]\d+)?)\b", re.IGNORECASE)
_SEMANTIC_GUARD_RE = re.compile(
    r"\b(?:nao|sem|com|baixo|alta|alto|aumenta|aumento|diminui|queda|melhora|piora|trimestre|semestre)\b",
    re.IGNORECASE,
)
_FOLLOW_UP_RE = re.compile(
    r"\b(?:isso|isto|aquilo|ele|ela|eles|elas|anterior|acima|continue|detalhe|explique melhor)\b",
    re.IGNORECASE,
)
_SYNONYMS = {
    "alertas": "incidentes",
    "alerta": "incidente",
    "ocorrencias": "incidentes",
    "ocorrencia": "incidente",
    "estourar": "exceder",
    "estoura": "exceder",
    "ultrapassar": "exceder",
    "limite": "cota",
    "orcamento": "cota",
    "preocupado": "risco",
    "preocupar": "risco",
    "perigoso": "risco",
    "projecao": "previsao",
}


def _enabled(name: str, default: bool = True) -> bool:
    fallback = "true" if default else "false"
    return os.getenv(name, fallback).lower() in {"1", "true", "yes", "on"}


def normalize_query(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    words = [_SYNONYMS.get(word, word) for word in _WORD_RE.findall(normalized)]
    return " ".join(words)


def context_fingerprint(
    context: dict[str, Any],
    *,
    prompt_version: str,
    provider: str,
    model: str,
) -> str:
    """Invalidate cached answers whenever evidence, prompt or model changes."""
    serialized = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    material = f"{prompt_version}|{provider}|{model}|{serialized}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def response_cache_key(
    *,
    namespace: str,
    message: str,
    history: list[dict[str, str]],
    analysis_mode: str,
    fingerprint: str,
) -> str:
    history_material = json.dumps(history, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    material = "|".join((namespace, analysis_mode, fingerprint, normalize_query(message), history_material))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CacheLookup:
    value: dict[str, Any]
    kind: str


@dataclass
class _MemoryEntry:
    expires_at: float
    value: dict[str, Any]


@dataclass
class _SemanticEntry:
    namespace: str
    fingerprint: str
    analysis_mode: str
    normalized_query: str
    sensitive_tokens: tuple[str, ...]
    expires_at: float
    value: dict[str, Any]


def _trigrams(value: str) -> Counter[str]:
    padded = f"  {value}  "
    return Counter(padded[index:index + 3] for index in range(max(0, len(padded) - 2)))


def _semantic_guards(value: str) -> tuple[str, ...]:
    tokens = _SENSITIVE_TOKEN_RE.findall(value) + _SEMANTIC_GUARD_RE.findall(value)
    return tuple(sorted(token.lower() for token in tokens))


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    numerator = sum(count * right.get(token, 0) for token, count in left.items())
    left_norm = math.sqrt(sum(count * count for count in left.values()))
    right_norm = math.sqrt(sum(count * count for count in right.values()))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


class ResponseCache:
    """Bounded L1 cache, optional shared L2 and conservative semantic cache."""

    def __init__(self) -> None:
        self.ttl_seconds = max(30, int(os.getenv("CHAT_CACHE_TTL_SECONDS", "900")))
        self.max_entries = max(16, int(os.getenv("CHAT_CACHE_MAX_ENTRIES", "256")))
        self.semantic_threshold = min(
            0.99,
            max(0.80, float(os.getenv("CHAT_SEMANTIC_CACHE_THRESHOLD", "0.94"))),
        )
        self._entries: OrderedDict[str, _MemoryEntry] = OrderedDict()
        self._semantic: list[_SemanticEntry] = []
        self._locks: dict[str, tuple[asyncio.Lock, int]] = {}
        self._locks_guard = asyncio.Lock()
        self.stats = Counter()

    @property
    def enabled(self) -> bool:
        return _enabled("CHAT_CACHE_ENABLED")

    def _redis_key(self, key: str) -> str:
        return f"predictfy:chat:response:{key}"

    def _remember(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        self._entries[key] = _MemoryEntry(time.monotonic() + (ttl or self.ttl_seconds), value)
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def _semantic_eligible(self, message: str, history: list[dict[str, str]]) -> bool:
        normalized = normalize_query(message)
        return (
            _enabled("CHAT_SEMANTIC_CACHE_ENABLED")
            and not history
            and 12 <= len(normalized) <= 320
            and not _FOLLOW_UP_RE.search(normalized)
        )

    async def get(
        self,
        key: str,
        *,
        namespace: str,
        message: str,
        history: list[dict[str, str]],
        analysis_mode: str,
        fingerprint: str,
        count_miss: bool = True,
    ) -> CacheLookup | None:
        if not self.enabled:
            self.stats["disabled"] += 1
            return None

        now = time.monotonic()
        local = self._entries.get(key)
        if local and local.expires_at > now:
            self._entries.move_to_end(key)
            self.stats["exact_hits"] += 1
            return CacheLookup(dict(local.value), "exact")
        if local:
            self._entries.pop(key, None)

        shared = await shared_redis.get_json(self._redis_key(key))
        if isinstance(shared, dict):
            self._remember(key, shared)
            self.stats["shared_hits"] += 1
            return CacheLookup(dict(shared), "shared")

        if self._semantic_eligible(message, history):
            normalized = normalize_query(message)
            sensitive = _semantic_guards(normalized)
            query_vector = _trigrams(normalized)
            best: tuple[float, _SemanticEntry] | None = None
            retained: list[_SemanticEntry] = []
            for candidate in self._semantic:
                if candidate.expires_at <= now:
                    continue
                retained.append(candidate)
                if (
                    candidate.namespace != namespace
                    or candidate.fingerprint != fingerprint
                    or candidate.analysis_mode != analysis_mode
                    or candidate.sensitive_tokens != sensitive
                ):
                    continue
                similarity = _cosine(query_vector, _trigrams(candidate.normalized_query))
                if best is None or similarity > best[0]:
                    best = (similarity, candidate)
            self._semantic = retained[-self.max_entries:]
            if best and best[0] >= self.semantic_threshold:
                self.stats["semantic_hits"] += 1
                value = dict(best[1].value)
                value["semantic_similarity"] = round(best[0], 4)
                return CacheLookup(value, "semantic")

        if count_miss:
            self.stats["misses"] += 1
        return None

    async def set(
        self,
        key: str,
        value: dict[str, Any],
        *,
        namespace: str,
        message: str,
        history: list[dict[str, str]],
        analysis_mode: str,
        fingerprint: str,
    ) -> None:
        if not self.enabled:
            return
        safe_value = json.loads(json.dumps(value, ensure_ascii=False, default=str))
        self._remember(key, safe_value)
        await shared_redis.set_json(self._redis_key(key), safe_value, self.ttl_seconds)
        if self._semantic_eligible(message, history):
            normalized = normalize_query(message)
            self._semantic.append(_SemanticEntry(
                namespace=namespace,
                fingerprint=fingerprint,
                analysis_mode=analysis_mode,
                normalized_query=normalized,
                sensitive_tokens=_semantic_guards(normalized),
                expires_at=time.monotonic() + self.ttl_seconds,
                value=safe_value,
            ))
            self._semantic = self._semantic[-self.max_entries:]
        self.stats["stores"] += 1

    @asynccontextmanager
    async def singleflight(self, key: str) -> AsyncIterator[None]:
        """Coalesce equal in-flight requests inside the current API worker."""
        async with self._locks_guard:
            lock, references = self._locks.get(key, (asyncio.Lock(), 0))
            waiting = lock.locked()
            self._locks[key] = (lock, references + 1)
        if waiting:
            self.stats["singleflight_waits"] += 1
        await lock.acquire()
        try:
            yield
        finally:
            lock.release()
            async with self._locks_guard:
                current_lock, references = self._locks.get(key, (lock, 1))
                if current_lock is lock and references <= 1:
                    self._locks.pop(key, None)
                elif current_lock is lock:
                    self._locks[key] = (lock, references - 1)

    def public_stats(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "semantic_enabled": _enabled("CHAT_SEMANTIC_CACHE_ENABLED"),
            "ttl_seconds": self.ttl_seconds,
            "l1_entries": len(self._entries),
            "semantic_entries": len(self._semantic),
            "shared_backend": shared_redis.configured,
            **{key: int(value) for key, value in self.stats.items()},
        }


response_cache = ResponseCache()
