"""Instructor token auth.

Student/classroom auth is deferred in this foundation pass; only the instructor
bearer token is honoured. WebSocket routes accept the token via `?token=`
because browsers cannot set headers on the upgrade request.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import Header, HTTPException, Request

from config import INSTRUCTOR_TOKEN


@dataclass
class InstructorIdentity:
    role: Literal["instructor"] = "instructor"


def _parse_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def require_instructor(authorization: str | None = Header(default=None)) -> InstructorIdentity:
    if _parse_bearer(authorization) != INSTRUCTOR_TOKEN:
        raise HTTPException(401, "Instructor token required")
    return InstructorIdentity()


def require_any_auth(
    request: Request,
    authorization: str | None = Header(default=None),
) -> InstructorIdentity:
    token = _parse_bearer(authorization) or request.query_params.get("token")
    if token != INSTRUCTOR_TOKEN:
        raise HTTPException(401, "Authorization required")
    return InstructorIdentity()


def valid_ws_token(token: str | None) -> bool:
    return token == INSTRUCTOR_TOKEN
