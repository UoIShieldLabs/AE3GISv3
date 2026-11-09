"""Shared fixtures: an app per test with its own SQLite file and a FakeEngine."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import catalog  # noqa: E402
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


@pytest.fixture(autouse=True)
def _builtin_catalog():
    """Registries merge into a process-wide catalog: each test starts and ends built-in."""
    catalog.set_registry_overlay(None)
    yield
    catalog.set_registry_overlay(None)


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


# ── classroom mode (accounts on) ────────────────────────────────────

INSTRUCTOR_PASSWORD = "teach-me-please"
STUDENT_PASSWORD = "student-pass-1"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class Classroom:
    """A TestClient on an accounts-on app, signed in as the instructor, that
    signs students up on demand (``student("alice")`` → their auth headers)."""

    def __init__(self, client: TestClient, app) -> None:
        self.client = client
        self.app = app
        r = client.post(
            "/api/v1/auth/login",
            json={"username": "instructor", "password": INSTRUCTOR_PASSWORD},
        )
        assert r.status_code == 200, r.text
        self.instructor = bearer(r.json()["token"])
        self._students: dict[str, dict[str, str]] = {}

    def open_signup(self) -> str:
        r = self.client.put("/api/v1/class", json={"signup_open": True}, headers=self.instructor)
        assert r.status_code == 200, r.text
        return r.json()["join_code"]

    def student(self, name: str) -> dict[str, str]:
        if name not in self._students:
            r = self.client.post(
                "/api/v1/auth/signup",
                json={
                    "username": name,
                    "password": STUDENT_PASSWORD,
                    "join_code": self.open_signup(),
                },
            )
            assert r.status_code == 201, r.text
            self._students[name] = bearer(r.json()["token"])
        return self._students[name]

    def create(self, headers: dict[str, str], name: str = "lab", data: dict | None = None) -> dict:
        r = self.client.post(
            "/api/v1/topologies", json={"name": name, "data": data or TWO_SUBNETS}, headers=headers
        )
        assert r.status_code == 201, r.text
        return r.json()

    def wait(self) -> None:
        self.client.portal.call(self.app.state.runner.wait_idle)


@pytest.fixture
def classroom_app(tmp_path: Path, fake_engine: FakeEngine):
    return create_app(make_settings(tmp_path, instructor_password=INSTRUCTOR_PASSWORD), fake_engine)


@pytest.fixture
def classroom(classroom_app):
    with TestClient(classroom_app) as c:
        yield Classroom(c, classroom_app)
