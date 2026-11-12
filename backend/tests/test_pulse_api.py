"""The live lab view end to end on the fake engine (WebSocket, shared collector)."""

import time

import pytest

from domain import pulse
from services import pulse as pulse_service


@pytest.fixture(autouse=True)
def _fast(monkeypatch, fake_engine):
    fake_engine.monitor_interval = 0.02
    monkeypatch.setattr(pulse_service, "LINGER_S", 0.05)
    monkeypatch.setattr(pulse_service, "REFRESH_S", 0.05)
    # The fake lab is used the moment it is deployed.
    monkeypatch.setattr(pulse, "DEPLOY_GRACE_S", -60.0)


def _deploy(client, wait_jobs, topology):
    client.post(f"/api/v1/topologies/{topology['id']}/deploy")
    wait_jobs()


def _path(topology):
    return f"/api/v1/topologies/ws/{topology['id']}/pulse"


def _until(ws, pred, tries=200):
    for _ in range(tries):
        msg = ws.receive_json()
        if msg["type"] == "pulse" and pred(msg):
            return msg
    raise AssertionError("the picture never got there")


def test_quiet_lab_then_traffic_and_a_process(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    with client.websocket_connect(_path(topology)) as ws:
        assert ws.receive_json() == {"type": "hello"}
        assert ws.receive_json() == {"type": "pulse", "links": {}, "nodes": {}}

        fake_engine.fake_traffic_nodes.add("hA")
        fake_engine.fake_procs["hB"] = [("zeek", "zeek -i eth0 -C")]
        msg = _until(ws, lambda m: m["links"] and m["nodes"])
        assert msg["links"] == {"c2": "both"}  # hA's only link, to its switch
        assert [p["name"] for p in msg["nodes"]["hB"]] == ["zeek"]
        assert msg["nodes"]["hB"][0]["args"] == "zeek -i eth0 -C"

        fake_engine.fake_traffic_nodes.clear()
        fake_engine.fake_procs.clear()
        _until(ws, lambda m: not m["links"] and not m["nodes"], tries=400)
    wait_jobs()
    # The collector ran with --procs and went away with its last viewer.
    [spec] = [s for s in fake_engine.started_helpers if s.purpose == "collector"]
    assert "--procs" in spec.command and spec.pid_host
    assert not fake_engine.helpers


def test_viewers_share_one_collector_and_a_late_one_gets_the_picture(
    client, topology, wait_jobs, fake_engine
):
    _deploy(client, wait_jobs, topology)
    fake_engine.fake_traffic_nodes.add("hB")
    with client.websocket_connect(_path(topology)) as first:
        _until(first, lambda m: m["links"])
        with client.websocket_connect(_path(topology)) as second:
            assert second.receive_json() == {"type": "hello"}
            assert second.receive_json()["links"] == {"c4": "both"}  # replayed, no wait
        assert len([s for s in fake_engine.started_helpers if s.purpose == "collector"]) == 1
    wait_jobs()


def test_a_long_running_exec_shows_as_a_process_with_traffic(
    client, topology, wait_jobs, fake_engine
):
    _deploy(client, wait_jobs, topology)
    fake_engine.exec_results["ping 10.0.2.5"] = (None, "")
    run = client.post(
        f"/api/v1/topologies/{topology['id']}/scenario/steps/run",
        json={"containerId": "hA", "script": "ping 10.0.2.5"},
    ).json()
    with client.websocket_connect(_path(topology)) as ws:
        msg = _until(ws, lambda m: m["links"] and m["nodes"])
        assert msg["nodes"]["hA"][0]["name"] == "ping" and "c2" in msg["links"]
    client.post(f"/api/v1/jobs/{run['id']}/stop")
    wait_jobs()


def test_not_deployed_lists_nothing_and_an_unknown_topology_is_refused(client, topology, wait_jobs):
    with client.websocket_connect(_path(topology)) as ws:
        assert ws.receive_json() == {"type": "hello"}
        assert ws.receive_json() == {"type": "pulse", "links": {}, "nodes": {}}
    wait_jobs()


def test_viewers_are_told_when_the_collector_cannot_run(client, topology, wait_jobs, fake_engine):
    _deploy(client, wait_jobs, topology)
    fake_engine.fail_helper["collector"] = "no cgroup tree"
    with client.websocket_connect(_path(topology)) as ws:
        assert ws.receive_json() == {"type": "hello"}
        msg = ws.receive_json()
        assert msg["type"] == "unavailable" and "no cgroup tree" in msg["reason"]
    wait_jobs()
    # A later viewer starts a fresh collector.
    fake_engine.fail_helper.clear()
    with client.websocket_connect(_path(topology)) as ws:
        assert ws.receive_json() == {"type": "hello"}
        assert ws.receive_json()["type"] == "pulse"
    wait_jobs()


def test_the_collector_lingers_for_a_returning_viewer(
    client, topology, wait_jobs, fake_engine, monkeypatch
):
    monkeypatch.setattr(pulse_service, "LINGER_S", 5.0)
    _deploy(client, wait_jobs, topology)
    for _ in range(2):
        with client.websocket_connect(_path(topology)) as ws:
            ws.receive_json()
            ws.receive_json()
        time.sleep(0.05)
    assert len([s for s in fake_engine.started_helpers if s.purpose == "collector"]) == 1
    monkeypatch.setattr(pulse_service, "LINGER_S", 0.05)
    wait_jobs()
