"""Background runs end to end on the fake engine (start, live state, stop, destroy)."""

import time

import pytest

from services import background


@pytest.fixture
def plain(monkeypatch):
    """The marker carries the job id, which a test only learns once the run
    exists: key the fake engine's commands on the bare command line instead."""
    monkeypatch.setattr(background, "marked_argv", lambda _job_id, command: ["sh", "-lc", command])


def _deploy(client, wait_jobs, topology):
    client.post(f"/api/v1/topologies/{topology['id']}/deploy")
    wait_jobs()


def _until(pred, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = pred()
        if value:
            return value
        time.sleep(0.02)
    raise AssertionError("condition never became true")


def _start(client, topology, items, **extra):
    return client.post(
        f"/api/v1/topologies/{topology['id']}/background/runs", json={"items": items, **extra}
    )


def _run(client, job_id):
    return client.get(f"/api/v1/background/runs/{job_id}").json()


PING = {"id": "t1:hA:hB", "containerId": "hA", "command": "ping -i 2 10.0.2.5"}
POLL = {"id": "t2:hB", "containerId": "hB", "command": "while sleep 2; do true; done"}


def test_commands_run_until_the_run_is_stopped(client, topology, wait_jobs, fake_engine, plain):
    _deploy(client, wait_jobs, topology)
    fake_engine.exec_results[PING["command"]] = (None, "64 bytes from 10.0.2.5\n")
    fake_engine.exec_results[POLL["command"]] = (None, "")
    r = _start(client, topology, [PING, POLL], label="Background traffic", tag="tutorial-traffic:t")
    assert r.status_code == 202, r.text
    run = r.json()
    assert run["live"] and run["tag"] == "tutorial-traffic:t" and run["node_ids"] == ["hA", "hB"]

    def running():
        got = _run(client, run["id"])
        return got if [i["status"] for i in got["items"]] == ["running", "running"] else None

    live = _until(running)
    _until(lambda: "64 bytes from 10.0.2.5" in _run(client, run["id"])["items"][0]["output"])
    assert live["items"][0]["container_id"] == "hA" and live["items"][0]["started_at"]
    # It shows in /runtime like a traffic run, and a second run is refused.
    activity = client.get(f"/api/v1/topologies/{topology['id']}/runtime").json()["activity"]
    assert [(a["kind"], a["node_ids"]) for a in activity] == [("background", ["hA", "hB"])]
    again = _start(client, topology, [PING])
    assert again.status_code == 409 and again.json()["code"] == "background_active"

    assert client.post(f"/api/v1/jobs/{run['id']}/stop").status_code in (200, 202)
    wait_jobs()
    done = _run(client, run["id"])
    assert done["status"] == "succeeded" and not done["live"] and done["stopped_by"] == "user"
    assert [i["status"] for i in done["items"]] == ["stopped", "stopped"]
    assert not fake_engine.running_execs
    # Whatever detached itself was looked for by the marker, before and after.
    sweeps = [c for c in fake_engine.calls if c[0] == "exec_output" and background.MARKER in c[1]]
    assert len(sweeps) == 4  # two nodes × (before the start + after the stop)
    [listed] = client.get(f"/api/v1/topologies/{topology['id']}/background/runs").json()
    assert listed["id"] == run["id"] and listed["items"] == []


def test_a_command_that_ends_on_its_own_is_reported_and_the_run_ends(
    client, topology, wait_jobs, fake_engine, plain
):
    _deploy(client, wait_jobs, topology)
    fake_engine.exec_results["nope"] = (127, "sh: nope: not found\n")
    run = _start(client, topology, [{"id": "a", "containerId": "hA", "command": "nope"}]).json()
    wait_jobs()
    done = _run(client, run["id"])
    assert done["status"] == "succeeded" and done["stopped_by"] == "completed"
    [item] = done["items"]
    assert item["status"] == "exited" and item["exit_code"] == 127
    assert "not found" in item["output"] and item["ended_at"]


def test_destroy_stops_the_run(client, topology, wait_jobs, fake_engine, plain):
    _deploy(client, wait_jobs, topology)
    fake_engine.exec_results[PING["command"]] = (None, "")
    run = _start(client, topology, [PING]).json()
    _until(lambda: _run(client, run["id"])["items"][0]["status"] == "running")
    client.post(f"/api/v1/topologies/{topology['id']}/destroy")
    wait_jobs()
    done = _run(client, run["id"])
    assert not done["live"] and done["stopped_by"] == "destroy"
    assert not fake_engine.running_execs


def test_the_marker_reaches_the_node(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    run = _start(client, topology, [{"id": "a", "containerId": "hA", "command": "poll"}]).json()
    # On the fake engine a marked command keeps running, like the pollers it stands for.
    _until(lambda: _run(client, run["id"])["items"][0]["status"] == "running")
    assert ("exec", "poll") in fake_engine.calls
    # The marker is in the environment the shell starts with, not exported by it.
    assert background.marked_argv(run["id"], "poll") == [
        "env",
        f"AE3GIS_BG={run['id']}",
        "sh",
        "-lc",
        "poll",
    ]
    client.post(f"/api/v1/jobs/{run['id']}/stop")
    wait_jobs()
    assert _run(client, run["id"])["items"][0]["status"] == "stopped"


def test_requests_are_checked(client, topology, wait_jobs):
    not_deployed = _start(client, topology, [PING])
    assert not_deployed.status_code == 409 and not_deployed.json()["code"] == "bad_state"
    _deploy(client, wait_jobs, topology)
    unknown = _start(client, topology, [{**PING, "containerId": "ghost"}])
    assert unknown.status_code == 422 and unknown.json()["code"] == "unknown_node"
    assert _start(client, topology, []).status_code == 422
    assert _start(client, topology, [PING, PING]).status_code == 422  # duplicate ids
    assert client.get("/api/v1/background/runs/nope").status_code == 404


def test_a_run_cut_short_reports_nothing_running(client, topology, wait_jobs, fake_engine, plain):
    _deploy(client, wait_jobs, topology)
    fake_engine.exec_results[PING["command"]] = (None, "")
    run = _start(client, topology, [PING]).json()
    _until(lambda: _run(client, run["id"])["items"][0]["status"] == "running")
    # Cancelled (as a shutdown does once its grace runs out), not stopped.
    client.post(f"/api/v1/jobs/{run['id']}/cancel")
    wait_jobs()
    done = _run(client, run["id"])
    assert done["status"] == "cancelled" and not done["live"]
    assert [i["status"] for i in done["items"]] == ["stopped"]
