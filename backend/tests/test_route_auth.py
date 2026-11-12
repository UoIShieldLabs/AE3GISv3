"""Every /api/v1 route asks who is calling, unless it is meant to be public.

A new route without ``current_identity`` (directly or through
``require_instructor`` / ``api.access``) fails here, so classroom mode cannot
grow an unauthenticated hole by accident.
"""

from __future__ import annotations

import inspect

from fastapi import routing
from fastapi.routing import APIRoute, APIWebSocketRoute

from auth import current_identity

PUBLIC = {
    ("GET", "/api/v1/system/health"),
    ("GET", "/api/v1/catalog"),
    ("GET", "/api/v1/presets"),
    ("GET", "/api/v1/presets/{preset_id}"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/signup"),
    ("POST", "/api/v1/auth/logout"),
}


def _routes(app):
    """(effective path, route) for every route, through included routers."""
    if hasattr(routing, "iter_route_contexts"):  # FastAPI >= 0.140
        for ctx in routing.iter_route_contexts(app.routes):
            yield ctx.path, ctx.original_route
    else:  # pragma: no cover - older FastAPI flattens app.routes itself
        for route in app.routes:
            yield getattr(route, "path", ""), route


def _calls(dependant):
    yield dependant.call
    for dep in dependant.dependencies:
        yield from _calls(dep)


def test_every_route_resolves_the_caller(app):
    unguarded, checked = [], 0
    for path, route in _routes(app):
        if isinstance(route, APIRoute) and path.startswith("/api/v1"):
            checked += 1
            guarded = current_identity in set(_calls(route.dependant))
            for method in route.methods:
                if not guarded and (method, path) not in PUBLIC:
                    unguarded.append((method, path))
    assert checked > 80  # the walk really saw the API
    assert unguarded == []


def test_public_routes_are_still_there(app):
    paths = {(m, p) for p, r in _routes(app) if isinstance(r, APIRoute) for m in r.methods}
    assert PUBLIC <= paths


def test_every_websocket_checks_access(app):
    sockets = [r for _, r in _routes(app) if isinstance(r, APIWebSocketRoute)]
    assert len(sockets) == 6
    for route in sockets:
        source = inspect.getsource(route.endpoint)
        assert "ws_guard(" in source or "ws_access(" in source, route.path
