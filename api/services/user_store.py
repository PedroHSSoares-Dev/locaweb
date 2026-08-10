"""Durable authorization repository for identities authenticated by Entra ID.

Email is used only to match an invitation on first login. After that, access is
bound to the immutable Microsoft subject pair ``tenant_id + object_id``.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.pool import StaticPool


metadata = MetaData()

app_users = Table(
    "app_users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(320), nullable=False),
    Column("email_normalized", String(320), nullable=False, unique=True),
    Column("role", String(16), nullable=False),
    Column("status", String(16), nullable=False),
    Column("entra_object_id", String(64), nullable=True),
    Column("entra_tenant_id", String(64), nullable=True),
    Column("is_owner", Boolean, nullable=False, default=False),
    Column("session_version", Integer, nullable=False, default=1),
    Column("invited_by", String(320), nullable=False, default=""),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("activated_at", DateTime(timezone=True), nullable=True),
    Column("last_login_at", DateTime(timezone=True), nullable=True),
    Column("disabled_at", DateTime(timezone=True), nullable=True),
    UniqueConstraint("entra_tenant_id", "entra_object_id", name="uq_app_users_entra_subject"),
)

user_access_audit = Table(
    "user_access_audit",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("actor_email", String(320), nullable=False),
    Column("action", String(48), nullable=False),
    Column("target_user_id", String(36), nullable=False),
    Column("target_email", String(320), nullable=False),
    Column("details_json", Text, nullable=False, default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

llm_usage_events = Table(
    "llm_usage_events",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("response_id", String(80), nullable=False, unique=True),
    Column("user_id", String(128), nullable=False),
    Column("provider", String(64), nullable=False),
    Column("model", String(128), nullable=False, default=""),
    Column("response_mode", String(24), nullable=False),
    Column("analysis_mode", String(16), nullable=False),
    Column("input_tokens", Integer, nullable=False, default=0),
    Column("output_tokens", Integer, nullable=False, default=0),
    Column("total_tokens", Integer, nullable=False, default=0),
    Column("reasoning_tokens", Integer, nullable=False, default=0),
    Column("cached_tokens", Integer, nullable=False, default=0),
    Column("saved_tokens", Integer, nullable=False, default=0),
    Column("cache_hit", Boolean, nullable=False, default=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

Index("ix_app_users_role_status", app_users.c.role, app_users.c.status)
Index("ix_user_access_audit_created", user_access_audit.c.created_at)
Index("ix_llm_usage_user_created", llm_usage_events.c.user_id, llm_usage_events.c.created_at)
Index("ix_llm_usage_created", llm_usage_events.c.created_at)


class UserStoreError(RuntimeError):
    pass


class UserStoreUnavailable(UserStoreError):
    pass


class UserNotFound(UserStoreError):
    pass


class UserConflict(UserStoreError):
    pass


class UserMutationForbidden(UserStoreError):
    pass


@dataclass(frozen=True)
class UserAccess:
    id: str
    email: str
    role: str
    status: str
    object_id: str
    tenant_id: str
    is_owner: bool
    session_version: int

    @property
    def permissions(self) -> tuple[str, ...]:
        if self.role == "admin":
            return ("chat:use", "users:read", "users:write", "usage:read")
        return ("chat:use",)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalized_email(email: str) -> str:
    return email.strip().lower()


def _subject(value: str) -> str:
    return value.strip().lower()


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class UserStore:
    """Synchronous repository used by the authentication middleware."""

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
                raise UserStoreUnavailable("Banco de autorização indisponível.") from exc

    def _harden_postgres_tables(self) -> None:
        """Keep authorization records inaccessible through public database roles."""
        if self.engine.dialect.name != "postgresql":
            return
        with self.engine.begin() as connection:
            for table_name in ("app_users", "user_access_audit", "llm_usage_events"):
                connection.execute(text(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY'))
                connection.execute(text(f'REVOKE ALL ON TABLE "{table_name}" FROM PUBLIC'))
            public_roles = {
                str(row[0])
                for row in connection.execute(text(
                    "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')"
                )).all()
            }
            for role_name in public_roles:
                # Values originate from the constant allowlist in the query above.
                for table_name in ("app_users", "user_access_audit", "llm_usage_events"):
                    connection.execute(text(
                        f'REVOKE ALL ON TABLE "{table_name}" FROM "{role_name}"'
                    ))

    @staticmethod
    def _row_dict(row: Any) -> dict[str, Any]:
        return dict(row._mapping if hasattr(row, "_mapping") else row)

    @classmethod
    def _access(cls, row: Any) -> UserAccess:
        data = cls._row_dict(row)
        return UserAccess(
            id=str(data["id"]),
            email=str(data["email"]),
            role=str(data["role"]),
            status=str(data["status"]),
            object_id=str(data.get("entra_object_id") or ""),
            tenant_id=str(data.get("entra_tenant_id") or ""),
            is_owner=bool(data.get("is_owner")),
            session_version=int(data.get("session_version") or 1),
        )

    @classmethod
    def _public(cls, row: Any) -> dict[str, Any]:
        data = cls._row_dict(row)
        return {
            "id": str(data["id"]),
            "email": str(data["email"]),
            "role": str(data["role"]),
            "status": str(data["status"]),
            "is_owner": bool(data.get("is_owner")),
            "version": int(data.get("session_version") or 1),
            "invited_by": str(data.get("invited_by") or ""),
            "created_at": _iso(data.get("created_at")),
            "updated_at": _iso(data.get("updated_at")),
            "activated_at": _iso(data.get("activated_at")),
            "last_login_at": _iso(data.get("last_login_at")),
            "disabled_at": _iso(data.get("disabled_at")),
        }

    @staticmethod
    def _audit(connection, actor: str, action: str, target: dict[str, Any], details: dict[str, Any] | None = None) -> None:
        connection.execute(insert(user_access_audit).values(
            id=str(uuid.uuid4()),
            actor_email=_normalized_email(actor)[:320],
            action=action[:48],
            target_user_id=str(target["id"]),
            target_email=str(target["email"]),
            details_json=json.dumps(details or {}, ensure_ascii=False, separators=(",", ":")),
            created_at=_now(),
        ))

    def sync_bootstrap_admins(self, emails: set[str]) -> None:
        """Create immutable owners once from the deployment bootstrap allowlist."""
        self._ensure_schema()
        try:
            with self.engine.begin() as connection:
                for raw_email in sorted(emails):
                    email = _normalized_email(raw_email)
                    if not email:
                        continue
                    row = connection.execute(select(app_users).where(
                        app_users.c.email_normalized == email
                    )).first()
                    if row is None:
                        now = _now()
                        values = {
                            "id": str(uuid.uuid4()), "email": email, "email_normalized": email,
                            "role": "admin", "status": "active", "is_owner": True,
                            "session_version": 1, "invited_by": "bootstrap:environment",
                            "created_at": now, "updated_at": now, "activated_at": now,
                        }
                        connection.execute(insert(app_users).values(**values))
                        self._audit(connection, "system", "bootstrap_owner_created", values)
                    # Existing records are never silently promoted or re-enabled.
                    # Bootstrap is an initial seed, not a recurring override of
                    # administrator decisions.
        except IntegrityError:
            # Multiple workers may seed the same owner during a cold deploy.
            # The unique email constraint elects one winner; the next lookup
            # observes the row and authorization can continue safely.
            return
        except SQLAlchemyError as exc:
            raise UserStoreUnavailable("Banco de autorização indisponível.") from exc

    def authorize_login(
        self,
        email: str,
        object_id: str,
        tenant_id: str,
        *,
        bootstrap_emails: set[str],
        allow_local_unlisted: bool = False,
    ) -> UserAccess:
        self.sync_bootstrap_admins(bootstrap_emails)
        normalized = _normalized_email(email)
        oid, tid = _subject(object_id), _subject(tenant_id)
        try:
            with self.engine.begin() as connection:
                row = connection.execute(select(app_users).where(
                    app_users.c.entra_tenant_id == tid,
                    app_users.c.entra_object_id == oid,
                )).first()
                if row is None:
                    invitation = connection.execute(select(app_users).where(
                        app_users.c.email_normalized == normalized
                    ).with_for_update()).first()
                    if invitation is None:
                        if allow_local_unlisted:
                            return UserAccess(
                                id=f"local:{normalized}", email=normalized, role="member", status="active",
                                object_id=oid, tenant_id=tid, is_owner=False, session_version=1,
                            )
                        raise UserNotFound("Acesso não autorizado.")
                    invitation_data = self._row_dict(invitation)
                    if invitation_data["status"] == "disabled":
                        raise UserNotFound("Acesso não autorizado.")
                    if invitation_data.get("entra_object_id") or invitation_data.get("entra_tenant_id"):
                        # A concurrent first-login request may have completed the
                        # same binding while this transaction waited for the row.
                        if (
                            _subject(str(invitation_data.get("entra_object_id") or "")) == oid
                            and _subject(str(invitation_data.get("entra_tenant_id") or "")) == tid
                            and invitation_data["status"] == "active"
                        ):
                            connection.execute(update(app_users).where(
                                app_users.c.id == invitation_data["id"]
                            ).values(last_login_at=_now(), updated_at=_now()))
                            row = connection.execute(select(app_users).where(
                                app_users.c.id == invitation_data["id"]
                            )).first()
                            return self._access(row)
                        raise UserNotFound("Acesso não autorizado.")
                    now = _now()
                    connection.execute(update(app_users).where(app_users.c.id == invitation_data["id"]).values(
                        entra_object_id=oid,
                        entra_tenant_id=tid,
                        status="active",
                        activated_at=invitation_data.get("activated_at") or now,
                        last_login_at=now,
                        updated_at=now,
                    ))
                    self._audit(connection, normalized, "identity_bound", invitation_data)
                    row = connection.execute(select(app_users).where(
                        app_users.c.id == invitation_data["id"]
                    )).first()
                else:
                    data = self._row_dict(row)
                    if data["status"] != "active":
                        raise UserNotFound("Acesso não autorizado.")
                    connection.execute(update(app_users).where(app_users.c.id == data["id"]).values(
                        last_login_at=_now(), updated_at=_now()
                    ))
                    row = connection.execute(select(app_users).where(app_users.c.id == data["id"])).first()
                return self._access(row)
        except IntegrityError as exc:
            raise UserConflict("Identidade já vinculada a outro acesso.") from exc
        except SQLAlchemyError as exc:
            raise UserStoreUnavailable("Banco de autorização indisponível.") from exc

    def authorize_session(
        self,
        user_id: str,
        object_id: str,
        tenant_id: str,
        session_version: int,
        *,
        bootstrap_emails: set[str],
        allow_local_unlisted: bool = False,
        email: str = "",
    ) -> UserAccess:
        self.sync_bootstrap_admins(bootstrap_emails)
        oid, tid = _subject(object_id), _subject(tenant_id)
        try:
            with self.engine.connect() as connection:
                row = connection.execute(select(app_users).where(
                    app_users.c.id == user_id,
                    app_users.c.entra_tenant_id == tid,
                    app_users.c.entra_object_id == oid,
                )).first()
            if row is None:
                if allow_local_unlisted and not bootstrap_emails and user_id == f"local:{_normalized_email(email)}":
                    return UserAccess(
                        id=user_id, email=_normalized_email(email), role="member", status="active",
                        object_id=oid, tenant_id=tid, is_owner=False, session_version=1,
                    )
                raise UserNotFound("Acesso não autorizado.")
            access = self._access(row)
            if access.status != "active" or access.session_version != session_version:
                raise UserNotFound("Sessão revogada.")
            return access
        except SQLAlchemyError as exc:
            raise UserStoreUnavailable("Banco de autorização indisponível.") from exc

    def list_users(self, *, q: str = "", role: str = "", status: str = "") -> list[dict[str, Any]]:
        self._ensure_schema()
        query = select(app_users)
        if q.strip():
            query = query.where(func.lower(app_users.c.email).contains(q.strip().lower()))
        if role:
            query = query.where(app_users.c.role == role)
        if status:
            query = query.where(app_users.c.status == status)
        query = query.order_by(app_users.c.is_owner.desc(), app_users.c.created_at.asc())
        try:
            with self.engine.connect() as connection:
                return [self._public(row) for row in connection.execute(query).all()]
        except SQLAlchemyError as exc:
            raise UserStoreUnavailable("Banco de autorização indisponível.") from exc

    def get_public(self, user_id: str) -> dict[str, Any]:
        try:
            with self.engine.connect() as connection:
                row = connection.execute(select(app_users).where(app_users.c.id == user_id)).first()
            if row is None:
                raise UserNotFound("Usuário não encontrado.")
            return self._public(row)
        except SQLAlchemyError as exc:
            raise UserStoreUnavailable("Banco de autorização indisponível.") from exc

    def invite(self, email: str, role: str, actor: str) -> dict[str, Any]:
        now = _now()
        normalized = _normalized_email(email)
        values = {
            "id": str(uuid.uuid4()), "email": normalized, "email_normalized": normalized,
            "role": role, "status": "pending", "is_owner": False, "session_version": 1,
            "invited_by": _normalized_email(actor), "created_at": now, "updated_at": now,
        }
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(app_users).values(**values))
                self._audit(connection, actor, "user_invited", values, {"role": role})
            return self.get_public(values["id"])
        except IntegrityError as exc:
            raise UserConflict("Este email já possui um acesso cadastrado.") from exc
        except SQLAlchemyError as exc:
            raise UserStoreUnavailable("Banco de autorização indisponível.") from exc

    @staticmethod
    def _ensure_admin_invariant(connection, target: dict[str, Any], new_role: str, new_status: str) -> None:
        loses_admin = target["role"] == "admin" and target["status"] == "active" and (
            new_role != "admin" or new_status != "active"
        )
        if not loses_admin:
            return
        active_admins = connection.execute(select(app_users.c.id).where(
            app_users.c.role == "admin", app_users.c.status == "active"
        ).with_for_update()).all()
        if len(active_admins) <= 1:
            raise UserMutationForbidden("A plataforma precisa manter ao menos um administrador ativo.")

    def update_user(
        self,
        user_id: str,
        actor: str,
        *,
        role: str | None = None,
        status: str | None = None,
        expected_version: int | None = None,
        action: str = "user_updated",
        clear_binding: bool = False,
    ) -> dict[str, Any]:
        try:
            with self.engine.begin() as connection:
                row = connection.execute(
                    select(app_users).where(app_users.c.id == user_id).with_for_update()
                ).first()
                if row is None:
                    raise UserNotFound("Usuário não encontrado.")
                target = self._row_dict(row)
                if expected_version is not None and int(target["session_version"]) != expected_version:
                    raise UserConflict("O acesso foi alterado por outra sessão. Atualize a lista.")
                new_role = role or str(target["role"])
                new_status = status or str(target["status"])
                changed = new_role != target["role"] or new_status != target["status"] or clear_binding
                if target.get("is_owner") and changed:
                    raise UserMutationForbidden("O administrador proprietário não pode ser alterado ou removido.")
                self._ensure_admin_invariant(connection, target, new_role, new_status)
                values: dict[str, Any] = {
                    "role": new_role, "status": new_status, "updated_at": _now(),
                    "disabled_at": _now() if new_status == "disabled" else None,
                }
                if changed:
                    values["session_version"] = int(target["session_version"]) + 1
                if clear_binding:
                    values.update(entra_object_id=None, entra_tenant_id=None, activated_at=None)
                connection.execute(update(app_users).where(app_users.c.id == user_id).values(**values))
                self._audit(connection, actor, action, target, {
                    "previous_role": target["role"], "role": new_role,
                    "previous_status": target["status"], "status": new_status,
                    "binding_cleared": clear_binding,
                })
            return self.get_public(user_id)
        except SQLAlchemyError as exc:
            raise UserStoreUnavailable("Banco de autorização indisponível.") from exc

    def delete_user(self, user_id: str, actor: str, expected_version: int | None = None) -> dict[str, Any]:
        # Soft revoke preserves both the access record and its audit history.
        return self.update_user(
            user_id, actor, status="disabled", expected_version=expected_version,
            action="user_access_removed", clear_binding=True,
        )

    def revoke_session(
        self,
        user_id: str,
        object_id: str,
        tenant_id: str,
        expected_version: int,
        actor: str,
    ) -> None:
        """Invalidate every token issued at the current user session version."""
        if user_id.startswith("local:"):
            return
        try:
            with self.engine.begin() as connection:
                row = connection.execute(select(app_users).where(
                    app_users.c.id == user_id,
                    app_users.c.entra_object_id == _subject(object_id),
                    app_users.c.entra_tenant_id == _subject(tenant_id),
                ).with_for_update()).first()
                if row is None:
                    raise UserNotFound("Acesso não autorizado.")
                target = self._row_dict(row)
                if int(target["session_version"]) != expected_version:
                    return
                connection.execute(update(app_users).where(app_users.c.id == user_id).values(
                    session_version=expected_version + 1,
                    updated_at=_now(),
                ))
                self._audit(connection, actor, "session_ended", target)
        except SQLAlchemyError as exc:
            raise UserStoreUnavailable("Banco de autorização indisponível.") from exc

    def list_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(
                    select(user_access_audit).order_by(user_access_audit.c.created_at.desc()).limit(limit)
                ).all()
            return [{
                "id": str((data := self._row_dict(row))["id"]),
                "actor_email": data["actor_email"], "action": data["action"],
                "target_user_id": data["target_user_id"], "target_email": data["target_email"],
                "details": json.loads(data.get("details_json") or "{}"),
                "created_at": _iso(data.get("created_at")),
            } for row in rows]
        except SQLAlchemyError as exc:
            raise UserStoreUnavailable("Banco de autorização indisponível.") from exc

    @staticmethod
    def _token_count(usage: dict[str, Any], field: str) -> int:
        try:
            return min(2_147_483_647, max(0, int(usage.get(field, 0) or 0)))
        except (TypeError, ValueError):
            return 0

    def record_usage(
        self,
        *,
        response_id: str,
        user_id: str,
        provider: str,
        model: str | None,
        response_mode: str,
        analysis_mode: str,
        usage: dict[str, Any] | None,
        cache_hit: bool,
    ) -> bool:
        """Persist provider-reported counters without storing prompts or answers."""
        counters = usage if isinstance(usage, dict) else {}
        input_tokens = self._token_count(counters, "input_tokens")
        output_tokens = self._token_count(counters, "output_tokens")
        reasoning_tokens = self._token_count(counters, "reasoning_tokens")
        cached_tokens = self._token_count(counters, "cached_tokens")
        if cache_hit:
            # A cache response performs no provider generation. Enforce zero
            # actual usage even if a caller accidentally replays old counters.
            input_tokens = output_tokens = reasoning_tokens = cached_tokens = 0
        # Reasoning tokens are a subset of output tokens in the OpenAI usage
        # contract and therefore must not be added to the total again.
        total_tokens = 0 if cache_hit else (
            self._token_count(counters, "total_tokens") or input_tokens + output_tokens
        )
        values = {
            "id": str(uuid.uuid4()),
            "response_id": response_id[:80],
            "user_id": user_id[:128],
            "provider": (provider or "unknown")[:64],
            "model": (model or "")[:128],
            "response_mode": (response_mode or "unknown")[:24],
            "analysis_mode": (analysis_mode or "fast")[:16],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "reasoning_tokens": reasoning_tokens,
            "cached_tokens": cached_tokens,
            "saved_tokens": self._token_count(counters, "saved_tokens"),
            "cache_hit": bool(cache_hit),
            "created_at": _now(),
        }
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(llm_usage_events).values(**values))
            return True
        except IntegrityError:
            # response_id is an idempotency key. A retry must never double-count.
            return False
        except SQLAlchemyError as exc:
            raise UserStoreUnavailable("Banco de telemetria indisponível.") from exc

    def usage_report(self, days: int = 30) -> dict[str, Any]:
        """Return per-user token consumption for an admin-selected UTC window."""
        since = _now() - timedelta(days=days) if days > 0 else None
        query = select(
            llm_usage_events.c.user_id,
            func.count(llm_usage_events.c.id).label("requests"),
            func.sum(llm_usage_events.c.input_tokens).label("input_tokens"),
            func.sum(llm_usage_events.c.output_tokens).label("output_tokens"),
            func.sum(llm_usage_events.c.total_tokens).label("total_tokens"),
            func.sum(llm_usage_events.c.reasoning_tokens).label("reasoning_tokens"),
            func.sum(llm_usage_events.c.cached_tokens).label("cached_tokens"),
            func.sum(llm_usage_events.c.saved_tokens).label("saved_tokens"),
            func.sum(func.cast(llm_usage_events.c.cache_hit, Integer)).label("cache_hits"),
        )
        if since is not None:
            query = query.where(llm_usage_events.c.created_at >= since)
        query = query.group_by(llm_usage_events.c.user_id)

        try:
            with self.engine.connect() as connection:
                aggregate_rows = connection.execute(query).all()
                tracked_since = connection.execute(select(func.min(llm_usage_events.c.created_at))).scalar()
                generated_rows = connection.execute(
                    select(
                        llm_usage_events.c.user_id,
                        func.count(llm_usage_events.c.id).label("generated_responses"),
                    ).where(
                        llm_usage_events.c.response_mode == "llm",
                        llm_usage_events.c.cache_hit.is_(False),
                        *((llm_usage_events.c.created_at >= since,) if since is not None else ()),
                    ).group_by(llm_usage_events.c.user_id)
                ).all()
        except SQLAlchemyError as exc:
            raise UserStoreUnavailable("Banco de telemetria indisponível.") from exc

        generated_by_user = {
            str(self._row_dict(row)["user_id"]): int(self._row_dict(row)["generated_responses"] or 0)
            for row in generated_rows
        }
        empty_metrics = {
            "requests": 0,
            "generated_responses": 0,
            "cache_hits": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "reasoning_tokens": 0,
            "cached_tokens": 0,
            "saved_tokens": 0,
        }
        metrics_by_user: dict[str, dict[str, int]] = {}
        for row in aggregate_rows:
            data = self._row_dict(row)
            user_id = str(data["user_id"])
            metrics_by_user[user_id] = {
                **empty_metrics,
                **{key: int(data.get(key) or 0) for key in empty_metrics if key != "generated_responses"},
                "generated_responses": generated_by_user.get(user_id, 0),
            }

        users = []
        totals = dict(empty_metrics)
        for user in self.list_users():
            metrics = metrics_by_user.get(str(user["id"]), dict(empty_metrics))
            users.append({
                "id": user["id"],
                "email": user["email"],
                "role": user["role"],
                "status": user["status"],
                "is_owner": user["is_owner"],
                **metrics,
            })
            for key in totals:
                totals[key] += metrics[key]
        users.sort(key=lambda item: (-item["total_tokens"], item["email"]))
        return {
            "period": {"days": days, "since": _iso(since)},
            "tracking_since": _iso(tracked_since),
            "totals": totals,
            "users": users,
        }


user_store = UserStore()
