"""Who is calling: FastAPI dependencies over ``services.accounts``.

Accounts are opt-in (``Settings.auth_required``). Off, every request is the
instructor (``OPEN_INSTRUCTOR``), the default for a local lab. On, a request
carries a session token (``POST /auth/login``) or the static instructor token:

- ``Authorization: Bearer <token>`` on any request;
- ``?token=`` on GET only (download links, the pcap stream ``curl`` reads), so
  a token in a URL can never change anything;
- the web-UI cookie (``POST /auth/webui-cookie``) on the node web-UI relay
  only, whose iframe pages cannot send a header.

WebSockets take ``?token=`` (browsers cannot set headers on an upgrade) and
check it with ``ws_identity`` before accepting. What an identity may do with a
topology or job is ``api.access``.

Settings are read from ``app.state.settings`` so a test app carries its own.
"""

from __future__ import annotations

import re

from fastapi import Depends, Header, Request, WebSocket
from sqlalchemy.orm import Session

from api.deps import get_db
from api.errors import Forbidden, Unauthorized
from config import Settings
from services.accounts import OPEN_INSTRUCTOR, Identity, resolve_token

WEBUI_COOKIE = "ae3gis_webui"
WEBUI_COOKIE_PATH = "/api/v1/topologies/"
_WEBUI_PATH = re.compile(r"^/api/v1/topologies/[^/]+/webui/")


def parse_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def _settings(request: Request | WebSocket) -> Settings:
    return request.app.state.settings


def request_token(request: Request, authorization: str | None) -> str | None:
    """The token a request authenticates with, under the rules above."""
    token = parse_bearer(authorization)
    if token is None and request.method in ("GET", "HEAD"):
        token = request.query_params.get("token") or None
    if token is None and _WEBUI_PATH.match(request.url.path):
        token = request.cookies.get(WEBUI_COOKIE) or None
    return token


def current_identity(
    request: Request,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Identity:
    """Any signed-in caller (everyone, with accounts off)."""
    settings = _settings(request)
    if not settings.auth_required:
        return OPEN_INSTRUCTOR
    identity = resolve_token(db, settings, request_token(request, authorization))
    if identity is None:
        raise Unauthorized()
    return identity


def require_instructor(identity: Identity = Depends(current_identity)) -> Identity:
    if not identity.is_instructor:
        raise Forbidden("Only the instructor can do this", code="instructor_only")
    return identity


def ws_identity(websocket: WebSocket, token: str | None, db: Session) -> Identity | None:
    """The caller of a WebSocket upgrade, or None (close with 4003)."""
    settings = _settings(websocket)
    if not settings.auth_required:
        return OPEN_INSTRUCTOR
    return resolve_token(db, settings, token)
