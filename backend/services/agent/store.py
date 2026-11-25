"""Chats and their messages in the database (append-only)."""

from __future__ import annotations

import threading
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import AgentChat, AgentMessage, utcnow
from services.agent.llm.base import Message

DEFAULT_TITLE = "New chat"
# Messages are numbered per chat; the runner and request threads both append.
_append_lock = threading.Lock()


def create_chat(
    db: Session, *, owner_id: str | None, mode: str, topology_id: str | None = None, title: str = ""
) -> AgentChat:
    chat = AgentChat(
        owner_id=owner_id,
        mode=mode,
        topology_id=topology_id,
        title=(title or "").strip()[:120] or DEFAULT_TITLE,
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def messages(db: Session, chat_id: str, *, after: int = 0) -> list[AgentMessage]:
    stmt = (
        select(AgentMessage)
        .where(AgentMessage.chat_id == chat_id, AgentMessage.seq > after)
        .order_by(AgentMessage.seq)
    )
    return list(db.scalars(stmt))


def append(
    db: Session,
    chat_id: str,
    role: str,
    content: dict[str, Any],
    *,
    raw: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> AgentMessage:
    with _append_lock:
        top = db.scalar(select(func.max(AgentMessage.seq)).where(AgentMessage.chat_id == chat_id))
        msg = AgentMessage(
            chat_id=chat_id,
            seq=(top or 0) + 1,
            role=role,
            content=content,
            provider_raw=raw,
            job_id=job_id,
        )
        db.add(msg)
        chat = db.get(AgentChat, chat_id)
        if chat is not None:
            chat.updated_at = utcnow()
        db.commit()
        db.refresh(msg)
        return msg


def message_out(m: AgentMessage) -> dict[str, Any]:
    content = dict(m.content or {})
    content.pop("note", None)  # the model-facing context line; the UI shows `context`
    return {
        "id": m.id,
        "seq": m.seq,
        "role": m.role,
        "content": content,
        "job_id": m.job_id,
        "created_at": m.created_at,
    }


def history(db: Session, chat_id: str) -> list[Message]:
    """The chat as the model sees it: each user message carries its context line."""
    out: list[Message] = []
    for m in messages(db, chat_id):
        content = dict(m.content or {})
        if m.role == "user" and content.get("note"):
            content = {"text": f"{content['note']}\n\n{content.get('text') or ''}"}
        out.append(Message(role=m.role, content=content, raw=m.provider_raw))  # type: ignore[arg-type]
    return out


def title_from(text: str) -> str:
    line = " ".join((text or "").split())
    return (line[:60] + "…") if len(line) > 60 else (line or DEFAULT_TITLE)
