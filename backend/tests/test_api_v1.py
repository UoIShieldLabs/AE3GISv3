import copy

from fastapi.testclient import TestClient

from config import Settings
from engine.fake import FakeEngine
from main import create_app
from tests.conftest import TWO_SUBNETS, make_settings

EMPTY = {"name": "T", "sites": [], "siteConnections": []}


def test_health_and_catalog(client):
    h = client.get("/api/v1/system/health").json()
    assert h["status"] == "ok" and h["engine"] == "fake" and h["engine_ok"] is True
    assert h["auth_required"] is False
    assert "router" in client.get("/api/v1/catalog").json()["types"]


def test_crud_roundtrip_with_versions(client):
    r = client.post("/api/v1/topologies", json={"name": "T", "data": EMPTY})
    assert r.status_code == 201
    rec = r.json()
    tid, version = rec["id"], rec["version"]
    assert version == 1 and rec["engine_state"] is None and rec["diagnostics"] == []

    assert client.get(f"/api/v1/topologies/{tid}").status_code == 200
    r = client.put(f"/api/v1/topologies/{tid}", json={"name": "Renamed", "version": version})
    assert r.status_code == 200 and r.json()["name"] == "Renamed" and r.json()["version"] == 2

    # a stale version is refused
    r = client.put(f"/api/v1/topologies/{tid}", json={"name": "Again", "version": 1})
    assert r.status_code == 409
    assert r.json()["code"] == "version_conflict" and r.json()["current_version"] == 2
    # If-Match works the same way; no version at all still writes (last writer wins)
    assert (
        client.put(
            f"/api/v1/topologies/{tid}", json={"name": "Via header"}, headers={"If-Match": '"2"'}
        ).status_code
        == 200
    )
    assert client.put(f"/api/v1/topologies/{tid}", json={"name": "No version"}).status_code == 200

    summaries = client.get("/api/v1/topologies").json()
    assert summaries[0]["id"] == tid and summaries[0]["version"] == 4
    assert client.delete(f"/api/v1/topologies/{tid}").status_code == 204
    assert client.get(f"/api/v1/topologies/{tid}").status_code == 404
    assert client.get(f"/api/v1/topologies/{tid}").json()["code"] == "not_found"


def test_unknown_fields_round_trip(client):
    data = copy.deepcopy(TWO_SUBNETS)
    data["brandNewTopLevelKey"] = "kept"
    data["sites"][0]["subnets"][0]["containers"][0]["future"] = {"nested": True}
    tid = client.post("/api/v1/topologies", json={"name": "Opaque", "data": data}).json()["id"]
    got = client.get(f"/api/v1/topologies/{tid}").json()["data"]
    assert got["brandNewTopLevelKey"] == "kept"
    assert got["sites"][0]["subnets"][0]["containers"][0]["future"] == {"nested": True}


def test_save_never_rejected_but_reports_diagnostics(client):
    data = copy.deepcopy(TWO_SUBNETS)
    data["sites"][0]["subnets"][0]["containers"][2]["ip"] = "10.0.1.1"  # duplicate of the router
    r = client.post("/api/v1/topologies", json={"name": "Bad", "data": data})
    assert r.status_code == 201
    codes = {d["code"] for d in r.json()["diagnostics"]}
    assert "ip.duplicate" in codes
    v = client.post("/api/v1/topologies/validate", json={"data": data}).json()
    assert v["summary"]["errors"] >= 1
    tid = r.json()["id"]
    assert client.post(f"/api/v1/topologies/{tid}/validate").json()["summary"] == v["summary"]


def test_import_json(client):
    payload = b'{"name":"Imp","topology":{"sites":[],"siteConnections":[]}}'
    r = client.post(
        "/api/v1/topologies/import-json", files={"file": ("t.json", payload, "application/json")}
    )
    assert r.status_code == 201 and r.json()["name"] == "Imp"
    r = client.post(
        "/api/v1/topologies/import-json",
        files={"file": ("t.json", b"not json", "application/json")},
    )
    assert r.status_code == 422 and r.json()["code"] == "invalid_json"


def test_plan_export_and_context(client, topology):
    tid = topology["id"]
    plan = client.get(f"/api/v1/topologies/{tid}/plan").json()["plan"]
    assert {n["id"] for n in plan["nodes"]} == {"rA", "swA", "hA", "rB", "swB", "hB"}

    spec = client.get(f"/api/v1/topologies/{tid}/export?format=labspec").json()
    assert (
        spec["labspec_version"] == 1 and spec["topology"]["id"] == tid and len(spec["nodes"]) == 6
    )

    r = client.get(f"/api/v1/topologies/{tid}/export?format=kathara")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    r = client.get(f"/api/v1/topologies/{tid}/export?format=containerlab")
    assert r.status_code == 200 and r.headers["content-disposition"].endswith('containerlab.zip"')
    assert client.get(f"/api/v1/topologies/{tid}/export?format=nope").status_code == 422

    ctx = client.get(f"/api/v1/topologies/{tid}/context").json()
    assert (
        ctx["topology"]["id"] == tid
        and ctx["runtime"]["status"] == "idle"
        and "nodes" in ctx["plan"]
    )


def test_presets_list_and_load(client):
    presets = client.get("/api/v1/presets").json()["presets"]
    assert presets and presets[0]["id"] == "two-subnet-demo"
    r = client.post("/api/v1/presets/two-subnet-demo/load")
    assert r.status_code == 201 and r.json()["name"]
    assert client.get("/api/v1/presets/../etc").status_code == 404


def test_auth_open_by_default_and_enforced_when_configured(tmp_path):
    with TestClient(create_app(make_settings(tmp_path), FakeEngine())) as c:
        assert c.post("/api/v1/topologies", json={"name": "T", "data": EMPTY}).status_code == 201

    settings = Settings(
        data_dir=tmp_path / "b",
        db_path=tmp_path / "b" / "t.db",
        engine="fake",
        instructor_token="s3cret",
    )
    with TestClient(create_app(settings, FakeEngine())) as c:
        assert c.get("/api/v1/topologies").status_code == 401
        assert c.get("/api/v1/topologies").json()["code"] == "unauthorized"
        assert c.post("/api/v1/topologies", json={"name": "T", "data": EMPTY}).status_code == 401
        assert (
            c.get("/api/v1/topologies", headers={"Authorization": "Bearer nope"}).status_code == 401
        )
        assert (
            c.get("/api/v1/topologies", headers={"Authorization": "Bearer s3cret"}).status_code
            == 200
        )
        assert c.get("/api/v1/topologies?token=s3cret").status_code == 200
        assert c.get("/api/v1/system/health").json()["auth_required"] is True
