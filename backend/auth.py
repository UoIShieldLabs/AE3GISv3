"""Optional instructor token auth.

Auth is opt-in: with no ``AE3GIS_INSTRUCTOR_TOKEN`` configured every request is
allowed through, which is the default for a local lab. Setting the variable
turns the checks below back on for the REST API and the exec WebSocket.
Student/classroom auth is deferred.

Settings are read from ``request.app.state.settings`` so an app built for tests
can carry its own token.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import Header, HTTPException, Request, WebSocket

from config import Settings


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


def _settings(request: Request | WebSocket) -> Settings:
    return request.app.state.settings


def require_instructor(
    request: Request, authorization: str | None = Header(default=None)
) -> InstructorIdentity:
    settings = _settings(request)
    if not settings.auth_required:
        return InstructorIdentity()
    if _parse_bearer(authorization) != settings.instructor_token:
        raise HTTPException(401, "Instructor token required")
    return InstructorIdentity()


def require_any_auth(
    request: Request, authorization: str | None = Header(default=None)
) -> InstructorIdentity:
    settings = _settings(request)
    if not settings.auth_required:
        return InstructorIdentity()
    token = _parse_bearer(authorization) or request.query_params.get("token")
    if token != settings.instructor_token:
        raise HTTPException(401, "Authorization required")
    return InstructorIdentity()


def valid_ws_token(websocket: WebSocket, token: str | None) -> bool:
    settings = _settings(websocket)
    if not settings.auth_required:
        return True
    return token == settings.instructor_token
