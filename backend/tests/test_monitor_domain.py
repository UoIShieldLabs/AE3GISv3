"""Monitor sweeps → host rates, classification, rows and aggregates."""

from __future__ import annotations

import json
from pathlib import Path

from domain import monitor as m
from domain import selectors
from engine.base import ContainerRef
from tests.conftest import TWO_SUBNETS

FIXTURE = Path(__file__).parent / "fixtures" / "monitor" / "collect-docker-desktop.ndjson"


def _line(t, cpu, psi_mem_full=0, containers=None, infra=None, mem_available=6 * 2**30):
    return json.dumps(
        {
            "v": 1,
            "t": t,
            "sweep_ms": 3.0,
            "ncpu": 8,
            "clk_tck": 100,
            "page": 4096,
            "host": {
                "cpu": cpu,
                "mem": {"MemTotal": 8 * 2**30, "MemAvailable": mem_available, "Slab": 1},
                "load": [1.5, 1.0, 0.5],
                "psi": {"memory": {"some": [0.0, 0], "full": [0.0, psi_mem_full]}},
                "procs": 200,
            },
            "infra": infra or {},
            "c": containers or {},
        }
    )


def test_real_collector_lines_parse():
    a, b = (m.parse_line(x) for x in FIXTURE.read_text().splitlines())
    assert a is not None and b is not None and b.t > a.t
    row = m.host_rates(a, b)
    assert (
        0 <= row["vm_cpu_pct"] <= 100 and row["mem_used"] == row["mem_total"] - row["mem_available"]
    )
    assert row["infra"]["containerd-shim"]["count"] >= 1
    assert all(r.cpu_total_ns >= 0 for r in b.containers.values())
    assert m.parse_line("not json") is None and m.parse_line('{"error": "x"}') is None


def test_host_rates():
    a = m.parse_line(_line(100.0, [100, 0, 100, 800, 0, 0, 0, 0], infra={"dockerd": [1, 10, 50]}))
    b = m.parse_line(
        _line(
            102.0,
            [300, 0, 200, 1300, 0, 0, 0, 0],
            psi_mem_full=500_000,
            infra={"dockerd": [1, 20, 70]},
        )
    )
    first = m.host_rates(None, a)
    assert (
        first["vm_cpu_pct"] is None
        and first["mem_used"] == 2 * 2**30
        and first["mem_used_pct"] == 25.0
    )
    row = m.host_rates(a, b)
    # 800 ticks passed, 500 idle: 37.5% busy; 300 busy ticks / 100 Hz / 2 s = 1.5 cores.
    assert row["vm_cpu_pct"] == 37.5 and row["cores_used"] == 1.5
    assert row["psi_mem_full"] == 25.0  # 0.5 s stalled of 2 s
    assert row["infra"]["dockerd"] == {"count": 1, "rss": 20, "cpu_pct": 10.0}
    assert row["load1"] == 1.5 and row["procs"] == 200


def _refs():
    return [
        ContainerRef(
            "n1" + "0" * 62, "k_a", "running", {"app": "kathara", "lab_hash": "L", "name": "a"}
        ),
        ContainerRef(
            "n2" + "0" * 62, "k_b", "running", {"app": "kathara", "lab_hash": "L", "name": "b"}
        ),
        ContainerRef(
            "n3" + "0" * 62, "k_x", "running", {"app": "kathara", "lab_hash": "OTHER", "name": "x"}
        ),
        ContainerRef(
            "t1" + "0" * 62,
            "ae3gis-collector-1",
            "running",
            {"ae3gis.sidecar": "1", "ae3gis.purpose": "collector", "ae3gis.job": "j"},
        ),
        ContainerRef("o1" + "0" * 62, "backend", "running", {}),
    ]


def _containers(usage, oom=0):
    iface = {"eth0": [1000 * usage, usage, 0, 0, 500 * usage, usage, 0, 0]}
    return {
        ("n1" + "0" * 62)[:12]: [usage * 1000, 1_000_000, 0, None, 1, oom, iface],
        ("n2" + "0" * 62)[:12]: [usage * 2000, 2_000_000, 0, None, 1, 0, iface],
        ("n3" + "0" * 62)[:12]: [usage, 3_000_000, 0, None, 1, 0, iface],
        ("t1" + "0" * 62)[:12]: [usage, 4_000_000, 0, None, 1, 0, iface],
        ("o1" + "0" * 62)[:12]: [usage, 5_000_000, 0, None, 1, 0, {}],
    }


def test_classify_and_process():
    scope = m.Scope(lab_hash="L", node_for_machine={"a": "nodeA", "b": "nodeB"}, selected={"nodeA"})
    targets = m.classify(_refs(), scope)
    assert {t.kind for t in targets.values()} == {"node", "other_lab", "tool", "other"}
    assert targets[("n1" + "0" * 62)[:12]].name == "nodeA"
    assert targets[("t1" + "0" * 62)[:12]].purpose == "collector"

    cpu = [0, 0, 0, 1000, 0, 0, 0, 0]
    a = m.parse_line(_line(10.0, cpu, containers=_containers(1)))
    b = m.parse_line(_line(12.0, cpu, containers=_containers(3, oom=1)))
    first = m.process(None, a, targets, scope, t0=10.0)
    assert first.t == 0.0 and first.oom == []
    r = m.process(a, b, targets, scope, t0=10.0)
    assert r.t == 2.0 and r.oom == ["nodeA"] and r.seen_nodes == {"nodeA", "nodeB"}
    # Only the selected node and the tools get rows; the tool carries no interfaces.
    assert [(row["target"], row["kind"]) for row in r.nodes] == [
        ("nodeA", "node"),
        ("ae3gis-collector-1", "tool"),
    ]
    node, tool = r.nodes
    assert node["cpu_pct"] == 0.1 and node["rx_bps"] == 8000 and node["tx_bps"] == 4000
    assert node["oom_kills"] == 1 and tool["purpose"] == "collector" and tool["rx_bps"] is None
    assert [i["iface"] for i in r.ifaces] == ["eth0"] and r.ifaces[0]["target"] == "nodeA"
    assert r.groups["node"]["count"] == 2 and r.groups["node"]["mem_used"] == 3_000_000
    assert r.groups["other_lab"]["count"] == 1 and r.groups["other"]["mem_used"] == 5_000_000


def test_selection_summary_and_percentiles():
    rows = [
        {
            "target": f"n{i}",
            "kind": "node",
            "cpu_pct": float(i),
            "mem_used": i * 10,
            "rx_bps": i,
            "tx_bps": 1,
        }
        for i in range(1, 11)
    ] + [{"target": "tool", "kind": "tool", "cpu_pct": 99.0}]
    s = m.selection_summary(rows, top=2)
    assert s["count"] == 10 and s["cpu_pct"]["max"] == 10.0 and s["cpu_pct"]["mean"] == 5.5
    assert s["cpu_pct"]["p95"] == 9.55 and s["cpu_pct"]["sum"] == 55.0
    assert s["top"]["cpu_pct"] == [["n10", 10.0], ["n9", 9.0]]
    assert s["top"]["net_bps"][0] == ["n10", 11]
    assert m.percentile([], 50) is None and m.percentile([4.0], 95) == 4.0
    rs = m.RunningStats()
    for v in (1, None, 3):
        rs.add(v)
    assert rs.to_dict() == {"mean": 2.0, "max": 3}


def test_selectors():
    deployed = ["rA", "swA", "hA", "rB", "swB", "hB"]
    assert selectors.resolve(TWO_SUBNETS, deployed, "all") == deployed
    assert selectors.resolve(TWO_SUBNETS, deployed, ["hB", "hA", "ghost"]) == ["hA", "hB"]
    assert selectors.resolve(TWO_SUBNETS, deployed, {"roles": ["host"]}) == ["hA", "hB"]
    assert selectors.resolve(TWO_SUBNETS, deployed, {"types": ["router"], "subnets": ["subB"]}) == [
        "rB"
    ]
    assert selectors.resolve(TWO_SUBNETS, deployed, {"subnets": ["subA"], "exclude": ["swA"]}) == [
        "rA",
        "hA",
    ]
    assert selectors.resolve(TWO_SUBNETS, ["hA"], {"ids": ["hA", "hB"]}) == ["hA"]
    index = selectors.node_index(TWO_SUBNETS)
    assert index["hA"]["ip"] == "10.0.1.5" and index["rA"]["role"] == "router"
