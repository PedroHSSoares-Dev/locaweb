"""Least-privilege administration of Predictfy application access."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, model_validator

from api.services.chat_auth import ChatSession
from api.services.user_store import (
    UserConflict,
    UserMutationForbidden,
    UserNotFound,
    UserStoreUnavailable,
    user_store,
)


router = APIRouter(prefix="/admin", tags=["Administração"])
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class UserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: Literal["admin", "member"] = "member"

    @model_validator(mode="after")
    def validate_email(self):
        self.email = self.email.strip().lower()
        if not EMAIL_RE.match(self.email):
            raise ValueError("Email inválido.")
        return self


class UserUpdateRequest(BaseModel):
    role: Literal["admin", "member"] | None = None
    # "pending" is reserved for a newly-created invitation.
    status: Literal["active", "disabled"] | None = None
    version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_change(self):
        if self.role is None and self.status is None:
            raise ValueError("Informe role ou status.")
        return self


class VersionRequest(BaseModel):
    version: int | None = Field(default=None, ge=1)


def require_admin(request: Request) -> ChatSession:
    session = getattr(request.state, "session", None)
    if not isinstance(session, ChatSession):
        raise HTTPException(status_code=401, detail="Sessão de acesso ausente.")
    if session.role != "admin" or "users:write" not in session.permissions:
        raise HTTPException(status_code=403, detail="Permissão de administrador necessária.")
    return session


def _raise_store_error(exc: Exception) -> None:
    if isinstance(exc, UserNotFound):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, (UserConflict, UserMutationForbidden)):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, UserStoreUnavailable):
        raise HTTPException(status_code=503, detail="Serviço de autorização temporariamente indisponível.") from exc
    raise exc


@router.get("/users")
def list_users(
    session: Annotated[ChatSession, Depends(require_admin)],
    q: Annotated[str, Query(max_length=120)] = "",
    role: Annotated[Literal["admin", "member"] | None, Query()] = None,
    status_filter: Annotated[
        Literal["pending", "active", "disabled"] | None,
        Query(alias="status"),
    ] = None,
):
    del session
    try:
        items = user_store.list_users(q=q, role=role or "", status=status_filter or "")
        return {"users": items, "count": len(items)}
    except Exception as exc:
        _raise_store_error(exc)


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreateRequest,
    session: Annotated[ChatSession, Depends(require_admin)],
):
    try:
        return {"user": user_store.invite(body.email, body.role, session.email)}
    except Exception as exc:
        _raise_store_error(exc)


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    body: UserUpdateRequest,
    session: Annotated[ChatSession, Depends(require_admin)],
):
    try:
        user = user_store.update_user(
            user_id,
            session.email,
            role=body.role,
            status=body.status,
            expected_version=body.version,
        )
        return {"user": user}
    except Exception as exc:
        _raise_store_error(exc)


@router.post("/users/{user_id}/enable")
def enable_user(
    user_id: str,
    body: VersionRequest,
    session: Annotated[ChatSession, Depends(require_admin)],
):
    try:
        return {"user": user_store.update_user(
            user_id, session.email, status="active", expected_version=body.version,
            action="user_enabled",
        )}
    except Exception as exc:
        _raise_store_error(exc)


@router.post("/users/{user_id}/disable")
def disable_user(
    user_id: str,
    body: VersionRequest,
    session: Annotated[ChatSession, Depends(require_admin)],
):
    try:
        return {"user": user_store.update_user(
            user_id, session.email, status="disabled", expected_version=body.version,
            action="user_disabled",
        )}
    except Exception as exc:
        _raise_store_error(exc)


@router.post("/users/{user_id}/revoke")
def revoke_user(
    user_id: str,
    body: VersionRequest,
    session: Annotated[ChatSession, Depends(require_admin)],
):
    try:
        return {"user": user_store.update_user(
            user_id, session.email, status="disabled", expected_version=body.version,
            action="user_revoked", clear_binding=True,
        )}
    except Exception as exc:
        _raise_store_error(exc)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    session: Annotated[ChatSession, Depends(require_admin)],
    version: Annotated[int | None, Query(ge=1)] = None,
):
    try:
        user = user_store.delete_user(user_id, session.email, expected_version=version)
        return {"removed": True, "user": user}
    except Exception as exc:
        _raise_store_error(exc)


@router.get("/audit")
def access_audit(
    session: Annotated[ChatSession, Depends(require_admin)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    del session
    try:
        items = user_store.list_audit(limit)
        return {"events": items, "count": len(items)}
    except Exception as exc:
        _raise_store_error(exc)


@router.get("/usage")
def usage_report(
    session: Annotated[ChatSession, Depends(require_admin)],
    days: Annotated[int, Query(ge=0, le=3650)] = 30,
):
    if "usage:read" not in session.permissions:
        raise HTTPException(status_code=403, detail="Permissão de leitura de consumo necessária.")
    try:
        return user_store.usage_report(days)
    except Exception as exc:
        _raise_store_error(exc)
