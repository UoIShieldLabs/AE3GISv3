"""Scenario runner end to end on the fake engine (API, job, live output, stop)."""

import copy
import time

from tests.conftest import TWO_SUBNETS


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


def _with_phase():
    """A topology with one scenario phase: echo A on hA, then echo B on hB."""
    data = copy.deepcopy(TWO_SUBNETS)
    data["scenarios"] = [
        {
            "id": "sc1",
            "name": "Demo",
            "phases": [
                {
                    "id": "ph1",
                    "name": "Bring up",
                    "executions": [
                        {"containerId": "hA", "script": "echo A"},
                        {"containerId": "hB", "script": "echo B"},
                    ],
                }
            ],
        }
    ]
    return data


def test_run_step_captures_output(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    fake_engine.exec_results["ip -o addr"] = (0, "eth0 10.0.1.5/24\n")
    r = client.post(
        f"/api/v1/topologies/{topology['id']}/scenario/steps/run",
        json={"containerId": "hA", "script": "ip -o addr"},
    )
    assert r.status_code == 202, r.text
    run = r.json()
    assert run["step_count"] == 1 and run["node_ids"] == ["hA"]
    wait_jobs()
    done = client.get(f"/api/v1/scenario/runs/{run['id']}").json()
    assert done["status"] == "succeeded"
    [step] = done["result"]["steps"]
    assert step["status"] == "ok" and step["exit_code"] == 0
    assert "10.0.1.5/24" in step["stdout"] and step["command"] == "ip -o addr"


def test_step_args_are_appended_and_quoted(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    fake_engine.exec_results["sh -c 'echo one two'"] = (0, "one two\n")
    r = client.post(
        f"/api/v1/topologies/{topology['id']}/scenario/steps/run",
        json={"containerId": "hA", "script": "sh -c", "args": ["echo one two"]},
    )
    wait_jobs()
    [step] = client.get(f"/api/v1/scenario/runs/{r.json()['id']}").json()["result"]["steps"]
    # The arg contains a space, so it is shell-quoted as one token when appended.
    assert step["command"] == "sh -c 'echo one two'" and "one two" in step["stdout"]


def test_run_phase_runs_steps_in_order(client, wait_jobs, fake_engine):
    rec = client.post("/api/v1/topologies", json={"name": "p", "data": _with_phase()}).json()
    _deploy(client, wait_jobs, rec)
    fake_engine.exec_results["echo A"] = (0, "A\n")
    fake_engine.exec_results["echo B"] = (0, "B\n")
    r = client.post(f"/api/v1/topologies/{rec['id']}/scenario/phases/ph1/run")
    assert r.status_code == 202, r.text
    assert r.json()["label"] == "Bring up"
    wait_jobs()
    steps = client.get(f"/api/v1/scenario/runs/{r.json()['id']}").json()["result"]["steps"]
    assert [s["container_id"] for s in steps] == ["hA", "hB"]
    assert [s["index"] for s in steps] == [0, 1]
    assert all(s["status"] == "ok" for s in steps)


def test_a_failing_command_is_recorded_not_fatal(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    fake_engine.exec_results["false"] = (3, "")
    r = client.post(
        f"/api/v1/topologies/{topology['id']}/scenario/steps/run",
        json={"containerId": "hA", "script": "false"},
    )
    wait_jobs()
    done = client.get(f"/api/v1/scenario/runs/{r.json()['id']}").json()
    assert done["status"] == "succeeded"  # the job ran; the command failed
    [step] = done["result"]["steps"]
    assert step["status"] == "failed" and step["exit_code"] == 3
    assert done["result"]["failed"] == 1


def test_refuses_when_not_deployed(client, topology, fake_engine):
    r = client.post(
        f"/api/v1/topologies/{topology['id']}/scenario/steps/run",
        json={"containerId": "hA", "script": "echo hi"},
    )
    assert r.status_code == 409 and r.json()["code"] == "bad_state"


def test_unknown_node_is_rejected(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    r = client.post(
        f"/api/v1/topologies/{topology['id']}/scenario/steps/run",
        json={"containerId": "ghost", "script": "echo hi"},
    )
    assert r.status_code == 422 and r.json()["code"] == "unknown_node"


def test_unknown_phase_is_rejected(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    r = client.post(f"/api/v1/topologies/{topology['id']}/scenario/phases/nope/run")
    assert r.status_code == 422 and r.json()["code"] == "unknown_phase"


def test_one_run_at_a_time(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    fake_engine.exec_results["tail -f x"] = (None, "following\n")  # runs until stopped
    first = client.post(
        f"/api/v1/topologies/{topology['id']}/scenario/steps/run",
        json={"containerId": "hA", "script": "tail -f x"},
    ).json()
    try:
        r = client.post(
            f"/api/v1/topologies/{topology['id']}/scenario/steps/run",
            json={"containerId": "hB", "script": "echo hi"},
        )
        assert r.status_code == 409 and r.json()["code"] == "scenario_active"
        assert r.json()["job_id"] == first["id"]
    finally:
        client.post(f"/api/v1/jobs/{first['id']}/stop")
        wait_jobs()


def test_stop_mid_phase_keeps_completed_steps(client, wait_jobs, fake_engine):
    rec = client.post("/api/v1/topologies", json={"name": "p", "data": _with_phase()}).json()
    _deploy(client, wait_jobs, rec)
    fake_engine.exec_results["echo A"] = (0, "A\n")
    fake_engine.exec_results["echo B"] = (None, "B running\n")  # second step hangs
    run = client.post(f"/api/v1/topologies/{rec['id']}/scenario/phases/ph1/run").json()
    # Wait until the first step has completed, then stop.
    _until(
        lambda: len(client.get(f"/api/v1/scenario/runs/{run['id']}/samples").json()["steps"]) >= 1
    )
    assert client.post(f"/api/v1/jobs/{run['id']}/stop").status_code == 202
    wait_jobs()
    done = client.get(f"/api/v1/scenario/runs/{run['id']}").json()
    assert done["status"] == "succeeded"
    result = done["result"]
    assert result["stopped_by"] in ("user", "destroy")
    assert result["steps"][0]["status"] == "ok" and result["steps"][0]["container_id"] == "hA"


def test_destroy_stops_a_running_scenario(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    fake_engine.exec_results["tail -f x"] = (None, "following\n")
    run = client.post(
        f"/api/v1/topologies/{topology['id']}/scenario/steps/run",
        json={"containerId": "hA", "script": "tail -f x"},
    ).json()
    _until(lambda: client.get(f"/api/v1/scenario/runs/{run['id']}").json()["live"])
    client.post(f"/api/v1/topologies/{topology['id']}/destroy")
    wait_jobs()
    assert not client.get(f"/api/v1/scenario/runs/{run['id']}").json()["live"]
    assert client.get(f"/api/v1/topologies/{topology['id']}").json()["status"] == "idle"


def test_live_ws_sends_hello_and_end(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    fake_engine.exec_results["echo hi"] = (0, "hi\n")
    run = client.post(
        f"/api/v1/topologies/{topology['id']}/scenario/steps/run",
        json={"containerId": "hA", "script": "echo hi"},
    ).json()
    with client.websocket_connect(run["ws_path"]) as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["run"]["id"] == run["id"]
        types = {hello["type"]}
        for _ in range(40):
            msg = ws.receive_json()
            types.add(msg["type"])
            if msg["type"] == "end":
                assert msg["result"]["steps"][0]["stdout"].strip() == "hi"
                break
        assert "end" in types
    wait_jobs()


def test_scenario_appears_in_runtime_activity(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    fake_engine.exec_results["tail -f x"] = (None, "following\n")
    run = client.post(
        f"/api/v1/topologies/{topology['id']}/scenario/steps/run",
        json={"containerId": "hA", "script": "tail -f x"},
    ).json()
    try:
        act = _until(
            lambda: [
                a
                for a in client.get(f"/api/v1/topologies/{topology['id']}/runtime").json()[
                    "activity"
                ]
                if a["kind"] == "scenario"
            ]
        )
        assert act[0]["node_ids"] == ["hA"]
    finally:
        client.post(f"/api/v1/jobs/{run['id']}/stop")
        wait_jobs()
