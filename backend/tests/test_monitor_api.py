"""Monitors end to end on the fake engine (API, job, collector helper, files)."""

import io
import time
import zipfile

import pytest
from starlette.websockets import WebSocketDisconnect


def _deploy(client, wait_jobs, topology):
    client.post(f"/api/v1/topologies/{topology['id']}/deploy")
    wait_jobs()


def _start(client, tid, **body):
    return client.post(f"/api/v1/topologies/{tid}/monitors", json=body)


def _until(pred, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = pred()
        if value:
            return value
        time.sleep(0.02)
    raise AssertionError("condition never became true")


@pytest.fixture
def fast(fake_engine):
    fake_engine.monitor_interval = 0.02
    return fake_engine


def test_monitor_lifecycle(client, topology, wait_jobs, fast):
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    r = _start(client, tid, label="idle", nodes={"roles": ["host"]}, interval_s=1)
    assert r.status_code == 202, r.text
    mon = r.json()
    assert mon["job"]["subject"] == f"monitor:{tid}" and mon["monitored"] == ["hA", "hB"]
    assert mon["selector"] == {"roles": ["host"]}

    samples = _until(
        lambda: (
            (s := client.get(f"/api/v1/monitors/{mon['id']}/samples").json())["nodes"]
            and len(s["host"]) > 3
            and s
        )
    )
    # The collector helper runs with the host's PID and cgroup namespaces.
    [spec] = fast.started_helpers
    assert spec.purpose == "collector" and spec.pid_host and spec.cgroupns_host
    assert spec.binds == {"/sys/fs/cgroup": "/host/cgroup"} and spec.command[0] == "ae3gis-collect"

    assert {r["target"] for r in samples["nodes"] if r["kind"] == "node"} == {"hA", "hB"}
    assert {r["purpose"] for r in samples["nodes"] if r["kind"] == "tool"} == {"collector"}
    host = samples["host"][-1]
    assert host["node_count"] == 6 and host["tool_count"] == 1 and host["mem_used_pct"] > 0
    assert {i["target"] for i in samples["ifaces"]} == {"hA", "hB"}
    only_a = client.get(f"/api/v1/monitors/{mon['id']}/samples?nodes=hA&every=2").json()
    assert {r["target"] for r in only_a["nodes"] if r["kind"] == "node"} == {"hA"}
    assert len(only_a["host"]) <= len(samples["host"]) // 2 + 1

    [act] = client.get(f"/api/v1/topologies/{tid}/runtime").json()["activity"]
    assert act["kind"] == "monitor" and act["node_ids"] == []

    assert client.post(f"/api/v1/jobs/{mon['id']}/stop").status_code == 202
    wait_jobs()
    done = client.get(f"/api/v1/monitors/{mon['id']}").json()
    assert done["status"] == "succeeded", done["job"]["error"]
    assert [s["name"] for s in done["job"]["steps"]] == ["images", "prepare", "run"]
    result = done["result"]
    assert result["stopped_by"] == "user" and result["node_count"] == 2
    assert result["sweeps"] > 3 and result["host"]["mem_used"]["max"] > 0
    assert result["environment_fingerprint"]
    assert fast.helpers == {}

    names = {a["name"] for a in client.get(f"/api/v1/jobs/{mon['id']}/artifacts").json()}
    assert names == {
        "monitor.json",
        "host.csv.gz",
        "nodes.csv.gz",
        "ifaces.csv.gz",
        "markers.csv.gz",
    }
    info = client.get(f"/api/v1/jobs/{mon['id']}/artifacts/monitor.json").json()
    assert set(info["summary"]["nodes"]) == {"hA", "hB"}
    assert info["environment"]["monitor"]["interval_s"] == 1.0
    # Finished monitors still serve their (gzipped) samples.
    assert client.get(f"/api/v1/monitors/{mon['id']}/samples").json()["host"]
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/v1/monitors/{mon['id']}/export").content))
    assert {"monitor.json", "host.csv.gz", "nodes.csv.gz", "job.log"} <= set(z.namelist())
    assert [m["id"] for m in client.get(f"/api/v1/topologies/{tid}/monitors").json()] == [mon["id"]]


def test_fixed_duration_and_oom(client, topology, wait_jobs, fast):
    fast.oom_nodes = {"hB"}
    _deploy(client, wait_jobs, topology)
    mon = _start(client, topology["id"], duration_s=1).json()
    wait_jobs()
    done = client.get(f"/api/v1/monitors/{mon['id']}").json()
    assert done["status"] == "succeeded" and done["result"]["stopped_by"] == "completed"
    assert done["monitored"] == ["rA", "swA", "hA", "rB", "swB", "hB"]


def test_refusals_and_destroy(client, topology, wait_jobs, fast):
    tid = topology["id"]
    assert _start(client, tid).json()["code"] == "bad_state"
    _deploy(client, wait_jobs, topology)
    assert _start(client, tid, nodes=["ghost"]).json()["code"] == "no_nodes"
    assert _start(client, tid, interval_s=0.1).status_code == 422
    mon = _start(client, tid).json()
    again = _start(client, tid)
    assert again.status_code == 409 and again.json()["code"] == "monitor_active"
    _until(lambda: client.get(f"/api/v1/monitors/{mon['id']}/samples").json()["host"])
    client.post(f"/api/v1/topologies/{tid}/destroy")
    wait_jobs()
    done = client.get(f"/api/v1/monitors/{mon['id']}").json()
    assert done["status"] == "succeeded" and done["result"]["stopped_by"] == "destroy"
    assert fast.helpers == {} and fast.labs == {}


def test_a_collector_that_never_reports_fails_the_monitor(client, topology, wait_jobs, fast):
    fast.fail_helper["collector"] = "no cgroup tree at /host/cgroup"
    _deploy(client, wait_jobs, topology)
    mon = _start(client, topology["id"]).json()
    wait_jobs()
    done = client.get(f"/api/v1/monitors/{mon['id']}").json()
    assert done["status"] == "failed"
    assert "collector did not start: no cgroup tree" in done["job"]["error"]
    assert fast.helpers == {}


def test_live_websocket(client, topology, wait_jobs, fast):
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    mon = _start(client, tid, nodes=["hA"]).json()
    _until(lambda: client.get(f"/api/v1/monitors/{mon['id']}/samples").json()["nodes"])
    with client.websocket_connect(mon["ws_path"]) as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["monitor"]["id"] == mon["id"]
        assert hello["backlog"] and hello["backlog"][-1]["type"] == "sweep"
        sweep = ws.receive_json()
        assert sweep["type"] == "sweep" and sweep["selection"]["count"] == 1
        assert [n["target"] for n in sweep["nodes"]] == ["hA"] and sweep["host"]["mem_used"]
        assert sweep["groups"]["tool"]["count"] == 1
        client.post(f"/api/v1/jobs/{mon['id']}/stop")
        while (msg := ws.receive_json())["type"] != "end":
            pass
        assert msg["result"]["stopped_by"] == "user"
    wait_jobs()
    with client.websocket_connect(mon["ws_path"]) as ws:
        assert ws.receive_json()["type"] == "hello" and ws.receive_json()["type"] == "end"
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/topologies/ws/{tid}/monitors/nope") as ws:
            ws.receive_json()
    assert exc.value.code == 4004
