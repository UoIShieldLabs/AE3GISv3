import copy

from services.jobs import recover_stale_jobs
from tests.conftest import TWO_SUBNETS


def _runtime(client, tid):
    return client.get(f"/api/v1/topologies/{tid}/runtime").json()


def test_deploy_then_destroy_via_jobs(client, topology, wait_jobs, fake_engine):
    tid = topology["id"]
    r = client.post(f"/api/v1/topologies/{tid}/deploy")
    assert r.status_code == 202, r.text
    job = r.json()
    assert job["kind"] == "deploy" and job["status"] in ("queued", "running")
    # a second deploy while one is active is refused
    assert client.post(f"/api/v1/topologies/{tid}/deploy").status_code == 409

    wait_jobs()
    job = client.get(f"/api/v1/jobs/{job['id']}").json()
    assert job["status"] == "succeeded", job
    assert [s["name"] for s in job["steps"]] == ["validate", "images", "plan", "deploy", "verify"]
    assert all(s["status"] == "succeeded" for s in job["steps"])

    rt = _runtime(client, tid)
    assert rt["status"] == "deployed" and rt["active_job"] is None
    assert {n["id"] for n in rt["nodes"]} == {"rA", "swA", "hA", "rB", "swB", "hB"}
    assert all(n["state"] == "running" for n in rt["nodes"])
    rec = client.get(f"/api/v1/topologies/{tid}").json()
    assert rec["engine_state"]["lab_name"] == f"ae3gis_{tid[:12]}"
    assert rec["engine_state"]["lab_hash"] and rec["engine_state"]["nodes"]["rA"] == "ra"
    assert len(fake_engine.labs) == 1

    # deleting a deployed topology is refused
    assert client.delete(f"/api/v1/topologies/{tid}").status_code == 409

    r = client.post(f"/api/v1/topologies/{tid}/destroy")
    assert r.status_code == 202
    wait_jobs()
    assert client.get(f"/api/v1/jobs/{r.json()['id']}").json()["status"] == "succeeded"
    rt = _runtime(client, tid)
    assert rt["status"] == "idle" and rt["nodes"] == []
    assert fake_engine.labs == {}
    types = [e["type"] for e in client.get(f"/api/v1/topologies/{tid}/events").json()]
    assert "deploy.requested" in types and "job.succeeded" in types
    assert client.get(f"/api/v1/topologies/{tid}/jobs").json()[0]["kind"] == "destroy"


def test_deploy_pulls_missing_images(client, topology, wait_jobs, fake_engine):
    fake_engine.present_images = {"kathara/base"}
    client.post(f"/api/v1/topologies/{topology['id']}/deploy")
    wait_jobs()
    assert fake_engine.pulled == ["kathara/frr"]


def test_deploy_refused_with_validation_errors(client):
    data = copy.deepcopy(TWO_SUBNETS)
    data["sites"][0]["subnets"][0]["containers"][0]["ip"] = "bad"
    tid = client.post("/api/v1/topologies", json={"name": "Bad", "data": data}).json()["id"]
    r = client.post(f"/api/v1/topologies/{tid}/deploy")
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"
    assert any(d["code"] == "ip.invalid" for d in r.json()["diagnostics"])
    assert _runtime(client, tid)["status"] == "idle"


def test_engine_failure_marks_job_failed_and_topology_error(
    client, topology, wait_jobs, fake_engine
):
    fake_engine.fail_deploy = RuntimeError("docker exploded")
    tid = topology["id"]
    job_id = client.post(f"/api/v1/topologies/{tid}/deploy").json()["id"]
    wait_jobs()
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "failed" and "docker exploded" in job["error"]
    assert next(s for s in job["steps"] if s["name"] == "deploy")["status"] == "failed"
    rec = client.get(f"/api/v1/topologies/{tid}").json()
    assert rec["status"] == "error" and rec["engine_state"] is None
    # destroy is allowed from error and brings it back to idle
    fake_engine.fail_deploy = None
    assert client.post(f"/api/v1/topologies/{tid}/destroy").status_code == 409  # nothing deployed
    assert client.post(f"/api/v1/topologies/{tid}/deploy").status_code == 202
    wait_jobs()
    assert _runtime(client, tid)["status"] == "deployed"


def test_restart_recovery_fails_stale_jobs(app, client, topology):
    from db.models import Job

    with app.state.session_factory() as db:
        db.add(Job(topology_id=topology["id"], kind="deploy", status="running", steps=[]))
        db.commit()
    assert recover_stale_jobs(app.state.session_factory) == 1
    jobs = client.get(f"/api/v1/topologies/{topology['id']}/jobs").json()
    assert jobs[0]["status"] == "failed" and "restarted" in jobs[0]["error"]
