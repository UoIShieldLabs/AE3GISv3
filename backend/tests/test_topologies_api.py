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
        r = c.post(
            "/api/topologies/import-json",
            headers=INSTR,
            files={"file": ("t.json", payload, "application/json")},
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Imp"


def test_unknown_fields_round_trip():
    """Backend stores topology data as opaque JSON: unknown fields survive verbatim,
    proving the frontend is not coupled to a backend schema."""
    with client() as c:
        payload = {
            "name": "Opaque",
            "data": {
                "name": "Opaque",
                "sites": [
                    {
                        "id": "s1",
                        "name": "S1",
                        "subnets": [
                            {
                                "id": "sub1",
                                "name": "N",
                                "cidr": "10.0.0.0/24",
                                "containers": [
                                    {
                                        "id": "c1",
                                        "name": "c",
                                        "type": "workstation",
                                        "ip": "10.0.0.5",
                                        "customField": 123,
                                        "future": {"nested": True},
                                    }
                                ],
                                "connections": [],
                            }
                        ],
                        "subnetConnections": [],
                    }
                ],
                "siteConnections": [],
                "brandNewTopLevelKey": "kept",
            },
        }
        r = c.post("/api/topologies", headers=INSTR, json=payload)
        assert r.status_code == 201
        tid = r.json()["id"]
        got = c.get(f"/api/topologies/{tid}", headers=INSTR).json()["data"]
        assert got["brandNewTopLevelKey"] == "kept"
        container = got["sites"][0]["subnets"][0]["containers"][0]
        assert container["customField"] == 123
        assert container["future"] == {"nested": True}
