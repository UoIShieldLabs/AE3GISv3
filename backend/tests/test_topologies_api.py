import os
import tempfile

# Point the DB at a throwaway file BEFORE importing the app.
os.environ["AE3GIS_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

INSTR = {"Authorization": "Bearer test"}
EMPTY = {"name": "T", "data": {"name": "T", "sites": [], "siteConnections": []}}


def client() -> TestClient:
    return TestClient(main.app)


def test_health_and_catalog():
    with client() as c:
        assert c.get("/api/health").json()["status"] == "ok"
        cat = c.get("/api/catalog").json()
        assert "router" in cat["types"]


def test_create_requires_instructor():
    with client() as c:
        assert c.post("/api/topologies", json=EMPTY).status_code == 401


def test_crud_roundtrip():
    with client() as c:
        r = c.post("/api/topologies", headers=INSTR, json=EMPTY)
        assert r.status_code == 201
        tid = r.json()["id"]
        assert r.json()["engine_state"] is None
        assert c.get(f"/api/topologies/{tid}", headers=INSTR).status_code == 200
        # status of an undeployed topology is idle with no containers
        st = c.get(f"/api/topologies/{tid}/status", headers=INSTR).json()
        assert st["status"] == "idle" and st["containers"] == []
        # update
        r = c.put(f"/api/topologies/{tid}", headers=INSTR, json={"name": "Renamed"})
        assert r.json()["name"] == "Renamed"
        assert c.delete(f"/api/topologies/{tid}", headers=INSTR).status_code == 204
        assert c.get(f"/api/topologies/{tid}", headers=INSTR).status_code == 404


def test_import_json():
    with client() as c:
        payload = b'{"name":"Imp","topology":{"sites":[],"siteConnections":[]}}'
        r = c.post("/api/topologies/import-json", headers=INSTR,
                   files={"file": ("t.json", payload, "application/json")})
        assert r.status_code == 201
        assert r.json()["name"] == "Imp"
