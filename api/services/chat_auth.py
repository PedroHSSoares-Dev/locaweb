"""Short signed session issued only after Microsoft Entra verification.

The Entra access token is exchanged once; the resulting Predictfy session
protects both dashboard data and chatbot routes and rechecks the allowlist on
every request.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from api.services.shared_redis import shared_redis


EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_requests: dict[str, deque[float]] = defaultdict(deque)


class SessionError(ValueError):
    pass


class RateLimitError(ValueError):
    pass


@dataclass(frozen=True)
class ChatSession:
    email: str
    expires_at: int
    object_id: str = ""
    tenant_id: str = ""


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


def email_is_allowed(email: str) -> bool:
    normalized = email.strip().lower()
    if not EMAIL_RE.match(normalized):
        return False
    allowed = _allowed_emails()
    return normalized in allowed or (not allowed and local_access_enabled())


def create_session(
    email: str,
    *,
    object_id: str = "",
    tenant_id: str = "",
) -> tuple[str, ChatSession]:
    normalized = email.strip().lower()
    if not email_is_allowed(normalized):
        raise SessionError("Email não autorizado.")
    if not object_id.strip() or not tenant_id.strip():
        raise SessionError("Identidade Microsoft incompleta.")

    ttl_minutes = max(5, int(os.getenv("CHAT_SESSION_TTL_MINUTES", "480")))
    session = ChatSession(
        email=normalized,
        expires_at=int(time.time()) + ttl_minutes * 60,
        object_id=object_id,
        tenant_id=tenant_id,
    )
    payload = _encode(json.dumps({
        "email": session.email,
        "exp": session.expires_at,
        "oid": session.object_id,
        "tid": session.tenant_id,
        "v": 2,
    }, separators=(",", ":")).encode())
    signature = _encode(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}", session


def verify_session(token: str) -> ChatSession:
    try:
        payload, supplied_signature = token.split(".", 1)
        expected_signature = _encode(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise SessionError("Sessão inválida.")
        raw = json.loads(_decode(payload))
        if raw.get("v") != 2:
            raise SessionError("Sessão anterior ao SSO não é mais válida.")
        session = ChatSession(
            email=str(raw["email"]),
            expires_at=int(raw["exp"]),
            object_id=str(raw.get("oid", "")),
            tenant_id=str(raw.get("tid", "")),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, SessionError):
            raise
        raise SessionError("Sessão inválida.") from exc

    if session.expires_at <= int(time.time()):
        raise SessionError("Sessão expirada.")
    if not session.object_id or not session.tenant_id:
        raise SessionError("Sessão sem identidade Microsoft.")
    if not email_is_allowed(session.email):
        raise SessionError("Email não autorizado.")
    return session


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
