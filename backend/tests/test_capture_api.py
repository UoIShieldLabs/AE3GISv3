"""Packet capture end to end on the fake engine (API, job, relay, pcap, WebSocket)."""

import threading
import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from domain.pcap import PcapSplitter
from engine.fake import FakeEngine
from engine.fake_tools import icmp_echo_frame
from main import create_app
from tests.conftest import TWO_SUBNETS, make_settings

FRAMES = [icmp_echo_frame("10.0.1.1", "10.0.2.1", i, reply=i % 2 == 0) for i in range(1, 6)]


def _deploy(client, wait_jobs, topology):
    client.post(f"/api/v1/topologies/{topology['id']}/deploy")
    wait_jobs()


def _until(client, pred, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = pred()
        if value:
            return value
        time.sleep(0.02)
    raise AssertionError("condition never became true")


def _capturing(client, cap_id):
    def pred():
        body = client.get(f"/api/v1/captures/{cap_id}").json()
        steps = {s["name"]: s["status"] for s in body["job"]["steps"]}
        return body if steps.get("capture") == "running" else None

    return _until(client, pred)


def _start(client, tid, **body):
    body.setdefault("target", {"kind": "link", "connection_id": "c5"})
    return client.post(f"/api/v1/topologies/{tid}/captures", json=body)


def test_capture_a_link_stop_and_download(client, topology, wait_jobs, fake_engine):
    fake_engine.capture_packets = FRAMES
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    r = _start(client, tid, filter="icmp", label="WAN")
    assert r.status_code == 202, r.text
    cap = r.json()
    assert cap["endpoint"]["node_id"] == "rA" and cap["endpoint"]["peer_node_id"] == "rB"
    assert cap["job"]["subject"] == f"capture:{tid}:rA:eth1" and cap["label"] == "WAN"

    _capturing(client, cap["id"])
    live = _until(
        client,
        lambda: (
            (b := client.get(f"/api/v1/captures/{cap['id']}").json())["stats"]["packets"] == 5 and b
        ),
    )
    assert live["live"] and live["stats"]["file_bytes"] > 24

    # The runtime view shows the capture on its link and nodes.
    [act] = client.get(f"/api/v1/topologies/{tid}/runtime").json()["activity"]
    assert act["kind"] == "capture" and act["connection_ids"] == ["c5"]
    assert set(act["node_ids"]) == {"rA", "rB"}

    # A download mid-capture is already a valid pcap.
    mid = client.get(f"/api/v1/captures/{cap['id']}/pcap")
    assert mid.status_code == 200 and len(PcapSplitter().feed(mid.content)) == 5
    assert mid.headers["content-type"] == "application/vnd.tcpdump.pcap"
    assert ".pcap" in mid.headers["content-disposition"]

    assert client.post(f"/api/v1/jobs/{cap['id']}/stop").status_code == 202
    wait_jobs()
    done = client.get(f"/api/v1/captures/{cap['id']}").json()
    assert done["status"] == "succeeded" and not done["live"]
    assert done["stats"]["packets"] == 5 and done["stats"]["stopped_by"] == "user"
    assert [s["name"] for s in done["job"]["steps"]] == ["images", "attach", "capture"]
    result = done["job"]["result"]
    assert result["dropped_by_kernel"] == 0 and result["pcap"] == "capture.pcap"

    pcap = client.get(f"/api/v1/captures/{cap['id']}/pcap").content
    sp = PcapSplitter()
    assert [r.data for r in sp.feed(pcap)] == FRAMES
    page = client.get(f"/api/v1/captures/{cap['id']}/packets?after=2&limit=2").json()
    assert [p["n"] for p in page["items"]] == [3, 4] and page["total"] == 5
    assert page["items"][0]["proto"] == "ICMP"
    names = {a["name"] for a in client.get(f"/api/v1/jobs/{cap['id']}/artifacts").json()}
    assert names == {"capture.pcap", "run.json"}
    run = client.get(f"/api/v1/jobs/{cap['id']}/artifacts/run.json").json()
    assert run["environment"]["fingerprint"] and run["result"]["packets"] == 5
    assert run["environment"]["tool"]["ref"] == "ae3gis.local/nettools"

    # The filter reached tcpdump as one argument after "--".
    [spec] = fake_engine.started_sidecars
    assert spec.command[-2:] == ["--", "icmp"] and spec.purpose == "capture"
    assert spec.command[spec.command.index("-i") + 1] == "eth1"
    assert fake_engine.sidecars == {}
    assert [c["id"] for c in client.get(f"/api/v1/topologies/{tid}/captures").json()] == [cap["id"]]


def test_packet_cap_ends_the_capture(client, topology, wait_jobs, fake_engine):
    fake_engine.capture_packets = FRAMES
    _deploy(client, wait_jobs, topology)
    cap = _start(client, topology["id"], max_packets=3).json()
    wait_jobs()
    done = client.get(f"/api/v1/captures/{cap['id']}").json()
    assert done["status"] == "succeeded"
    assert done["stats"] == {**done["stats"], "packets": 3, "stopped_by": "limit:packets"}
    body = client.get(f"/api/v1/captures/{cap['id']}/pcap?follow=true").content
    assert len(PcapSplitter().feed(body)) == 3


def test_follow_streams_until_the_capture_stops(client, topology, wait_jobs, fake_engine):
    # TestClient buffers whole responses, so this checks that a follow stream
    # ends when the capture does and carries every packet (the incremental
    # delivery is covered end to end against Docker).
    fake_engine.capture_packets = FRAMES
    _deploy(client, wait_jobs, topology)
    cap = _start(client, topology["id"]).json()
    _capturing(client, cap["id"])
    _until(client, lambda: client.get(f"/api/v1/captures/{cap['id']}").json()["stats"]["packets"])
    stopper = threading.Timer(0.3, lambda: client.post(f"/api/v1/jobs/{cap['id']}/stop"))
    stopper.start()
    started = time.monotonic()
    body = client.get(f"/api/v1/captures/{cap['id']}/pcap?follow=true").content
    assert time.monotonic() - started >= 0.25  # it waited for the stop
    stopper.join()
    assert len(PcapSplitter().feed(body)) == 5
    wait_jobs()


def test_capture_refusals_and_dedup(client, topology, wait_jobs, fake_engine):
    tid = topology["id"]
    r = _start(client, tid)
    assert r.status_code == 409 and r.json()["code"] == "bad_state"
    _deploy(client, wait_jobs, topology)
    r = _start(client, tid, target={"kind": "link", "connection_id": "nope"})
    assert r.status_code == 409 and r.json()["code"] == "link_not_deployed"
    r = _start(client, tid, target={"kind": "interface", "node_id": "hA", "interface": "eth5"})
    assert r.json()["code"] == "interface_not_deployed"
    assert _start(client, tid, snaplen=10).status_code == 422
    assert _start(client, tid, filter="icmp\nrm -rf").status_code == 422

    first = _start(client, tid, target={"kind": "interface", "node_id": "rA", "interface": "eth1"})
    again = _start(client, tid)  # the same interface, as a link target
    assert first.status_code == 202 and again.status_code == 200
    assert again.json()["id"] == first.json()["id"]
    other = _start(client, tid, target={"kind": "link", "connection_id": "c5", "endpoint": "to"})
    assert other.status_code == 202 and other.json()["endpoint"]["node_id"] == "rB"
    for c in (first.json(), other.json()):
        client.post(f"/api/v1/jobs/{c['id']}/stop")
    wait_jobs()


def test_destroy_stops_captures_first(client, topology, wait_jobs, fake_engine):
    fake_engine.capture_packets = FRAMES
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    cap = _start(client, tid).json()
    _capturing(client, cap["id"])
    job = client.post(f"/api/v1/topologies/{tid}/destroy").json()
    wait_jobs()
    destroy = client.get(f"/api/v1/jobs/{job['id']}").json()
    assert destroy["status"] == "succeeded"
    assert destroy["steps"][0]["message"] == "Stopped 1 capture/traffic job(s)"
    done = client.get(f"/api/v1/captures/{cap['id']}").json()
    assert done["status"] == "succeeded" and done["stats"]["stopped_by"] == "destroy"
    assert done["stats"]["packets"] == 5 and fake_engine.sidecars == {}
    assert client.get(f"/api/v1/captures/{cap['id']}/pcap").status_code == 200


def test_tcpdump_errors_fail_the_capture(client, topology, wait_jobs, fake_engine):
    fake_engine.fail_sidecar["capture"] = "tcpdump: can't parse filter expression: syntax error"
    _deploy(client, wait_jobs, topology)
    cap = _start(client, topology["id"], filter="port banana").json()
    wait_jobs()
    done = client.get(f"/api/v1/captures/{cap['id']}").json()
    assert done["status"] == "failed"
    assert "can't parse filter expression" in done["job"]["error"]
    assert fake_engine.sidecars == {}


def test_live_websocket(client, topology, wait_jobs, fake_engine):
    fake_engine.capture_packets = FRAMES
    _deploy(client, wait_jobs, topology)
    tid = topology["id"]
    cap = _start(client, tid).json()
    _capturing(client, cap["id"])
    with client.websocket_connect(cap["ws_path"]) as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["capture"]["id"] == cap["id"]
        client.post(f"/api/v1/jobs/{cap['id']}/stop")
        seen = []
        while True:
            msg = ws.receive_json()
            seen.append(msg["type"])
            if msg["type"] == "end":
                assert msg["result"]["packets"] == 5
                break
    assert "status" in seen or "end" in seen
    wait_jobs()
    # After the end: the recent packets from the file, then the result.
    with client.websocket_connect(cap["ws_path"]) as ws:
        hello = ws.receive_json()
        assert len(hello["recent"]) == 5 and ws.receive_json()["type"] == "end"
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/topologies/ws/other/captures/{cap['id']}") as ws:
            ws.receive_json()
    assert exc.value.code == 4004


def test_restart_fails_the_capture_sweeps_its_sidecar_and_keeps_the_pcap(tmp_path):
    from db.models import Job
    from engine.base import EngineState, SidecarSpec

    engine = FakeEngine()
    engine.capture_packets = FRAMES
    app = create_app(make_settings(tmp_path, instance_id="inst1"), engine)
    with TestClient(app) as c:
        tid = c.post("/api/v1/topologies", json={"name": "t", "data": TWO_SUBNETS}).json()["id"]
        c.post(f"/api/v1/topologies/{tid}/deploy")
        c.portal.call(app.state.runner.wait_idle)
        cap = _start(c, tid).json()
        _capturing(c, cap["id"])
        _until(c, lambda: c.get(f"/api/v1/captures/{cap['id']}").json()["stats"]["packets"] == 5)
        c.post(f"/api/v1/jobs/{cap['id']}/stop")
        c.portal.call(app.state.runner.wait_idle)
        # Stage what a crash mid-capture leaves: the row still says running and
        # a sidecar of this instance is still around.
        state = EngineState.from_dict(c.get(f"/api/v1/topologies/{tid}").json()["engine_state"])
        spec = SidecarSpec("rA", "img", ["sleep"], "capture", cap["id"], "inst1")
        c.portal.call(engine.start_sidecar, state, spec)
        with app.state.session_factory() as db:
            db.get(Job, cap["id"]).status = "running"
            db.commit()
    assert len(engine.sidecars) == 1
    with TestClient(create_app(make_settings(tmp_path, instance_id="inst1"), engine)) as c:
        done = c.get(f"/api/v1/captures/{cap['id']}").json()
        assert done["status"] == "failed" and "restarted" in done["job"]["error"]
        assert engine.sidecars == {}
        pcap = c.get(f"/api/v1/captures/{cap['id']}/pcap").content
        assert len(PcapSplitter().feed(pcap)) == 5


def test_live_websocket_waits_for_a_capture_that_is_still_starting(
    client, topology, wait_jobs, fake_engine
):
    fake_engine.capture_packets = FRAMES
    _deploy(client, wait_jobs, topology)
    # Hold the tool image build so the capture sits in its "images" step.
    gate = client.portal.call(lambda: _make_event())
    fake_engine.build_gate = gate
    cap = _start(client, topology["id"]).json()
    threading.Timer(0.4, lambda: client.portal.call(_set, gate)).start()
    with client.websocket_connect(cap["ws_path"]) as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["capture"]["live"]
        client.post(f"/api/v1/jobs/{cap['id']}/stop")
        while (msg := ws.receive_json())["type"] != "end":
            pass
        assert msg["result"]["stopped_by"] == "user"
    wait_jobs()


async def _make_event():
    import asyncio

    return asyncio.Event()


async def _set(event):
    event.set()


def test_live_websocket_handler_exits_when_the_client_leaves(
    app, client, topology, wait_jobs, fake_engine
):
    # An idle capture sends nothing: the handler must still notice the client
    # leaving (or a shutdown would wait on it forever).
    fake_engine.capture_packets = []
    _deploy(client, wait_jobs, topology)
    cap = _start(client, topology["id"]).json()
    _capturing(client, cap["id"])
    channel = app.state.live.get(cap["id"])
    with client.websocket_connect(cap["ws_path"]) as ws:
        assert ws.receive_json()["type"] == "hello"
        assert channel.subscribers == 1
    _until(client, lambda: channel.subscribers == 0)
    client.post(f"/api/v1/jobs/{cap['id']}/stop")
    wait_jobs()
