"""API tokens: long-lived bearer tokens a staff member makes for an external
agent (Claude Code, OpenCode… over ``/api/v1/mcp``) or a script.

A token is a ``sessions`` row with ``purpose`` ``api`` and a label, so it
authenticates exactly like a sign-in (``accounts.resolve_token``) and carries
its owner's permissions, no more. It is shown once; only its hash is kept. A
password change or reset ends every session of the user, tokens included.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.errors import Conflict, Forbidden, NotFound
from db.models import UserSession, utcnow
from domain import passwords
from services.accounts import Identity

TTL_DAYS = 90
MAX_PER_USER = 20
# The public id of a token: a prefix of its hash (the hash is not a secret).
ID_CHARS = 16


def _check(identity: Identity) -> str:
    if not identity.user_id:
        raise Conflict("Accounts are off: the API needs no token", code="accounts_off")
    if not identity.is_staff:
        raise Forbidden("Only an instructor can do this", code="staff_only")
    return identity.user_id


def _out(row: UserSession) -> dict[str, Any]:
    return {
        "id": row.token_hash[:ID_CHARS],
        "label": row.label or "",
        "created_at": row.created_at,
        "expires_at": row.expires_at,
        "last_used_at": row.last_seen_at,
    }


def _rows(db: Session, user_id: str) -> list[UserSession]:
    return list(
        db.scalars(
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.purpose == "api")
            .order_by(UserSession.created_at.desc())
        )
    )


def list_tokens(db: Session, identity: Identity) -> list[dict[str, Any]]:
    return [_out(r) for r in _rows(db, _check(identity))]


def create_token(db: Session, identity: Identity, label: str) -> tuple[str, dict[str, Any]]:
    user_id = _check(identity)
    if len(_rows(db, user_id)) >= MAX_PER_USER:
        raise Conflict(f"You have {MAX_PER_USER} tokens; revoke one first", code="too_many_tokens")
    token = passwords.new_session_token()
    now = utcnow()
    row = UserSession(
        token_hash=passwords.token_hash(token),
        user_id=user_id,
        purpose="api",
        label=(label or "").strip()[:80] or "API token",
        created_at=now,
        expires_at=now + timedelta(days=TTL_DAYS),
        last_seen_at=None,
    )
    db.add(row)
    db.commit()
    return token, _out(row)


def revoke_token(db: Session, identity: Identity, token_id: str) -> None:
    user_id = _check(identity)
    for row in _rows(db, user_id):
        if row.token_hash[:ID_CHARS] == token_id:
            db.delete(row)
            db.commit()
            return
    raise NotFound("Token")
