"""Durable, cloud-agnostic conversation archive.

SQLite is the zero-configuration local default. Any PostgreSQL service can be
used in production by setting ``CHAT_DATABASE_URL``; the API and repository
contract remain unchanged.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    create_engine,
    delete,
    exists,
    func,
    insert,
    or_,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool


metadata = MetaData()

conversations = Table(
    "chat_conversations",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("owner", String(64), primary_key=True),
    Column("title", String(120), nullable=False),
    Column("title_auto", Boolean, nullable=False, default=True),
    Column("pinned", Boolean, nullable=False, default=False),
    Column("origin_route", String(64), nullable=False, default="/gestao"),
    Column("origin_label", String(64), nullable=False, default="GESTÃO"),
    Column("context_json", Text, nullable=False, default="{}"),
    Column("summary", Text, nullable=False, default=""),
    Column("summarized_message_count", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

messages = Table(
    "chat_messages",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("conversation_id", String(64), nullable=False),
    Column("owner", String(64), nullable=False),
    Column("role", String(12), nullable=False),
    Column("content", Text, nullable=False),
    Column("response_id", String(80), nullable=False, default=""),
    Column("metadata_json", Text, nullable=False, default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["conversation_id", "owner"],
        ["chat_conversations.id", "chat_conversations.owner"],
        ondelete="CASCADE",
    ),
)

Index("ix_chat_messages_owner_conversation", messages.c.owner, messages.c.conversation_id)
Index("ix_chat_messages_conversation_created", messages.c.conversation_id, messages.c.created_at)
Index("ix_chat_conversations_owner_updated", conversations.c.owner, conversations.c.updated_at)


class ConversationNotFound(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _decode(value: str | None, fallback: Any) -> Any:
    try:
        decoded = json.loads(value or "")
        return decoded
    except (json.JSONDecodeError, TypeError):
        return fallback


def _iso(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: str, limit: int) -> str:
    compact = re.sub(r"\s+", " ", re.sub(r"[#*_`>|]", " ", value)).strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[:max(1, limit - 1)].rstrip()}…"


def automatic_title(message: str) -> str:
    title = _clean_text(message, 72)
    return title or "Nova análise operacional"


def summarize_messages(rows: list[dict[str, Any]]) -> str:
    """Create an extractive, bounded recap without another paid LLM call."""
    lines: list[str] = []
    for row in rows:
        content = str(row.get("content", ""))
        if row.get("role") == "user":
            excerpt = _clean_text(content, 150)
            if excerpt:
                lines.append(f"Pergunta: {excerpt}")
        elif row.get("role") == "assistant":
            first_sentence = re.split(r"(?<=[.!?])\s+", content, maxsplit=1)[0]
            excerpt = _clean_text(first_sentence, 190)
            if excerpt:
                lines.append(f"Resposta registrada: {excerpt}")
    if not lines:
        return ""
    body = " · ".join(lines[-12:])
    return _clean_text(f"Resumo automático do histórico anterior: {body}", 1_800)


class ConversationStore:
    """Synchronous repository; FastAPI calls it through ``asyncio.to_thread``."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or self._default_database_url()
        self.engine = self._build_engine(self.database_url)
        metadata.create_all(self.engine)

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
            if database_url != "sqlite:///:memory:":
                Path(database_url.removeprefix("sqlite:///")).expanduser().parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
            options: dict[str, Any] = {
                "connect_args": {"check_same_thread": False},
                "future": True,
            }
            if database_url == "sqlite:///:memory:":
                options["poolclass"] = StaticPool
            return create_engine(database_url, **options)
        return create_engine(database_url, pool_pre_ping=True, future=True)

    @staticmethod
    def _conversation_dict(row: Any) -> dict[str, Any]:
        data = dict(row._mapping if hasattr(row, "_mapping") else row)
        return {
            "id": data["id"],
            "title": data["title"],
            "title_auto": bool(data["title_auto"]),
            "pinned": bool(data["pinned"]),
            "origin_route": data["origin_route"],
            "origin_label": data["origin_label"],
            "dashboard_context": _decode(data.get("context_json"), {}),
            "summary": data.get("summary", ""),
            "summarized_message_count": int(data.get("summarized_message_count", 0)),
            "created_at": _iso(data.get("created_at")),
            "updated_at": _iso(data.get("updated_at")),
        }

    @staticmethod
    def _message_dict(row: Any) -> dict[str, Any]:
        data = dict(row._mapping if hasattr(row, "_mapping") else row)
        return {
            "id": data["id"],
            "role": data["role"],
            "content": data["content"],
            "response_id": data.get("response_id", ""),
            "metadata": _decode(data.get("metadata_json"), {}),
            "created_at": _iso(data.get("created_at")),
        }

    def _owned_row(self, connection, owner: str, conversation_id: str):
        return connection.execute(select(conversations).where(and_(
            conversations.c.id == conversation_id,
            conversations.c.owner == owner,
        ))).first()

    def ensure(
        self,
        owner: str,
        conversation_id: str,
        dashboard_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self.engine.begin() as connection:
            row = self._owned_row(connection, owner, conversation_id)
            if row:
                return self._conversation_dict(row)
            now = _now()
            context = dashboard_context or {"route": "/gestao", "label": "GESTÃO", "filters": {}}
            connection.execute(insert(conversations).values(
                id=conversation_id,
                owner=owner,
                title="Nova análise operacional",
                title_auto=True,
                pinned=False,
                origin_route=str(context.get("route", "/gestao"))[:64],
                origin_label=str(context.get("label", "GESTÃO"))[:64],
                context_json=_json(context),
                summary="",
                summarized_message_count=0,
                created_at=now,
                updated_at=now,
            ))
            row = self._owned_row(connection, owner, conversation_id)
            return self._conversation_dict(row)

    def append_exchange(
        self,
        owner: str,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        *,
        response_id: str,
        metadata_value: dict[str, Any],
        dashboard_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.ensure(owner, conversation_id, dashboard_context)
        with self.engine.begin() as connection:
            conversation = self._owned_row(connection, owner, conversation_id)
            if not conversation:
                raise ConversationNotFound("Conversa não encontrada.")
            now = _now()
            existing_messages = int(connection.scalar(
                select(func.count()).select_from(messages).where(and_(
                    messages.c.owner == owner,
                    messages.c.conversation_id == conversation_id,
                ))
            ) or 0)
            connection.execute(insert(messages), [
                {
                    "id": uuid.uuid4().hex,
                    "conversation_id": conversation_id,
                    "owner": owner,
                    "role": "user",
                    "content": user_message[:12_000],
                    "response_id": "",
                    "metadata_json": "{}",
                    "created_at": now,
                },
                {
                    "id": uuid.uuid4().hex,
                    "conversation_id": conversation_id,
                    "owner": owner,
                    "role": "assistant",
                    "content": assistant_message[:24_000],
                    "response_id": response_id,
                    "metadata_json": _json(metadata_value),
                    "created_at": now + timedelta(microseconds=1),
                },
            ])
            changes: dict[str, Any] = {"updated_at": now}
            if existing_messages == 0 and bool(conversation._mapping["title_auto"]):
                changes["title"] = automatic_title(user_message)
            connection.execute(update(conversations).where(and_(
                conversations.c.id == conversation_id,
                conversations.c.owner == owner,
            )).values(**changes))
        self._refresh_summary(owner, conversation_id)
        return self.get(owner, conversation_id, message_limit=200)

    def _refresh_summary(self, owner: str, conversation_id: str) -> None:
        with self.engine.begin() as connection:
            rows = connection.execute(
                select(messages)
                .where(and_(messages.c.owner == owner, messages.c.conversation_id == conversation_id))
                .order_by(messages.c.created_at.asc(), messages.c.id.asc())
            ).fetchall()
            if len(rows) <= 8:
                return
            older = [self._message_dict(row) for row in rows[:-6]]
            summary = summarize_messages(older)
            connection.execute(update(conversations).where(and_(
                conversations.c.id == conversation_id,
                conversations.c.owner == owner,
            )).values(summary=summary, summarized_message_count=len(older)))

    def get(
        self,
        owner: str,
        conversation_id: str,
        *,
        message_limit: int = 200,
        message_offset: int = 0,
    ) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = self._owned_row(connection, owner, conversation_id)
            if not row:
                raise ConversationNotFound("Conversa não encontrada.")
            total = int(connection.scalar(select(func.count()).select_from(messages).where(and_(
                messages.c.owner == owner,
                messages.c.conversation_id == conversation_id,
            ))) or 0)
            message_rows = connection.execute(
                select(messages)
                .where(and_(messages.c.owner == owner, messages.c.conversation_id == conversation_id))
                .order_by(messages.c.created_at.asc(), messages.c.id.asc())
                .offset(max(0, message_offset))
                .limit(max(1, min(message_limit, 500)))
            ).fetchall()
            result = self._conversation_dict(row)
            result["messages"] = [self._message_dict(item) for item in message_rows]
            result["message_count"] = total
            return result

    def history(self, owner: str, conversation_id: str) -> list[dict[str, str]]:
        with self.engine.connect() as connection:
            conversation = self._owned_row(connection, owner, conversation_id)
            if not conversation:
                return []
            recent = connection.execute(
                select(messages.c.role, messages.c.content)
                .where(and_(messages.c.owner == owner, messages.c.conversation_id == conversation_id))
                .order_by(messages.c.created_at.desc(), messages.c.id.desc())
                .limit(6)
            ).fetchall()
            result: list[dict[str, str]] = []
            summary = str(conversation._mapping.get("summary", "") or "")
            if summary:
                result.append({"role": "assistant", "content": summary})
            result.extend(
                {"role": row.role, "content": row.content}
                for row in reversed(recent)
            )
            return result

    def list(self, owner: str, query: str = "", limit: int = 80) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            statement = select(conversations).where(conversations.c.owner == owner)
            normalized = query.strip()
            if normalized:
                pattern = f"%{normalized[:120]}%"
                message_match = exists(select(messages.c.id).where(and_(
                    messages.c.owner == owner,
                    messages.c.conversation_id == conversations.c.id,
                    messages.c.content.ilike(pattern),
                )))
                statement = statement.where(or_(conversations.c.title.ilike(pattern), message_match))
            rows = connection.execute(
                statement
                .order_by(conversations.c.pinned.desc(), conversations.c.updated_at.desc())
                .limit(max(1, min(limit, 200)))
            ).fetchall()
            output: list[dict[str, Any]] = []
            for row in rows:
                item = self._conversation_dict(row)
                last_message = connection.execute(
                    select(messages.c.content, messages.c.role)
                    .where(and_(messages.c.owner == owner, messages.c.conversation_id == item["id"]))
                    .order_by(messages.c.created_at.desc(), messages.c.id.desc())
                    .limit(1)
                ).first()
                item["preview"] = _clean_text(last_message.content, 150) if last_message else "Sem mensagens"
                item["last_role"] = last_message.role if last_message else ""
                item["message_count"] = int(connection.scalar(
                    select(func.count()).select_from(messages).where(and_(
                        messages.c.owner == owner,
                        messages.c.conversation_id == item["id"],
                    ))
                ) or 0)
                output.append(item)
            return output

    def update(
        self,
        owner: str,
        conversation_id: str,
        *,
        title: str | None = None,
        pinned: bool | None = None,
        dashboard_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        values: dict[str, Any] = {"updated_at": _now()}
        if title is not None:
            values.update(title=_clean_text(title, 120) or "Nova análise operacional", title_auto=False)
        if pinned is not None:
            values["pinned"] = pinned
        if dashboard_context is not None:
            values["context_json"] = _json(dashboard_context)
        with self.engine.begin() as connection:
            if not self._owned_row(connection, owner, conversation_id):
                raise ConversationNotFound("Conversa não encontrada.")
            connection.execute(update(conversations).where(and_(
                conversations.c.id == conversation_id,
                conversations.c.owner == owner,
            )).values(**values))
        return self.get(owner, conversation_id)

    def delete(self, owner: str, conversation_id: str) -> bool:
        with self.engine.begin() as connection:
            if not self._owned_row(connection, owner, conversation_id):
                return False
            connection.execute(delete(messages).where(and_(
                messages.c.owner == owner,
                messages.c.conversation_id == conversation_id,
            )))
            connection.execute(delete(conversations).where(and_(
                conversations.c.owner == owner,
                conversations.c.id == conversation_id,
            )))
            return True

    def response_metadata(self, owner: str, response_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(messages.c.metadata_json)
                .where(and_(
                    messages.c.owner == owner,
                    messages.c.response_id == response_id,
                    messages.c.role == "assistant",
                ))
                .limit(1)
            ).first()
            return _decode(row.metadata_json, {}) if row else None


conversation_store = ConversationStore()
