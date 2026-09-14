"""Shared fixtures: an app per test with its own SQLite file and a FakeEngine."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Settings  # noqa: E402
from engine.fake import FakeEngine  # noqa: E402
from main import create_app  # noqa: E402

TWO_SUBNETS = {
    "name": "demo",
    "sites": [
        {
            "id": "s1",
            "name": "Site 1",
            "location": "",
            "position": {"x": 0, "y": 0},
            "subnets": [
                {
                    "id": "subA",
                    "name": "A",
                    "cidr": "10.0.1.0/24",
                    "gateway": "10.0.1.1",
                    "containers": [
                        {"id": "rA", "name": "Router A", "type": "router", "ip": "10.0.1.1"},
                        {"id": "swA", "name": "Switch A", "type": "switch", "ip": "10.0.1.2"},
                        {"id": "hA", "name": "Host A", "type": "workstation", "ip": "10.0.1.5"},
                    ],
                    "connections": [
                        {"id": "c1", "from": "swA", "to": "rA"},
                        {"id": "c2", "from": "swA", "to": "hA"},
                    ],
                },
                {
                    "id": "subB",
                    "name": "B",
                    "cidr": "10.0.2.0/24",
                    "gateway": "10.0.2.1",
                    "containers": [
                        {"id": "rB", "name": "Router B", "type": "router", "ip": "10.0.2.1"},
                        {"id": "swB", "name": "Switch B", "type": "switch", "ip": "10.0.2.2"},
                        {"id": "hB", "name": "Host B", "type": "workstation", "ip": "10.0.2.5"},
                    ],
                    "connections": [
                        {"id": "c3", "from": "swB", "to": "rB"},
                        {"id": "c4", "from": "swB", "to": "hB"},
                    ],
                },
            ],
            "subnetConnections": [{"id": "c5", "from": "subA", "to": "subB"}],
        }
    ],
    "siteConnections": [],
}


def make_settings(tmp_path: Path, **overrides) -> Settings:
    return Settings(data_dir=tmp_path, db_path=tmp_path / "test.db", engine="fake", **overrides)


@pytest.fixture
def fake_engine() -> FakeEngine:
    return FakeEngine()


@pytest.fixture
def app(tmp_path: Path, fake_engine: FakeEngine):
    return create_app(make_settings(tmp_path), fake_engine)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def wait_jobs(client, app):
    """Block until every background job scheduled by the app has finished."""

    def _wait() -> None:
        client.portal.call(app.state.runner.wait_idle)

    return _wait


@pytest.fixture
def topology(client) -> dict:
    r = client.post("/api/v1/topologies", json={"name": "demo", "data": TWO_SUBNETS})
    assert r.status_code == 201, r.text
    return r.json()
