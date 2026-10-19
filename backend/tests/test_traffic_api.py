"""Traffic runs end to end on the fake engine (API, job, netns driver, samples)."""

import io
import json
import time
import zipfile

import pytest
from starlette.websockets import WebSocketDisconnect

FLOW = {"id": "f1", "client": "hA", "server": "hB"}


def _deploy(client, wait_jobs, topology):
    client.post(f"/api/v1/topologies/{topology['id']}/deploy")
    wait_jobs()


def _run(client, tid, **body):
    if "patterns" not in body:
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


def _driver_spec(fake_engine) -> dict:
    [spec] = [h for h in fake_engine.started_helpers if h.purpose == "driver"]
    return spec, json.loads(spec.files["/ae3gis/spec.json"])


def test_fixed_duration_run(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    r = _run(client, tid, duration_s=3, label="baseline", flows=[{**FLOW, "parallel": 2}])
    assert r.status_code == 202, r.text
    run = r.json()
    assert run["job"]["subject"] == f"traffic:{tid}" and run["label"] == "baseline"
    assert run["flows"][0]["server_address"] == "10.0.2.5"  # the server node's IP
    assert run["flows"][0]["port"] == 5201 and run["flow_count"] == 1
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
    totals = result["totals"]
    assert totals["flows"] == 1 and totals["processes"] == 2 and totals["delivered_bps"] > 0
    assert totals["offered_bps"] is None and totals["flows_with_errors"] == 0  # TCP, no rate

    # One driver helper, in the host PID namespace with CAP_SYS_ADMIN, ran both ends.
    spec, doc = _driver_spec(fake_engine)
    assert spec.pid_host and "SYS_ADMIN" in spec.cap_add and spec.command[0] == "ae3gis-netns"
    server, client_ = doc["procs"]
    assert (server["id"], server["role"], server["port"]) == ("f1.s", "server", 5201)
    # The server answers from the address its client targets (multi-homed nodes).
    assert server["argv"][-2:] == ["-B", "10.0.2.5"]
    argv = client_["argv"]
    assert argv[argv.index("-c") + 1] == "10.0.2.5" and argv[argv.index("-t") + 1] == "3"
    assert argv[argv.index("-P") + 1] == "2" and client_["pid"] != server["pid"]
    assert fake_engine.helpers == {} and fake_engine.sidecars == {}

    samples = client.get(f"/api/v1/traffic/runs/{run['id']}/samples").json()
    assert {(s["direction"], s["side"]) for s in samples["flows"]} == {
        ("fwd", "sender"),
        ("fwd", "receiver"),
    }
    assert samples["totals"] and all("delivered_bps" in t for t in samples["totals"])
    only_totals = client.get(f"/api/v1/traffic/runs/{run['id']}/samples?totals_only=true").json()
    assert only_totals["flows"] == [] and only_totals["totals"]
    names = {a["name"] for a in client.get(f"/api/v1/jobs/{run['id']}/artifacts").json()}
    assert names == {"flows.ndjson", "totals.ndjson", "raw.ndjson", "run.json"}
    info = client.get(f"/api/v1/jobs/{run['id']}/artifacts/run.json").json()
    env = info["environment"]
    assert env["topology"]["plan_sha256"] and env["tool"]["ref"] == "ae3gis.local/nettools"
    assert {n["node_id"] for n in env["nodes"]} >= {"hA", "hB"}
    assert env["traffic"] == {"flows": 1, "interval_s": 1.0, "ramp_s": 0.0}
    assert env["concurrent_jobs"] == [] and info["result"]["flows"][0]["id"] == "f1"

    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/v1/traffic/runs/{run['id']}/export").content))
    assert {"run.json", "flows.ndjson", "totals.ndjson", "raw.ndjson", "job.log"} <= set(
        z.namelist()
    )
    [listed] = client.get(f"/api/v1/topologies/{tid}/traffic/runs").json()
    assert listed["id"] == run["id"] and listed["flows"] == [] and listed["flow_count"] == 1
    assert "flows" not in listed["result"] and listed["result"]["totals"]["flows"] == 1


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
    _, doc = _driver_spec(fake_engine)
    clients = [p for p in doc["procs"] if p["role"] == "client"]
    assert [p["argv"][p["argv"].index("-t") + 1] for p in clients] == ["0", "0"]
    # Each server node counts its ports from 5201.
    assert [p["port"] for p in doc["procs"] if p["role"] == "server"] == [5201, 5201]


def test_patterns_expand_into_flows(client, topology, wait_jobs, fake_engine, app):
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    run = _run(
        client,
        tid,
        duration_s=1,
        patterns=[
            {
                "id": "cs",
                "kind": "clients_to_servers",
                "clients": {"roles": ["host"]},
                "servers": ["hB"],
                "bitrate": "1M",
            },
            {
                "id": "mesh",
                "kind": "mesh",
                "nodes": "all",
                "fanout": 2,
                "bitrate": "2M",
                "protocol": "udp",
            },
        ],
    )
    assert run.status_code == 202, run.text
    flows = run.json()["flows"]
    # hB is the only server, so it is not a client too; the mesh: 6 nodes x 2 peers.
    assert [(f["id"], f["client"], f["server"]) for f in flows[:1]] == [("cs.1", "hA", "hB")]
    mesh = [f for f in flows if f["pattern"] == "mesh"]
    assert len(mesh) == 12 and mesh[0]["protocol"] == "udp" and mesh[0]["bitrate"] == "2M"
    served = {}
    for f in flows:
        served.setdefault(f["server"], []).append(f["port"])
    assert all(ports == list(range(5201, 5201 + len(ports))) for ports in served.values())
    wait_jobs()
    done = client.get(f"/api/v1/traffic/runs/{run.json()['id']}").json()
    assert done["status"] == "succeeded", done["job"]["error"]
    totals = done["result"]["totals"]
    assert totals["flows"] == 13 and totals["processes"] == 26
    assert totals["offered_bps"] == 1e6 + 12 * 2e6 and 0 < totals["delivered_ratio"] <= 1.05
    # Run-wide latency and jitter from the flows (fake: UDP jitter 0.21 ms).
    assert totals["jitter_ms_p50"] == 0.21 and totals["bytes_received"] > 0
    assert 0 < totals["flow_ratio_min"] <= totals["flow_ratio_p05"] and totals["slowest_flow"]

    app.state.settings.traffic_max_flows = 10
    big = _run(
        client,
        tid,
        patterns=[{"id": "m", "kind": "mesh", "nodes": "all", "fanout": 5, "bitrate": "1M"}],
    )
    assert big.status_code == 422 and big.json()["code"] == "too_many_flows"
    assert big.json()["flows"] == 30


def test_burst_patterns(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    burst = {"id": "b", "kind": "mesh", "nodes": "all", "bitrate": "250K", "protocol": "udp"}
    run = _run(client, tid, duration_s=1, patterns=[{**burst, "burst_interval_ms": 500}])
    assert run.status_code == 202, run.text
    flow = run.json()["flows"][0]
    assert flow["burst"] == {"count": 12, "length": 1302, "bytes": 15624}
    wait_jobs()
    _, doc = _driver_spec(fake_engine)
    argv = next(p["argv"] for p in doc["procs"] if p["role"] == "client")
    assert argv[argv.index("-b") + 1] == "250K/12" and argv[argv.index("-l") + 1] == "1302"
    wait_jobs()
    done = client.get(f"/api/v1/traffic/runs/{run.json()['id']}").json()
    assert done["status"] == "succeeded", done["job"]["error"]
    assert done["result"]["totals"]["offered_bps"] == 6 * 250e3  # bursts keep the mean rate
    assert done["result"]["flows"][0]["burst"]["count"] == 12

    huge = _run(client, tid, patterns=[{**burst, "bitrate": "1G", "burst_interval_ms": 10000}])
    assert huge.status_code == 422 and huge.json()["code"] == "bad_burst"
    unlimited = _run(client, tid, patterns=[{**burst, "bitrate": "0", "burst_interval_ms": 100}])
    assert unlimited.status_code == 422


def test_large_runs_keep_the_job_row_lean(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    patterns = [
        {"id": f"m{i}", "kind": "mesh", "nodes": "all", "fanout": 5, "bitrate": "1M"}
        for i in range(3)
    ]
    run = _run(client, topology["id"], duration_s=1, patterns=patterns).json()
    assert run["flow_count"] == 90
    wait_jobs()
    done = client.get(f"/api/v1/traffic/runs/{run['id']}").json()
    assert done["status"] == "succeeded", done["job"]["error"]
    result = done["result"]
    assert result["flows_truncated"] and len(result["flows"]) <= 64
    assert result["totals"]["flows"] == 90
    info = client.get(f"/api/v1/jobs/{run['id']}/artifacts/run.json").json()
    assert len(info["result"]["flows"]) == 90
    # Many flows: live views get totals, not every sample.
    with client.websocket_connect(run["ws_path"]) as ws:
        hello = ws.receive_json()
        assert hello["backlog"]["flows"] == [] and hello["backlog"]["totals"]


def test_a_server_that_never_listens_fails_the_run(client, topology, wait_jobs, fake_engine):
    fake_engine.fail_listen = {"hB"}
    _deploy(client, wait_jobs, topology)
    run = _run(client, topology["id"]).json()
    wait_jobs()
    done = client.get(f"/api/v1/traffic/runs/{run['id']}").json()
    assert done["status"] == "failed" and "did not start listening" in done["job"]["error"]
    assert fake_engine.helpers == {}


def test_some_servers_failing_leaves_the_rest_running(client, topology, wait_jobs, fake_engine):
    fake_engine.fail_listen = {"hB"}
    _deploy(client, wait_jobs, topology)
    flows = [FLOW, {"id": "f2", "client": "hB", "server": "hA"}]
    run = _run(client, topology["id"], duration_s=1, flows=flows).json()
    wait_jobs()
    done = client.get(f"/api/v1/traffic/runs/{run['id']}").json()
    assert done["status"] == "succeeded", done["job"]["error"]
    f1, f2 = done["result"]["flows"]
    assert any("listener" in e for e in f1["errors"]) and f2["errors"] == []
    assert done["result"]["totals"]["flows_with_errors"] == 1
    kinds = {e["type"] for e in client.get(f"/api/v1/topologies/{topology['id']}/events").json()}
    assert "traffic.servers_failed" in kinds


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
    assert fake_engine.helpers == {} and fake_engine.labs == {}


def test_runs_mark_a_running_monitor(client, topology, wait_jobs, fake_engine):
    fake_engine.monitor_interval = 0.02
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    mon = client.post(f"/api/v1/topologies/{tid}/monitors", json={}).json()
    _until(lambda: client.get(f"/api/v1/monitors/{mon['id']}/samples").json()["host"])
    run = _run(client, tid, duration_s=1).json()
    _until(lambda: client.get(f"/api/v1/traffic/runs/{run['id']}").json()["status"] == "succeeded")
    client.post(f"/api/v1/jobs/{mon['id']}/stop")
    wait_jobs()
    markers = client.get(f"/api/v1/monitors/{mon['id']}/samples").json()["markers"]
    assert [m["text"] for m in markers] == [
        "Traffic started: 1 flow(s)",
        "Traffic ended (completed)",
    ]
    env = client.get(f"/api/v1/jobs/{run['id']}/artifacts/run.json").json()["environment"]
    assert [j["kind"] for j in env["concurrent_jobs"]] == ["monitor"]


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
    assert _run(client, tid, flows=[]).json()["code"] == "no_flows"
    no_servers = _run(
        client,
        tid,
        patterns=[{"id": "p", "kind": "clients_to_servers", "servers": ["ghost"], "bitrate": "1M"}],
    )
    assert no_servers.json()["code"] == "no_servers"
    twice = _run(client, tid, patterns=[{"id": "p", "kind": "mesh", "bitrate": "1M"}] * 2)
    assert twice.status_code == 422
    no_rate = _run(client, tid, patterns=[{"id": "p", "kind": "mesh"}])
    assert no_rate.status_code == 422


def test_live_websocket_backlog_and_end(client, topology, wait_jobs, fake_engine):
    fake_engine.traffic_interval = 0.02
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    run = _run(client, tid, duration_s=None, interval_s=0.5).json()
    _until(lambda: client.get(f"/api/v1/traffic/runs/{run['id']}/samples").json()["flows"])
    with client.websocket_connect(run["ws_path"]) as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["run"]["id"] == run["id"]
        assert hello["backlog"]["flows"]
        status = None
        while status is None:
            msg = ws.receive_json()
            if msg["type"] == "status":
                status = msg
        assert status["total"]["active"] == 1 and "f1" in status["flows"]
        client.post(f"/api/v1/jobs/{run['id']}/stop")
        while (msg := ws.receive_json())["type"] != "end":
            pass
        assert msg["result"]["stopped_by"] == "user"
    wait_jobs()
    with client.websocket_connect(run["ws_path"]) as ws:
        hello = ws.receive_json()
        assert hello["backlog"]["flows"] and ws.receive_json()["type"] == "end"
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/topologies/ws/{tid}/traffic/nope") as ws:
            ws.receive_json()
    assert exc.value.code == 4004
