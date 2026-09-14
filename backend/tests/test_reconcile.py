from domain.plan import build_lab_plan
from tests.conftest import TWO_SUBNETS


def test_reconcile_classifies_and_purges(client, topology, wait_jobs, fake_engine):
    tid = topology["id"]
    client.post(f"/api/v1/topologies/{tid}/deploy")
    wait_jobs()

    # an orphan lab nobody tracks
    async def _make_orphan():
        await fake_engine.deploy(build_lab_plan(TWO_SUBNETS, "ae3gis_orphan"), lambda _m: None)

    client.portal.call(_make_orphan)

    report = client.get("/api/v1/system/labs").json()
    by_class = {lab["classification"]: lab for lab in report["labs"]}
    assert by_class["tracked"]["topology_id"] == tid and by_class["tracked"]["running"] == 6
    assert by_class["orphan"]["topology_id"] is None
    assert report["stale"] == []

    r = client.post(f"/api/v1/system/labs/{by_class['orphan']['lab_hash']}/purge")
    assert r.status_code == 200 and r.json()["topology_id"] is None
    assert len(client.get("/api/v1/system/labs").json()["labs"]) == 1

    # the engine loses the tracked lab (e.g. containers removed by hand) -> stale -> reset
    fake_engine.labs.clear()
    report = client.get("/api/v1/system/labs").json()
    assert report["stale"] and report["stale"][0]["topology_id"] == tid
    assert client.post("/api/v1/system/reconcile").json()["reset"] == 1
    rec = client.get(f"/api/v1/topologies/{tid}").json()
    assert rec["status"] == "idle" and rec["engine_state"] is None
    assert any(
        e["type"] == "reconcile.stale"
        for e in client.get(f"/api/v1/topologies/{tid}/events").json()
    )
