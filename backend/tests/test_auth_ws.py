"""Opt-in auth on REST routes and on the exec WebSocket.

Also the template for WebSocket tests: ``client.websocket_connect`` raises
``WebSocketDisconnect`` (carrying the close code) when the server closes
before accepting.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from main import create_app
from tests.conftest import TWO_SUBNETS, make_settings

TOKEN = "s3cret"


@pytest.fixture
def secured(tmp_path, fake_engine):
    app = create_app(make_settings(tmp_path, instructor_token=TOKEN), fake_engine)
    with TestClient(app) as c:
        yield c


def _bearer(token: str = TOKEN) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_open_by_default(client):
    assert client.get("/api/v1/topologies").status_code == 200
    r = client.post("/api/v1/topologies", json={"name": "x", "data": TWO_SUBNETS})
    assert r.status_code == 201


def test_read_routes_take_bearer_or_query_token(secured):
    assert secured.get("/api/v1/topologies").status_code == 401
    assert secured.get("/api/v1/topologies", headers=_bearer("wrong")).status_code == 401
    assert secured.get("/api/v1/topologies", headers=_bearer()).status_code == 200
    assert secured.get(f"/api/v1/topologies?token={TOKEN}").status_code == 200


def test_write_routes_need_the_bearer_header(secured):
    body = {"name": "x", "data": TWO_SUBNETS}
    assert secured.post("/api/v1/topologies", json=body).status_code == 401
    # The query-param token is accepted for reads (downloads, streams) only.
    assert secured.post(f"/api/v1/topologies?token={TOKEN}", json=body).status_code == 401
    assert secured.post("/api/v1/topologies", json=body, headers=_bearer()).status_code == 201


def _exec_path(topology_id: str, container_id: str = "hA") -> str:
    return f"/api/v1/topologies/ws/{topology_id}/exec/{container_id}"


def test_exec_ws_rejects_a_bad_token(secured):
    r = secured.post(
        "/api/v1/topologies", json={"name": "x", "data": TWO_SUBNETS}, headers=_bearer()
    )
    tid = r.json()["id"]
    for suffix in ("", "?token=wrong"):
        with pytest.raises(WebSocketDisconnect) as exc:
            with secured.websocket_connect(_exec_path(tid) + suffix) as ws:
                ws.receive_text()
        assert exc.value.code == 4003


def test_exec_ws_explains_why_it_cannot_attach(secured):
    r = secured.post(
        "/api/v1/topologies", json={"name": "x", "data": TWO_SUBNETS}, headers=_bearer()
    )
    tid = r.json()["id"]
    cases = [
        ("missing", "hA", "topology not found"),
        (tid, "nope", "container not found"),
        (tid, "hA", "not deployed"),
    ]
    for topology_id, container_id, message in cases:
        with secured.websocket_connect(
            _exec_path(topology_id, container_id) + f"?token={TOKEN}"
        ) as ws:
            assert message in ws.receive_text()
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_text()
            assert exc.value.code == 4004
