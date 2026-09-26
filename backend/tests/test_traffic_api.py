"""Traffic runs end to end on the fake engine (API, job, sidecars, samples)."""

import io
import time
import zipfile

import pytest
from starlette.websockets import WebSocketDisconnect

FLOW = {"id": "f1", "client": "hA", "server": "hB"}


def _deploy(client, wait_jobs, topology):
    client.post(f"/api/v1/topologies/{topology['id']}/deploy")
    wait_jobs()


def _run(client, tid, **body):
    body.setdefault("flows", [FLOW])
    return client.post(f"/api/v1/topologies/{tid}/traffic/runs", json=body)


def _until(pred, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = pred()
        if value:
            return value
        time.sleep(0.02)
    raise AssertionError("condition never became true")


def test_fixed_duration_run(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    r = _run(client, tid, duration_s=3, label="baseline", flows=[{**FLOW, "parallel": 2}])
    assert r.status_code == 202, r.text
    run = r.json()
    assert run["job"]["subject"] == f"traffic:{tid}" and run["label"] == "baseline"
    assert run["flows"][0]["server_address"] == "10.0.2.5"  # the server node's IP
    wait_jobs()
    done = client.get(f"/api/v1/traffic/runs/{run['id']}").json()
    assert done["status"] == "succeeded", done["job"]["error"]
    assert [s["name"] for s in done["job"]["steps"]] == ["images", "prepare", "run"]
    result = done["result"]
    assert result["stopped_by"] == "completed" and result["environment_fingerprint"]
    [flow] = result["flows"]
    assert flow["errors"] == [] and flow["port"] == 5201
    fwd = flow["summary"]["fwd"]
    assert fwd["intervals"] == 3 and fwd["measured_by"] == "receiver" and fwd["bps"]["mean"] > 0
    assert {v["role"] for v in done["sidecars"].values()} == {"client", "server"}
    assert fake_engine.sidecars == {}

    # The client ran iperf3 against the server's address, for the run's duration.
    client_spec = next(s for s in fake_engine.started_sidecars if s.purpose == "iperf-client")
    argv = client_spec.command
    assert argv[argv.index("-c") + 1] == "10.0.2.5" and argv[argv.index("-t") + 1] == "3"
    assert argv[argv.index("-P") + 1] == "2" and client_spec.node_id == "hA"

    samples = client.get(f"/api/v1/traffic/runs/{run['id']}/samples").json()
    assert {(s["direction"], s["side"]) for s in samples["flows"]} == {
        ("fwd", "sender"),
        ("fwd", "receiver"),
    }
    assert {s["target"] for s in samples["nodes"] if s["kind"] == "node"} >= {"hA", "hB", "rA"}
    names = {a["name"] for a in client.get(f"/api/v1/jobs/{run['id']}/artifacts").json()}
    assert names == {"flows.ndjson", "nodes.ndjson", "run.json"}
    env = client.get(f"/api/v1/jobs/{run['id']}/artifacts/run.json").json()["environment"]
    assert env["topology"]["plan_sha256"] and env["tool"]["ref"] == "ae3gis.local/nettools"
    assert {n["node_id"] for n in env["nodes"]} >= {"hA", "hB"}
    assert env["sampling"]["interval_s"] == 1.0 and env["concurrent_captures"] == []

    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/v1/traffic/runs/{run['id']}/export").content))
    assert {
        "run.json",
        "flows.ndjson",
        "nodes.ndjson",
        "job.log",
        "raw/f1-client.ndjson",
        "raw/f1-server.ndjson",
    } <= set(z.namelist())
    assert [r["id"] for r in client.get(f"/api/v1/topologies/{tid}/traffic/runs").json()] == [
        run["id"]
    ]


def test_until_stopped_then_stop(client, topology, wait_jobs, fake_engine):
    fake_engine.traffic_interval = 0.02
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    flows = [
        {**FLOW, "protocol": "udp", "bitrate": "50M"},
        {"id": "f2", "client": "hB", "server": "hA", "direction": "bidir"},
    ]
    run = _run(client, tid, duration_s=None, flows=flows).json()
    _until(lambda: len(client.get(f"/api/v1/traffic/runs/{run['id']}/samples").json()["flows"]) > 8)
    [act] = client.get(f"/api/v1/topologies/{tid}/runtime").json()["activity"]
    assert act["kind"] == "traffic" and set(act["node_ids"]) == {"hA", "hB"}
    # One run at a time per topology.
    again = _run(client, tid)
    assert again.status_code == 409 and again.json()["code"] == "traffic_active"
    assert again.json()["job_id"] == run["id"]
    assert client.post(f"/api/v1/jobs/{run['id']}/stop").status_code == 202
    wait_jobs()
    done = client.get(f"/api/v1/traffic/runs/{run['id']}").json()
    assert done["status"] == "succeeded" and done["result"]["stopped_by"] == "user"
    f1, f2 = done["result"]["flows"]
    assert f1["errors"] == [] and "jitter_ms" in f1["summary"]["fwd"]  # UDP, interrupted cleanly
    assert set(f2["summary"]) == {"fwd", "rev"}
    assert [
        s.command[s.command.index("-t") + 1]
        for s in fake_engine.started_sidecars
        if s.purpose == "iperf-client"
    ] == ["0", "0"]


def test_a_server_that_never_listens_fails_the_run(client, topology, wait_jobs, fake_engine):
    fake_engine.fail_sidecar["iperf-server"] = "iperf3: error - unable to start listener"
    _deploy(client, wait_jobs, topology)
    run = _run(client, topology["id"]).json()
    wait_jobs()
    done = client.get(f"/api/v1/traffic/runs/{run['id']}").json()
    assert done["status"] == "failed" and "did not start listening" in done["job"]["error"]
    assert fake_engine.sidecars == {}


def test_destroy_stops_a_run(client, topology, wait_jobs, fake_engine):
    fake_engine.traffic_interval = 0.02
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    run = _run(client, tid, duration_s=None).json()
    _until(lambda: client.get(f"/api/v1/traffic/runs/{run['id']}/samples").json()["flows"])
    client.post(f"/api/v1/topologies/{tid}/destroy")
    wait_jobs()
    done = client.get(f"/api/v1/traffic/runs/{run['id']}").json()
    assert done["status"] == "succeeded" and done["result"]["stopped_by"] == "destroy"
    assert fake_engine.sidecars == {} and fake_engine.labs == {}


def test_refusals(client, topology, wait_jobs):
    tid = topology["id"]
    assert _run(client, tid).json()["code"] == "bad_state"
    _deploy(client, wait_jobs, topology)
    same = _run(client, tid, flows=[{"id": "x", "client": "hA", "server": "hA"}])
    assert same.status_code == 422 and same.json()["code"] == "same_node"
    ghost = _run(client, tid, flows=[{"id": "x", "client": "hA", "server": "nope"}])
    assert ghost.json()["code"] == "node_not_deployed"
    dup = _run(client, tid, flows=[FLOW, FLOW])
    assert dup.json()["code"] == "duplicate_flow"
    assert _run(client, tid, flows=[{**FLOW, "bitrate": "fast"}]).status_code == 422
    assert _run(client, tid, flows=[]).status_code == 422


def test_live_websocket_backlog_and_end(client, topology, wait_jobs, fake_engine):
    fake_engine.traffic_interval = 0.02
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    run = _run(client, tid, duration_s=None).json()
    _until(lambda: client.get(f"/api/v1/traffic/runs/{run['id']}/samples").json()["flows"])
    with client.websocket_connect(run["ws_path"]) as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["run"]["id"] == run["id"]
        assert hello["backlog"]["flows"]
        client.post(f"/api/v1/jobs/{run['id']}/stop")
        kinds = set()
        while True:
            msg = ws.receive_json()
            kinds.add(msg["type"])
            if msg["type"] == "end":
                assert msg["result"]["stopped_by"] == "user"
                break
    wait_jobs()
    with client.websocket_connect(run["ws_path"]) as ws:
        hello = ws.receive_json()
        assert hello["backlog"]["flows"] and ws.receive_json()["type"] == "end"
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/topologies/ws/{tid}/traffic/nope") as ws:
            ws.receive_json()
    assert exc.value.code == 4004
