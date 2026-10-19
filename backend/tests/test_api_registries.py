"""Docker Hub registries end to end: API, sync job, catalog overlay, deploy."""

import copy

import pytest

import catalog
from engine.fake import FakeEngine
from main import create_app
from services import jobs
from services.registries import registry_subject
from tests.conftest import TWO_SUBNETS, make_settings
from tests.hubfake import FakeHub, standard_labels

BASTION = standard_labels(
    "bastion",
    default="true",
    type_name="Bastion Host",
    type_role="router",
    type_label="BS",
    type_category="security",
    shell="/bin/sh",
)


@pytest.fixture
def hub() -> FakeHub:
    h = FakeHub()
    h.add("lab", "bastion", labels=BASTION)
    h.add("lab", "openplc", labels=standard_labels("plc"), platforms=("linux/amd64",))
    h.add("lab", "unmarked", description="just an image", labels=standard_labels("plc"))
    h.add("lab", "secret", private=True, labels=standard_labels("plc"))
    h.add("lab", "broken", labels={"io.ae3gis.schema": "1"})
    return h


@pytest.fixture
def app(tmp_path, fake_engine, hub):
    app = create_app(make_settings(tmp_path), fake_engine)
    app.state.registries.hub = hub.client
    return app


def add(client, url="https://hub.docker.com/u/lab"):
    r = client.post("/api/v1/registries", json={"url": url})
    assert r.status_code == 201, r.text
    return r.json()


def test_add_syncs_and_merges_into_the_catalog(client, wait_jobs, hub):
    row = add(client)
    assert row["namespace"] == "lab" and row["hub_url"] == "https://hub.docker.com/u/lab"
    assert row["active_job"]["kind"] == "sync_registry"
    wait_jobs()

    [reg] = client.get("/api/v1/registries").json()
    assert reg["last_job"]["status"] == "succeeded"
    assert reg["last_job"]["result"] == {
        "loaded": 2,
        "rejected": 1,
        "skipped": 2,
        "pending": 0,
        "warnings": 0,
    }
    assert (reg["repositories"], reg["skipped"], reg["pending"]) == (5, 2, [])
    assert {i["ref"]: i["type"] for i in reg["loaded"]} == {
        "lab/bastion:latest": "bastion",
        "lab/openplc:latest": "plc",
    }
    assert reg["rejected"][0]["repo"] == "broken"
    assert "io.ae3gis.type is required" in reg["rejected"][0]["reasons"][0]
    assert reg["synced_at"] is not None

    cat = client.get("/api/v1/catalog").json()
    assert cat["types"]["bastion"]["origin"] == "lab"
    assert cat["types"]["bastion"]["category"] == "security"
    assert "lab/openplc:latest" in cat["types"]["plc"]["images"]
    assert cat["images"]["lab/openplc:latest"]["source"] == {"kind": "registry", "registry": "lab"}

    images = client.get("/api/v1/images").json()
    assert [r["namespace"] for r in images["registries"]] == ["lab"]
    row = next(i for i in images["images"] if i["ref"] == "lab/openplc:latest")
    assert row["kind"] == "registry" and row["platforms"] == ["linux/amd64"]


def test_bad_and_duplicate_urls(client, wait_jobs):
    r = client.post("/api/v1/registries", json={"url": "https://ghcr.io/lab"})
    assert r.status_code == 422 and r.json()["code"] == "invalid_registry"
    add(client, "lab")
    r = client.post("/api/v1/registries", json={"url": "https://hub.docker.com/u/lab"})
    assert r.status_code == 409 and r.json()["code"] == "registry_exists"
    wait_jobs()


def test_an_unknown_namespace_fails_the_sync(client, wait_jobs):
    reg = add(client, "nobody")
    wait_jobs()
    [row] = client.get("/api/v1/registries").json()
    assert row["id"] == reg["id"] and row["last_job"]["status"] == "failed"
    assert "no namespace" in row["last_job"]["error"]
    assert row["loaded"] == []


def test_resync_reuses_labels_of_unchanged_images(client, wait_jobs, hub):
    reg = add(client)
    wait_jobs()
    gets = hub.manifest_gets
    assert client.post(f"/api/v1/registries/{reg['id']}/sync").status_code == 202
    wait_jobs()
    assert hub.manifest_gets == gets  # nothing changed: no pulls spent

    hub.namespaces["lab"]["openplc"].version += 1  # a new push
    client.post(f"/api/v1/registries/{reg['id']}/sync")
    wait_jobs()
    assert hub.manifest_gets == gets + 2  # its index and its platform manifest
    [row] = client.get("/api/v1/registries").json()
    assert len(row["loaded"]) == 2


def test_a_sync_stops_short_of_the_pull_limit(client, wait_jobs, hub):
    hub.remaining = 12  # the reserve is 10; each index read costs two
    reg = add(client)
    wait_jobs()
    [row] = client.get("/api/v1/registries").json()
    assert [i["repo"] for i in row["loaded"]] == ["bastion"]
    assert row["pending"] == ["broken", "openplc"] and row["pulls_remaining"] == 10
    assert row["last_job"]["result"]["pending"] == 2

    hub.remaining = 100
    client.post(f"/api/v1/registries/{reg['id']}/sync")
    wait_jobs()
    [row] = client.get("/api/v1/registries").json()
    assert {i["repo"] for i in row["loaded"]} == {"bastion", "openplc"} and row["pending"] == []


def test_remove_drops_the_registry_from_the_catalog(client, wait_jobs):
    reg = add(client)
    wait_jobs()
    assert "bastion" in client.get("/api/v1/catalog").json()["types"]

    data = copy.deepcopy(TWO_SUBNETS)
    data["sites"][0]["subnets"][0]["containers"][2]["type"] = "bastion"
    topo = client.post("/api/v1/topologies", json={"name": "t", "data": data}).json()
    codes = {d["code"] for d in topo["diagnostics"]}
    assert "type.unknown" not in codes

    assert client.delete(f"/api/v1/registries/{reg['id']}").status_code == 204
    assert client.get("/api/v1/registries").json() == []
    cat = client.get("/api/v1/catalog").json()
    assert (
        "bastion" not in cat["types"] and "lab/openplc:latest" not in cat["types"]["plc"]["images"]
    )
    diags = client.post(f"/api/v1/topologies/{topo['id']}/validate").json()
    assert "type.unknown" in {d["code"] for d in diags["diagnostics"]}


def test_remove_refuses_while_syncing(client, app, wait_jobs):
    reg = add(client)
    wait_jobs()
    with app.state.session_factory() as db:
        jobs.create_job(db, "sync_registry", subject=registry_subject(reg["id"]))
        db.commit()
    r = client.delete(f"/api/v1/registries/{reg['id']}")
    assert r.status_code == 409 and r.json()["code"] == "registry_busy"
    assert client.delete("/api/v1/registries/nope").status_code == 404


def test_the_catalog_is_restored_from_the_db_at_startup(client, wait_jobs, tmp_path):
    add(client)
    wait_jobs()
    catalog.set_registry_overlay(None)
    assert "bastion" not in catalog.node_types()
    create_app(make_settings(tmp_path), FakeEngine())  # no network: DB only
    assert catalog.node_types()["bastion"]["origin"] == "lab"


def test_plan_uses_a_registry_type_role_and_shell(client, wait_jobs):
    add(client)
    wait_jobs()
    data = copy.deepcopy(TWO_SUBNETS)
    data["sites"][0]["subnets"][0]["containers"][2]["type"] = "bastion"
    topo = client.post("/api/v1/topologies", json={"name": "t", "data": data}).json()
    plan = client.get(f"/api/v1/topologies/{topo['id']}/plan").json()["plan"]
    node = next(n for n in plan["nodes"] if n["id"] == "hA")
    assert (node["image"], node["role"], node["shell"]) == (
        "lab/bastion:latest",
        "router",
        "/bin/sh",
    )


def test_an_image_not_built_for_the_host_is_pulled_for_amd64(client, wait_jobs, fake_engine):
    fake_engine.platform = "linux/arm64"
    fake_engine.present_images = set()
    add(client)
    wait_jobs()
    data = copy.deepcopy(TWO_SUBNETS)
    host = data["sites"][0]["subnets"][0]["containers"][2]
    host.update(type="plc", image="lab/openplc:latest")
    topo = client.post("/api/v1/topologies", json={"name": "t", "data": data}).json()
    assert client.post(f"/api/v1/topologies/{topo['id']}/deploy").status_code == 202
    wait_jobs()

    assert client.get(f"/api/v1/topologies/{topo['id']}").json()["status"] == "deployed"
    assert fake_engine.pull_platforms["lab/openplc:latest"] == "linux/amd64"
    assert fake_engine.pull_platforms["kathara/frr"] is None
    events = client.get(f"/api/v1/topologies/{topo['id']}/events").json()
    emulated = [e for e in events if e["type"] == "deploy.images_emulated"]
    assert emulated and "lab/openplc:latest" in emulated[0]["data"]["refs"]
