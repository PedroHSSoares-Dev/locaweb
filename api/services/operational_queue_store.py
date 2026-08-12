"""Durable closed-loop queue for model-assisted operational investigations."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool


metadata = MetaData()

operational_alerts = Table(
    "operational_alerts",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("incident_ref", String(80), nullable=False, default=""),
    Column("title", String(180), nullable=False),
    Column("priority", String(4), nullable=False),
    Column("source_model_id", String(96), nullable=False),
    Column("risk_score", Float, nullable=True),
    Column("status", String(24), nullable=False),
    Column("team", String(100), nullable=False, default=""),
    Column("assignee_email", String(320), nullable=False, default=""),
    Column("recommended_action", Text, nullable=False, default=""),
    Column("action_taken", Text, nullable=False, default=""),
    Column("observed_result", Text, nullable=False, default=""),
    Column("created_by", String(320), nullable=False),
    Column("updated_by", String(320), nullable=False),
    Column("version", Integer, nullable=False, default=1),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("acknowledged_at", DateTime(timezone=True), nullable=True),
    Column("closed_at", DateTime(timezone=True), nullable=True),
)

operational_alert_audit = Table(
    "operational_alert_audit",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("alert_id", String(36), nullable=False),
    Column("actor_email", String(320), nullable=False),
    Column("action", String(48), nullable=False),
    Column("details_json", Text, nullable=False, default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

Index("ix_operational_alerts_status_priority", operational_alerts.c.status, operational_alerts.c.priority)
Index("ix_operational_alerts_updated", operational_alerts.c.updated_at)
Index("ix_operational_alert_audit_alert", operational_alert_audit.c.alert_id, operational_alert_audit.c.created_at)


class OperationalQueueError(RuntimeError):
    pass


class OperationalQueueUnavailable(OperationalQueueError):
    pass


class OperationalAlertNotFound(OperationalQueueError):
    pass


class OperationalAlertConflict(OperationalQueueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class OperationalQueueStore:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or self._default_database_url()
        self.engine = self._build_engine(self.database_url)
        self._schema_lock = threading.Lock()
        self._schema_ready = False
        self._ensure_schema()

    @staticmethod
    def _default_database_url() -> str:
        configured = os.getenv("CHAT_DATABASE_URL", "").strip()
        if configured:
            return configured
        path = Path(__file__).resolve().parents[2] / "data" / "chat" / "conversations.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"

    @staticmethod
    def _build_engine(database_url: str) -> Engine:
        if database_url.startswith("sqlite"):
            options: dict[str, Any] = {
                "connect_args": {"check_same_thread": False},
                "future": True,
            }
            if database_url == "sqlite:///:memory:":
                options["poolclass"] = StaticPool
            return create_engine(database_url, **options)
        return create_engine(database_url, pool_pre_ping=True, future=True)

    def _ensure_schema(self) -> None:
        if self._schema_ready:
            return
        with self._schema_lock:
            if self._schema_ready:
                return
            try:
                metadata.create_all(self.engine)
                self._harden_postgres_tables()
                self._schema_ready = True
            except SQLAlchemyError as exc:
                raise OperationalQueueUnavailable("Fila operacional indisponível.") from exc

    def _harden_postgres_tables(self) -> None:
        if self.engine.dialect.name != "postgresql":
            return
        with self.engine.begin() as connection:
            for table_name in ("operational_alerts", "operational_alert_audit"):
                connection.execute(text(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY'))
                connection.execute(text(f'REVOKE ALL ON TABLE "{table_name}" FROM PUBLIC'))
            public_roles = {
                str(row[0]) for row in connection.execute(text(
                    "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')"
                )).all()
            }
            for role_name in public_roles:
                for table_name in ("operational_alerts", "operational_alert_audit"):
                    connection.execute(text(
                        f'REVOKE ALL ON TABLE "{table_name}" FROM "{role_name}"'
                    ))

    @staticmethod
    def _row(row: Any) -> dict[str, Any]:
        data = dict(row._mapping if hasattr(row, "_mapping") else row)
        for key in ("created_at", "updated_at", "acknowledged_at", "closed_at"):
            data[key] = _iso(data.get(key))
        data["version"] = int(data.get("version") or 1)
        return data

    @staticmethod
    def _audit(connection, alert_id: str, actor: str, action: str, details: dict[str, Any]) -> None:
        connection.execute(insert(operational_alert_audit).values(
            id=str(uuid.uuid4()),
            alert_id=alert_id,
            actor_email=actor.strip().lower()[:320],
            action=action[:48],
            details_json=json.dumps(details, ensure_ascii=False, separators=(",", ":")),
            created_at=_now(),
        ))

    def list_alerts(self, *, status: str = "", priority: str = "", limit: int = 100) -> list[dict[str, Any]]:
        self._ensure_schema()
        statement = select(operational_alerts)
        if status:
            statement = statement.where(operational_alerts.c.status == status)
        if priority:
            statement = statement.where(operational_alerts.c.priority == priority)
        statement = statement.order_by(operational_alerts.c.updated_at.desc()).limit(limit)
        try:
            with self.engine.connect() as connection:
                return [self._row(row) for row in connection.execute(statement).all()]
        except SQLAlchemyError as exc:
            raise OperationalQueueUnavailable("Fila operacional indisponível.") from exc

    def summary(self) -> dict[str, Any]:
        self._ensure_schema()
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(select(
                    operational_alerts.c.status,
                    operational_alerts.c.priority,
                    func.count().label("count"),
                ).group_by(operational_alerts.c.status, operational_alerts.c.priority)).all()
        except SQLAlchemyError as exc:
            raise OperationalQueueUnavailable("Fila operacional indisponível.") from exc
        by_status: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for row in rows:
            count = int(row.count)
            by_status[str(row.status)] = by_status.get(str(row.status), 0) + count
            by_priority[str(row.priority)] = by_priority.get(str(row.priority), 0) + count
        return {"total": sum(by_status.values()), "by_status": by_status, "by_priority": by_priority}

    def create(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        self._ensure_schema()
        now = _now()
        alert_id = str(uuid.uuid4())
        record = {
            **values,
            "id": alert_id,
            "status": "new",
            "created_by": actor.strip().lower(),
            "updated_by": actor.strip().lower(),
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "acknowledged_at": None,
            "closed_at": None,
        }
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(operational_alerts).values(**record))
                self._audit(connection, alert_id, actor, "alert_created", {
                    "priority": values.get("priority"),
                    "source_model_id": values.get("source_model_id"),
                })
                row = connection.execute(select(operational_alerts).where(
                    operational_alerts.c.id == alert_id
                )).first()
                return self._row(row)
        except SQLAlchemyError as exc:
            raise OperationalQueueUnavailable("Não foi possível criar o alerta.") from exc

    def update(self, alert_id: str, changes: dict[str, Any], actor: str, version: int) -> dict[str, Any]:
        self._ensure_schema()
        try:
            with self.engine.begin() as connection:
                current_row = connection.execute(select(operational_alerts).where(
                    operational_alerts.c.id == alert_id
                )).first()
                if current_row is None:
                    raise OperationalAlertNotFound("Alerta operacional não encontrado.")
                current = dict(current_row._mapping)
                if int(current.get("version") or 1) != version:
                    raise OperationalAlertConflict("O alerta foi atualizado por outra sessão.")

                merged = {**current, **changes}
                if merged.get("status") == "resolved" and not (
                    str(merged.get("action_taken", "")).strip()
                    and str(merged.get("observed_result", "")).strip()
                ):
                    raise OperationalAlertConflict(
                        "Registre a ação tomada e o resultado observado antes de concluir."
                    )
                if merged.get("status") == "false_positive" and not str(
                    merged.get("observed_result", "")
                ).strip():
                    raise OperationalAlertConflict(
                        "Registre por que o alerta foi um falso positivo."
                    )

                now = _now()
                next_values = {
                    **changes,
                    "updated_by": actor.strip().lower(),
                    "updated_at": now,
                    "version": version + 1,
                }
                if changes.get("status") in {"acknowledged", "investigating"} and not current.get("acknowledged_at"):
                    next_values["acknowledged_at"] = now
                if changes.get("status") in {"resolved", "false_positive"}:
                    next_values["closed_at"] = now
                elif changes.get("status") and changes.get("status") not in {"resolved", "false_positive"}:
                    next_values["closed_at"] = None

                result = connection.execute(update(operational_alerts).where(
                    operational_alerts.c.id == alert_id,
                    operational_alerts.c.version == version,
                ).values(**next_values))
                if result.rowcount != 1:
                    raise OperationalAlertConflict("O alerta foi atualizado por outra sessão.")
                self._audit(connection, alert_id, actor, "alert_updated", {
                    "fields": sorted(changes),
                    "from_status": current.get("status"),
                    "to_status": merged.get("status"),
                })
                row = connection.execute(select(operational_alerts).where(
                    operational_alerts.c.id == alert_id
                )).first()
                return self._row(row)
        except (OperationalAlertNotFound, OperationalAlertConflict):
            raise
        except SQLAlchemyError as exc:
            raise OperationalQueueUnavailable("Não foi possível atualizar o alerta.") from exc

    def audit(self, alert_id: str, limit: int = 100) -> list[dict[str, Any]]:
        self._ensure_schema()
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(select(operational_alert_audit).where(
                    operational_alert_audit.c.alert_id == alert_id
                ).order_by(operational_alert_audit.c.created_at.desc()).limit(limit)).all()
        except SQLAlchemyError as exc:
            raise OperationalQueueUnavailable("Auditoria operacional indisponível.") from exc
        result = []
        for row in rows:
            data = dict(row._mapping)
            try:
                details = json.loads(data.get("details_json") or "{}")
            except json.JSONDecodeError:
                details = {}
            result.append({
                "id": data["id"],
                "action": data["action"],
                "actor_email": data["actor_email"],
                "details": details,
                "created_at": _iso(data.get("created_at")),
            })
        return result


operational_queue_store = OperationalQueueStore()
