"""Sidecars on the fake engine: lifecycle, teardown order, sweeps, telemetry."""

import asyncio

from domain.pcap import PcapSplitter
from engine.base import EngineState, SidecarSpec
from engine.fake import FakeEngine
from tests.conftest import TWO_SUBNETS


def _deployed(client, wait_jobs, topology) -> EngineState:
    client.post(f"/api/v1/topologies/{topology['id']}/deploy")
    wait_jobs()
    rec = client.get(f"/api/v1/topologies/{topology['id']}").json()
    return EngineState.from_dict(rec["engine_state"])


def _spec(command, node="hA", purpose="capture", job="job1", owner="me") -> SidecarSpec:
    return SidecarSpec(
        node_id=node,
        image="ae3gis.local/nettools",
        command=command,
        purpose=purpose,
        job_id=job,
        owner=owner,
    )


def test_capture_sidecar_streams_a_pcap_until_signalled(client, wait_jobs, topology, fake_engine):
    state = _deployed(client, wait_jobs, topology)
    fake_engine.capture_pps = 1000

    async def run():
        sc = await fake_engine.start_sidecar(state, _spec(["tcpdump", "-i", "eth0", "-w", "-"]))
        out, err = bytearray(), bytearray()
        pump = asyncio.ensure_future(sc.pump(out.extend, err.extend))
        await asyncio.sleep(0.05)
        await sc.signal("SIGINT")
        return await pump, bytes(out), bytes(err)

    code, out, err = client.portal.call(run)
    recs = PcapSplitter().feed(out)
    assert code == 0 and recs and b"packets captured" in err
    assert b"listening on eth0" in err


def test_iperf_client_without_a_server_is_refused(client, wait_jobs, topology, fake_engine):
    state = _deployed(client, wait_jobs, topology)

    async def run():
        sc = await fake_engine.start_sidecar(
            state, _spec(["iperf3", "-c", "10.0.2.5", "--json-stream"], purpose="iperf-client")
        )
        out = bytearray()
        return await sc.pump(out.extend, lambda _b: None), bytes(out)

    code, out = client.portal.call(run)
    assert code == 1 and b"Connection refused" in out


def test_destroy_removes_sidecars_before_the_lab(client, wait_jobs, topology, fake_engine):
    state = _deployed(client, wait_jobs, topology)

    async def start():
        await fake_engine.start_sidecar(state, _spec(["sleep", "infinity"], purpose="probe"))
        await fake_engine.start_sidecar(
            state, _spec(["sleep", "infinity"], node="rA", purpose="probe")
        )

    client.portal.call(start)
    assert len(fake_engine.sidecars) == 2
    client.post(f"/api/v1/topologies/{topology['id']}/destroy")
    wait_jobs()
    kinds = [c[0] for c in fake_engine.calls]
    assert kinds == ["remove_sidecar", "remove_sidecar", "destroy"]
    assert fake_engine.sidecars == {}


def test_sweeps_by_owner_and_purge(client, wait_jobs, topology, fake_engine):
    state = _deployed(client, wait_jobs, topology)

    async def run():
        await fake_engine.start_sidecar(state, _spec(["sleep"], owner="old"))
        await fake_engine.start_sidecar(state, _spec(["sleep"], owner="other"))
        assert {s.owner for s in await fake_engine.list_sidecars(lab_hash=state.lab_hash)} == {
            "old",
            "other",
        }
        assert await fake_engine.remove_sidecars(owner="old") == 1
        await fake_engine.purge(state.lab_hash)
        return await fake_engine.list_sidecars()

    assert client.portal.call(run) == []


def test_startup_sweeps_this_backends_sidecars(tmp_path):
    from fastapi.testclient import TestClient

    from main import create_app
    from tests.conftest import make_settings

    engine = FakeEngine()
    settings = make_settings(tmp_path, instance_id="inst1")
    app = create_app(settings, engine)
    with TestClient(app) as c:
        tid = c.post("/api/v1/topologies", json={"name": "t", "data": TWO_SUBNETS}).json()["id"]
        c.post(f"/api/v1/topologies/{tid}/deploy")
        c.portal.call(app.state.runner.wait_idle)
        state = EngineState.from_dict(c.get(f"/api/v1/topologies/{tid}").json()["engine_state"])

        async def start():
            await engine.start_sidecar(state, _spec(["sleep"], owner="inst1"))
            await engine.start_sidecar(state, _spec(["sleep"], owner="someone-else"))

        c.portal.call(start)
    # A new process with the same instance id removes only its own leftovers.
    with TestClient(create_app(make_settings(tmp_path, instance_id="inst1"), engine)):
        assert [s.spec.owner for s in engine.sidecars.values()] == ["someone-else"]


def test_interfaces_stats_and_runtime_info(client, wait_jobs, topology, fake_engine):
    state = _deployed(client, wait_jobs, topology)

    async def run():
        ifaces = await fake_engine.node_interfaces(state, "rA")
        stats = await fake_engine.sample_stats(state, ["rA", "hA", "gone"])
        info = await fake_engine.node_runtime_info(state)
        return ifaces, stats, info

    ifaces, stats, info = client.portal.call(run)
    assert [(i.name, i.collision_domain) for i in ifaces] == [("eth0", "cd0"), ("eth1", "cd4")]
    assert [s.target for s in stats] == ["rA", "hA"]
    assert set(stats[0].ifaces) == {"eth0", "eth1"} and stats[0].online_cpus == 8
    assert {i.node_id for i in info} == {"rA", "swA", "hA", "rB", "swB", "hB"}
