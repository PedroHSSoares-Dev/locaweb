"""Authenticated operational alert workflow."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, model_validator

from api.services.chat_auth import ChatSession
from api.services.model_registry import ModelRegistryError, get_model_registry
from api.services.operational_queue_store import (
    OperationalAlertConflict,
    OperationalAlertNotFound,
    OperationalQueueUnavailable,
    operational_queue_store,
)


router = APIRouter(prefix="/operations", tags=["Operações"])
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
STATUSES = {"new", "acknowledged", "investigating", "resolved", "false_positive"}


def require_operator(request: Request) -> ChatSession:
    session = getattr(request.state, "session", None)
    if not isinstance(session, ChatSession):
        raise HTTPException(status_code=401, detail="Sessão de acesso ausente.")
    return session


def _source_models() -> set[str]:
    try:
        return {
            str(item.get("id")) for item in get_model_registry().get("models", [])
            if item.get("task") == "ola_risk_triage"
        } | {"manual"}
    except ModelRegistryError:
        return {"manual"}


class AlertCreateRequest(BaseModel):
    incident_ref: str = Field(default="", max_length=80)
    title: str = Field(min_length=4, max_length=180)
    priority: Literal["P2", "P3"]
    source_model_id: str = Field(default="manual", max_length=96)
    risk_score: float | None = Field(default=None, ge=0, le=1)
    team: str = Field(default="", max_length=100)
    assignee_email: str = Field(default="", max_length=320)
    recommended_action: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_fields(self):
        self.title = self.title.strip()
        self.incident_ref = self.incident_ref.strip()
        self.team = self.team.strip()
        self.assignee_email = self.assignee_email.strip().lower()
        self.recommended_action = self.recommended_action.strip()
        if self.source_model_id not in _source_models():
            raise ValueError("Modelo de origem não autorizado pelo registro canônico.")
        if self.assignee_email and not EMAIL_RE.match(self.assignee_email):
            raise ValueError("Email do responsável inválido.")
        return self


class AlertUpdateRequest(BaseModel):
    status: Literal["new", "acknowledged", "investigating", "resolved", "false_positive"] | None = None
    team: str | None = Field(default=None, max_length=100)
    assignee_email: str | None = Field(default=None, max_length=320)
    recommended_action: str | None = Field(default=None, max_length=2000)
    action_taken: str | None = Field(default=None, max_length=4000)
    observed_result: str | None = Field(default=None, max_length=4000)
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_fields(self):
        mutable = ("status", "team", "assignee_email", "recommended_action", "action_taken", "observed_result")
        if not any(getattr(self, field) is not None for field in mutable):
            raise ValueError("Informe ao menos uma alteração.")
        if self.assignee_email is not None:
            self.assignee_email = self.assignee_email.strip().lower()
            if self.assignee_email and not EMAIL_RE.match(self.assignee_email):
                raise ValueError("Email do responsável inválido.")
        for field in ("team", "recommended_action", "action_taken", "observed_result"):
            value = getattr(self, field)
            if value is not None:
                setattr(self, field, value.strip())
        return self


def _raise_store_error(exc: Exception) -> None:
    if isinstance(exc, OperationalAlertNotFound):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, OperationalAlertConflict):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, OperationalQueueUnavailable):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    raise exc


@router.get("/alerts")
def list_alerts(
    session: Annotated[ChatSession, Depends(require_operator)],
    status_filter: Annotated[str, Query(alias="status", max_length=24)] = "",
    priority: Annotated[str, Query(max_length=4)] = "",
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
):
    del session
    if status_filter and status_filter not in STATUSES:
        raise HTTPException(status_code=422, detail="Status inválido.")
    if priority and priority not in {"P2", "P3"}:
        raise HTTPException(status_code=422, detail="Prioridade inválida.")
    try:
        alerts = operational_queue_store.list_alerts(
            status=status_filter, priority=priority, limit=limit
        )
        return {"alerts": alerts, "count": len(alerts), "summary": operational_queue_store.summary()}
    except Exception as exc:
        _raise_store_error(exc)


@router.post("/alerts", status_code=status.HTTP_201_CREATED)
def create_alert(
    payload: AlertCreateRequest,
    session: Annotated[ChatSession, Depends(require_operator)],
):
    try:
        alert = operational_queue_store.create(payload.model_dump(), session.email)
        return {"alert": alert}
    except Exception as exc:
        _raise_store_error(exc)


@router.patch("/alerts/{alert_id}")
def update_alert(
    alert_id: str,
    payload: AlertUpdateRequest,
    session: Annotated[ChatSession, Depends(require_operator)],
):
    changes = payload.model_dump(exclude={"version"}, exclude_none=True)
    try:
        alert = operational_queue_store.update(alert_id, changes, session.email, payload.version)
        return {"alert": alert}
    except Exception as exc:
        _raise_store_error(exc)


@router.get("/alerts/{alert_id}/audit")
def alert_audit(
    alert_id: str,
    session: Annotated[ChatSession, Depends(require_operator)],
):
    del session
    try:
        return {"events": operational_queue_store.audit(alert_id)}
    except Exception as exc:
        _raise_store_error(exc)
