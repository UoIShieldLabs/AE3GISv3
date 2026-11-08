"""Saved lab state: save & destroy, resume on deploy, discard."""

from __future__ import annotations

import copy
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import command

from domain import saved_state
from domain.plan import LabPlan, NodePlan
from tests.test_migrations import alembic_config

# ── domain ──


def _plan() -> LabPlan:
    return LabPlan(
        name="lab",
        nodes=[
            NodePlan(id="a", name="A", type="workstation", role="host", image="img:a"),
            NodePlan(id="b", name="B", type="workstation", role="host", image="img:b2"),
            NodePlan(id="c", name="C", type="workstation", role="host", image="img:c"),
            NodePlan(id="d", name="D", type="workstation", role="host", image="img:d"),
        ],
    )


def test_apply_resumes_matching_nodes_and_says_why_others_start_fresh():
    saved = saved_state.make(
        {"a": "snap:a", "b": "snap:b", "c": "snap:c", "gone": "snap:gone"},
        {"a": "img:a", "b": "img:b1", "c": "img:c", "gone": "img:x"},
        deployed_version=3,
        now=datetime(2026, 11, 8, tzinfo=UTC),
    )
    plan = _plan()
    out = saved_state.apply(plan, saved, {"snap:a": True, "snap:b": True, "snap:c": False})
    by_id = {n.id: n for n in plan.nodes}
    assert out.applied == ["a"]
    assert by_id["a"].image == "snap:a"
    assert by_id["a"].startup[-1] == saved_state.RESTORE_COMMAND
    assert "image changed" in out.skipped["b"] and by_id["b"].image == "img:b2"
    assert "missing" in out.skipped["c"] and by_id["c"].image == "img:c"
    assert by_id["d"].image == "img:d" and "d" not in out.skipped
    assert saved_state.summary(saved) == {"created_at": "2026-11-08T00:00:00+00:00", "nodes": 4}
    assert saved_state.refs(saved) == ["snap:a", "snap:b", "snap:c", "snap:gone"]


def test_empty_or_malformed_saved_state_is_ignored():
    for raw in (None, {}, {"nodes": "x"}, {"nodes": {"a": {"ref": ""}}}):
        assert saved_state.summary(raw) is None
        assert saved_state.refs(raw) == []
        assert saved_state.apply(_plan(), raw, {}).applied == []


def test_repository_and_tag_are_valid_docker_names():
    assert saved_state.repository("ABCDEF0123456789") == "ae3gis.local/snapshot/abcdef012345"
    assert saved_state.tag_suffix(datetime(2026, 1, 2, 3, 4, 5)) == "20260102t030405"


# ── API ──


def _deploy(client, wait_jobs, tid: str) -> None:
    assert client.post(f"/api/v1/topologies/{tid}/deploy").status_code == 202
    wait_jobs()
    assert client.get(f"/api/v1/topologies/{tid}/runtime").json()["status"] == "deployed"


def _job(client, jid: str) -> dict:
    return client.get(f"/api/v1/jobs/{jid}").json()


def test_save_and_destroy_then_deploy_resumes(client, topology, wait_jobs, fake_engine):
    tid = topology["id"]
    _deploy(client, wait_jobs, tid)
    job = client.post(f"/api/v1/topologies/{tid}/destroy?save=true").json()
    wait_jobs()
    done = _job(client, job["id"])
    assert done["status"] == "succeeded", done
    assert [s["name"] for s in done["steps"]] == ["stop", "save", "undeploy", "verify"]

    rt = client.get(f"/api/v1/topologies/{tid}/runtime").json()
    assert rt["status"] == "idle"
    assert rt["saved"]["nodes"] == 6
    assert client.get(f"/api/v1/topologies/{tid}").json()["saved"]["nodes"] == 6
    first_refs = set(fake_engine.snapshots)
    assert len(first_refs) == 6
    assert all(r.startswith(saved_state.repository(tid) + ":") for r in first_refs)

    _deploy(client, wait_jobs, tid)
    lab = next(iter(fake_engine.labs.values()))
    images = {n.id: n.image for n in lab.plan.nodes}
    assert set(images.values()) == first_refs
    host = next(n for n in lab.plan.nodes if n.id == "hA")
    assert host.startup[-1] == saved_state.RESTORE_COMMAND
    # The base images, not the snapshots, are what the next save records.
    state = client.get(f"/api/v1/topologies/{tid}").json()["engine_state"]
    assert not any(v.startswith(saved_state.REPO_PREFIX) for v in state["base_images"].values())
    events = client.get(f"/api/v1/topologies/{tid}/events").json()
    assert any(e["type"] == "deploy.saved_state_restored" for e in events)


def test_saving_again_replaces_the_previous_images(
    client, topology, wait_jobs, fake_engine, monkeypatch
):
    tid = topology["id"]
    _deploy(client, wait_jobs, tid)
    client.post(f"/api/v1/topologies/{tid}/destroy?save=true")
    wait_jobs()
    first = set(fake_engine.snapshots)
    _deploy(client, wait_jobs, tid)
    # Saves within the same second would share tags; force distinct ones.
    monkeypatch.setattr(saved_state, "tag_suffix", lambda now: "later")
    client.post(f"/api/v1/topologies/{tid}/destroy?save=true")
    wait_jobs()
    assert set(fake_engine.removed_images) == first
    assert all(r.endswith("-later") for r in fake_engine.snapshots)


def test_destroy_without_saving_discards_the_earlier_save(client, topology, wait_jobs, fake_engine):
    tid = topology["id"]
    _deploy(client, wait_jobs, tid)
    client.post(f"/api/v1/topologies/{tid}/destroy?save=true")
    wait_jobs()
    refs = set(fake_engine.snapshots)
    _deploy(client, wait_jobs, tid)
    client.post(f"/api/v1/topologies/{tid}/destroy")
    wait_jobs()
    assert client.get(f"/api/v1/topologies/{tid}").json()["saved"] is None
    assert set(fake_engine.removed_images) == refs
    _deploy(client, wait_jobs, tid)
    lab = next(iter(fake_engine.labs.values()))
    assert not any(n.image.startswith(saved_state.REPO_PREFIX) for n in lab.plan.nodes)


def test_a_failed_save_leaves_the_lab_deployed(client, topology, wait_jobs, fake_engine):
    tid = topology["id"]
    _deploy(client, wait_jobs, tid)
    fake_engine.fail_snapshot = RuntimeError("disk full")
    job = client.post(f"/api/v1/topologies/{tid}/destroy?save=true").json()
    wait_jobs()
    assert _job(client, job["id"])["status"] == "failed"
    rt = client.get(f"/api/v1/topologies/{tid}/runtime").json()
    assert rt["status"] == "deployed"
    assert rt["saved"] is None
    assert len(fake_engine.labs) == 1


def test_save_needs_a_deployed_lab(client, topology):
    r = client.post(f"/api/v1/topologies/{topology['id']}/destroy?save=true")
    assert r.status_code == 409


def test_nodes_whose_image_changed_start_fresh(client, topology, wait_jobs, fake_engine):
    tid = topology["id"]
    _deploy(client, wait_jobs, tid)
    client.post(f"/api/v1/topologies/{tid}/destroy?save=true")
    wait_jobs()
    rec = client.get(f"/api/v1/topologies/{tid}").json()
    data = copy.deepcopy(rec["data"])
    data["sites"][0]["subnets"][0]["containers"][2]["image"] = "alpine:3.20"  # hA
    r = client.put(
        f"/api/v1/topologies/{tid}", json={"name": "demo", "data": data, "version": rec["version"]}
    )
    assert r.status_code == 200, r.text
    _deploy(client, wait_jobs, tid)
    lab = next(iter(fake_engine.labs.values()))
    images = {n.id: n.image for n in lab.plan.nodes}
    assert images["hA"] == "alpine:3.20"
    assert images["hB"].startswith(saved_state.REPO_PREFIX)
    events = client.get(f"/api/v1/topologies/{tid}/events").json()
    assert any(e["type"] == "deploy.saved_state_skipped" for e in events)


def test_discard_removes_the_images_and_deploy_starts_fresh(
    client, topology, wait_jobs, fake_engine
):
    tid = topology["id"]
    _deploy(client, wait_jobs, tid)
    assert client.delete(f"/api/v1/topologies/{tid}/saved-state").status_code == 409
    client.post(f"/api/v1/topologies/{tid}/destroy?save=true")
    wait_jobs()
    refs = set(fake_engine.snapshots)
    assert client.delete(f"/api/v1/topologies/{tid}/saved-state").status_code == 204
    assert set(fake_engine.removed_images) == refs
    assert client.get(f"/api/v1/topologies/{tid}").json()["saved"] is None
    _deploy(client, wait_jobs, tid)
    lab = next(iter(fake_engine.labs.values()))
    assert not any(n.image.startswith(saved_state.REPO_PREFIX) for n in lab.plan.nodes)


def test_deleting_a_topology_removes_its_saved_images(client, topology, wait_jobs, fake_engine):
    tid = topology["id"]
    _deploy(client, wait_jobs, tid)
    client.post(f"/api/v1/topologies/{tid}/destroy?save=true")
    wait_jobs()
    refs = set(fake_engine.snapshots)
    assert client.delete(f"/api/v1/topologies/{tid}").status_code == 204
    assert set(fake_engine.removed_images) == refs


# ── migration ──


def test_0006_adds_saved_state(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    cfg = alembic_config(url)
    command.upgrade(cfg, "0005_registries")
    command.upgrade(cfg, "head")
    engine = sa.create_engine(url)
    columns = {c["name"] for c in sa.inspect(engine).get_columns("topologies")}
    assert "saved_state" in columns
    command.upgrade(cfg, "head")  # a no-op
