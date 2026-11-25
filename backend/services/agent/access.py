"""Who gets the agent, in which mode, and who may read or drive a chat.

- **Mode:** ``full`` for staff (and everyone with accounts off); ``tutor`` for a
  student whose class has the tutor switched on; otherwise no agent.
- **Chats** follow the topology rule (``api.access.can_own``): the owner, the
  owner's instructor and any admin may read one; only the owner may send to it,
  approve its tool calls or stop it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Class, User
from services.accounts import Identity, teacher_of

if TYPE_CHECKING:
    from db.models import AgentChat
    from services.agent.tools import Mode


def tutor_enabled_for(db: Session, user_id: str | None) -> bool:
    """Whether the student's class has the tutor switched on."""
    if not user_id:
        return False
    value = db.scalar(
        select(Class.tutor_enabled).join(User, User.class_id == Class.id).where(User.id == user_id)
    )
    return bool(value)


def agent_mode(db: Session, identity: Identity) -> Mode | None:
    if identity.is_staff:
        return "full"
    if identity.is_student and tutor_enabled_for(db, identity.user_id):
        return "tutor"
    return None


def can_read_chat(db: Session, identity: Identity, chat: AgentChat) -> bool:
    if identity.is_admin:
        return True
    if chat.owner_id is None:
        return identity.user_id is None
    if chat.owner_id == identity.user_id:
        return True
    return identity.is_staff and teacher_of(db, chat.owner_id) == identity.user_id


def can_drive_chat(identity: Identity, chat: AgentChat) -> bool:
    return chat.owner_id == identity.user_id
