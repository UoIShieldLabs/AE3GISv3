"""Optional instructor token auth.

Auth is opt-in: with no `AE3GIS_INSTRUCTOR_TOKEN` configured every request is
allowed through, which is the default for a local lab. Setting the variable
turns the checks below back on for the REST API and the exec WebSocket.
Student/classroom auth is deferred.

`config` is imported as a module (not its values) so tests can patch the token.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import Header, HTTPException, Request

import config


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
    if not config.auth_required():
        return InstructorIdentity()
    if _parse_bearer(authorization) != config.INSTRUCTOR_TOKEN:
        raise HTTPException(401, "Instructor token required")
    return InstructorIdentity()


def require_any_auth(
    request: Request,
    authorization: str | None = Header(default=None),
) -> InstructorIdentity:
    if not config.auth_required():
        return InstructorIdentity()
    token = _parse_bearer(authorization) or request.query_params.get("token")
    if token != config.INSTRUCTOR_TOKEN:
        raise HTTPException(401, "Authorization required")
    return InstructorIdentity()


def valid_ws_token(token: str | None) -> bool:
    if not config.auth_required():
        return True
    return token == config.INSTRUCTOR_TOKEN
