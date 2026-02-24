"""Simple token-based auth for instructor and student roles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from config import INSTRUCTOR_TOKEN
from database import get_db
from models import StudentSlot


@dataclass
class InstructorIdentity:
    role: Literal["instructor"] = "instructor"


@dataclass
class StudentIdentity:
    role: Literal["student"] = "student"
    topology_id: str = ""
    slot_id: str = ""


AuthIdentity = InstructorIdentity | StudentIdentity


def _parse_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def require_instructor(
    authorization: str | None = Header(default=None),
) -> InstructorIdentity:
    token = _parse_bearer(authorization)
    if token != INSTRUCTOR_TOKEN:
        raise HTTPException(401, "Instructor token required")
    return InstructorIdentity()


def require_any_auth(
    request: Request,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthIdentity:
    token = _parse_bearer(authorization)
    
    if not token:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(401, "Authorization header or token query parameter required")

    if token == INSTRUCTOR_TOKEN:
        return InstructorIdentity()

    slot = db.query(StudentSlot).filter(StudentSlot.join_code == token).first()
    if not slot:
        raise HTTPException(401, "Invalid token")
    return StudentIdentity(topology_id=slot.topology_id, slot_id=slot.id)


def validate_student_topology(identity: AuthIdentity, topology_id: str) -> None:
    """Raise 403 if a student is trying to access a topology that isn't theirs."""
    if isinstance(identity, StudentIdentity) and identity.topology_id != topology_id:
        raise HTTPException(403, "Access denied")
