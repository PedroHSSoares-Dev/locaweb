"""Microsoft Entra ID access-token validation for the Predictfy API.

The browser authenticates with MSAL and sends an access token whose audience is
the Predictfy API.  Only after this module validates the token does the API
exchange it for the short-lived Predictfy session used by the dashboard.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError


TENANT_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class EntraAuthError(ValueError):
    """Raised when an Entra token cannot establish an authorized identity."""


@dataclass(frozen=True)
class EntraIdentity:
    email: str
    object_id: str
    tenant_id: str


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise EntraAuthError(f"Configuração SSO ausente: {name}.")
    return value


def _tenant_authority() -> str:
    return os.getenv("ENTRA_TENANT_ID", "common").strip() or "common"


@lru_cache(maxsize=4)
def _jwks_client(authority: str) -> PyJWKClient:
    url = f"https://login.microsoftonline.com/{authority}/discovery/v2.0/keys"
    return PyJWKClient(url, cache_keys=True, lifespan=3600)


def _allowed_tenant_ids() -> set[str]:
    configured = {
        item.strip().lower()
        for item in os.getenv("ENTRA_ALLOWED_TENANT_IDS", "").split(",")
        if item.strip()
    }
    authority = _tenant_authority().lower()
    if TENANT_ID_RE.fullmatch(authority):
        configured.add(authority)
    return configured


def _extract_email(claims: dict) -> str:
    for claim_name in ("email", "preferred_username", "upn"):
        value = claims.get(claim_name)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if EMAIL_RE.fullmatch(normalized):
                return normalized
    raise EntraAuthError(
        "A conta Microsoft não forneceu um e-mail verificável. "
        "Configure o claim email/preferred_username no registro da API."
    )


def validate_entra_access_token(token: str) -> EntraIdentity:
    """Validate a v2 user access token issued for the configured API."""
    api_client_id = _required_env("ENTRA_API_CLIENT_ID")
    try:
        unverified_header = jwt.get_unverified_header(token)
        unverified_claims = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False,
            },
        )
    except InvalidTokenError as exc:
        raise EntraAuthError("Token Microsoft inválido.") from exc

    if unverified_header.get("alg") != "RS256" or not unverified_header.get("kid"):
        raise EntraAuthError("Algoritmo ou chave do token Microsoft não autorizado.")

    tenant_id = str(unverified_claims.get("tid", "")).lower()
    if not TENANT_ID_RE.fullmatch(tenant_id):
        raise EntraAuthError("Tenant Microsoft inválido.")

    allowed_tenants = _allowed_tenant_ids()
    if allowed_tenants and tenant_id not in allowed_tenants:
        raise EntraAuthError("Tenant Microsoft não autorizado.")

    if str(unverified_claims.get("ver", "")) != "2.0":
        raise EntraAuthError("A API aceita apenas tokens Microsoft v2.0.")

    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    audiences = [api_client_id, f"api://{api_client_id}"]
    try:
        signing_key = _jwks_client(_tenant_authority()).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audiences,
            issuer=issuer,
            options={"require": ["exp", "iat", "iss", "aud", "tid", "oid", "ver"]},
        )
    except (InvalidTokenError, PyJWKClientError) as exc:
        raise EntraAuthError("Token Microsoft expirado ou inválido para esta API.") from exc

    spa_client_id = os.getenv("ENTRA_SPA_CLIENT_ID", "").strip()
    authorized_party = str(claims.get("azp", ""))
    if spa_client_id and authorized_party != spa_client_id:
        raise EntraAuthError("Aplicação cliente Microsoft não autorizada.")

    required_scope = os.getenv("ENTRA_REQUIRED_SCOPE", "access_as_user").strip()
    scopes = set(str(claims.get("scp", "")).split())
    if required_scope and required_scope not in scopes:
        raise EntraAuthError("Token Microsoft sem permissão para acessar a API.")

    object_id = str(claims.get("oid", "")).strip()
    if not object_id:
        raise EntraAuthError("Identificador da conta Microsoft ausente.")

    return EntraIdentity(
        email=_extract_email(claims),
        object_id=object_id,
        tenant_id=tenant_id,
    )


def require_entra_identity(authorization: str | None = Header(default=None)) -> EntraIdentity:
    """FastAPI dependency used only by the Entra-to-Predictfy session exchange."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token Microsoft ausente.")
    try:
        return validate_entra_access_token(authorization.split(" ", 1)[1].strip())
    except EntraAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
