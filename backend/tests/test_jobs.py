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


def _wait_for_step(client, job_id, name, timeout=5.0):
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        if any(s["name"] == name and s["status"] == "running" for s in job["steps"]):
            return job
        time.sleep(0.02)
    raise AssertionError(f"step {name} never started: {job}")


def test_job_log_records_steps(client, topology, wait_jobs):
    job_id = client.post(f"/api/v1/topologies/{topology['id']}/deploy").json()["id"]
    wait_jobs()
    first = client.get(f"/api/v1/jobs/{job_id}/log", params={"offset": 0}).json()
    assert "── validate" in first["text"] and "── verify" in first["text"]
    assert first["text"].rstrip().endswith("succeeded")
    assert first["done"] is True and first["next_offset"] == first["size"]
    rest = client.get(f"/api/v1/jobs/{job_id}/log", params={"offset": first["next_offset"]})
    assert rest.json()["text"] == ""
    assert client.get("/api/v1/jobs/nope/log").status_code == 404


def test_cancel_deploy_while_pulling_images(client, topology, wait_jobs, fake_engine):
    import asyncio

    fake_engine.present_images = {"kathara/base"}
    fake_engine.pull_gate = asyncio.Event()
    tid = topology["id"]
    job_id = client.post(f"/api/v1/topologies/{tid}/deploy").json()["id"]
    _wait_for_step(client, job_id, "images")

    r = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert r.status_code == 202, r.text
    wait_jobs()
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "cancelled"
    assert next(s for s in job["steps"] if s["name"] == "images")["status"] == "cancelled"
    assert _runtime(client, tid)["status"] == "idle"
    assert fake_engine.labs == {} and fake_engine.pulled == []
    # Finished jobs can't be cancelled; a new deploy works.
    assert client.post(f"/api/v1/jobs/{job_id}/cancel").status_code == 409
    fake_engine.pull_gate = None
    assert client.post(f"/api/v1/topologies/{tid}/deploy").status_code == 202
    wait_jobs()
    assert _runtime(client, tid)["status"] == "deployed"


def test_destroy_cannot_be_cancelled(client, topology, wait_jobs):
    tid = topology["id"]
    client.post(f"/api/v1/topologies/{tid}/deploy")
    wait_jobs()
    job_id = client.post(f"/api/v1/topologies/{tid}/destroy").json()["id"]
    r = client.post(f"/api/v1/jobs/{job_id}/cancel")
    wait_jobs()
    assert r.status_code == 409 and r.json()["code"] == "not_cancellable"
    assert client.get(f"/api/v1/jobs/{job_id}").json()["status"] == "succeeded"


def test_deploy_that_dies_part_way_is_cleaned_up_and_explained(
    client, topology, wait_jobs, fake_engine
):
    fake_engine.fail_after_create = RuntimeError("409 container is not running")
    fake_engine.crash_nodes = {"hA": "sysctl: setting key: Read-only file system"}
    tid = topology["id"]
    job_id = client.post(f"/api/v1/topologies/{tid}/deploy").json()["id"]
    wait_jobs()
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert "409 container is not running" in job["error"]
    assert "ha exited (1): sysctl: setting key: Read-only file system" in job["error"]
    assert fake_engine.labs == {}  # the half-created lab was removed
    rec = client.get(f"/api/v1/topologies/{tid}").json()
    assert rec["status"] == "error" and rec["engine_state"] is None
    text = client.get(f"/api/v1/jobs/{job_id}/log", params={"offset": 0}).json()["text"]
    assert "ha | sysctl: setting key" in text


def test_verify_reports_crashed_nodes(client, topology, wait_jobs, fake_engine, monkeypatch):
    from services import deployment

    monkeypatch.setattr(deployment, "VERIFY_TIMEOUT_S", 0.0)
    fake_engine.crash_nodes = {"hA": "nft: No such file or directory"}
    tid = topology["id"]
    job_id = client.post(f"/api/v1/topologies/{tid}/deploy").json()["id"]
    wait_jobs()
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "succeeded"
    verify = next(s for s in job["steps"] if s["name"] == "verify")
    assert "ha exited (1): nft: No such file" in verify["message"]
    partial = [
        e
        for e in client.get(f"/api/v1/topologies/{tid}/events").json()
        if e["type"] == "deploy.partial"
    ]
    assert partial and partial[0]["data"]["logs"] == {"hA": "nft: No such file or directory"}


def test_restart_recovery_unsticks_topologies(app, client, topology):
    from db.models import Topology

    with app.state.session_factory() as db:
        db.get(Topology, topology["id"]).status = "deploying"
        db.commit()
    recover_stale_jobs(app.state.session_factory)
    assert _runtime(client, topology["id"])["status"] == "error"
    types = [e["type"] for e in client.get(f"/api/v1/topologies/{topology['id']}/events").json()]
    assert "topology.recovered" in types


# ── stopping open-ended jobs ─────────────────────────────────────────


async def _open_ended(runner, job_id):
    """A stand-in for a capture: runs until stopped, then records a result."""
    async with runner.step(job_id, "run"):
        await runner.stop_event(job_id).wait()
    runner.set_result(job_id, {"stopped_by": "user"})


def _start_open_ended(app, client, subject="test:1"):
    from services import jobs

    runner = app.state.runner
    runner.register("open_ended", _open_ended, cancellable=True, stoppable=True)
    with runner.session_factory() as db:
        job = jobs.create_job(db, "open_ended", subject=subject)
        db.commit()
        job_id = job.id
    runner.submit(job_id)
    for _ in range(200):
        steps = client.get(f"/api/v1/jobs/{job_id}").json()["steps"]
        if steps and steps[0]["status"] == "running":
            return job_id
        client.portal.call(_sleep)
    raise AssertionError("job never started")


async def _sleep():
    import asyncio

    await asyncio.sleep(0.01)


def test_stop_finishes_an_open_ended_job_as_succeeded(app, client, wait_jobs):
    job_id = _start_open_ended(app, client)
    r = client.post(f"/api/v1/jobs/{job_id}/stop")
    assert r.status_code == 202, r.text
    wait_jobs()
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "succeeded" and job["result"] == {"stopped_by": "user"}
    # A finished job can't be stopped again.
    assert client.post(f"/api/v1/jobs/{job_id}/stop").json()["code"] == "not_stoppable"


def test_stop_is_refused_for_kinds_that_cannot_stop(client, topology, wait_jobs):
    job = client.post(f"/api/v1/topologies/{topology['id']}/deploy").json()
    r = client.post(f"/api/v1/jobs/{job['id']}/stop")
    assert r.status_code == 409 and r.json()["code"] == "not_stoppable"
    wait_jobs()


def test_shutdown_stops_open_ended_jobs(app, client):
    job_id = _start_open_ended(app, client)
    runner = app.state.runner
    client.portal.call(lambda: runner.shutdown(stop_kinds=("open_ended",), stop_grace=2))
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "succeeded" and job["result"] == {"stopped_by": "user"}
