"""Benchmark metrics, stop criteria and the report."""

from domain import benchmark as bm

STOP = {"max_mem_pct": 90, "max_psi_mem_full": 10, "min_delivered_ratio": 0.8, "max_loss_pct": 5}


def test_watch_needs_sustained_host_thresholds_but_not_for_ooms():
    w = bm.Watch(STOP, interval_s=1)
    hot = {"mem_used_pct": 95.0, "psi_mem_full": 0, "sweep_ms": 5}
    assert w.check(hot, {}) is None and w.check(hot, {}) is None
    assert w.check(hot, {})[0] == "memory"
    w.reset()
    assert w.check(hot, {}) is None and w.check({"mem_used_pct": 50}, {}) is None  # streak broken
    assert w.check({}, {"oom": ["h1"]}) == ("oom", "out of memory: h1")
    assert w.check({}, {"missing": ["h2"]})[0] == "node_exited"
    lag = {"sweep_ms": 1500.0}
    for _ in range(2):
        assert w.check(lag, {}) is None
    assert w.check(lag, {})[0] == "monitor_lag"


def test_traffic_verdict():
    assert bm.traffic_verdict({"delivered_ratio": 0.5}, STOP)[0] == "traffic_short"
    assert (
        bm.traffic_verdict({"delivered_ratio": 0.9, "lost_percent": 9}, STOP)[0] == "traffic_loss"
    )
    assert bm.traffic_verdict({"flows": 3, "flows_without_data": 3}, STOP)[0] == "traffic_none"
    assert (
        bm.traffic_verdict({"delivered_ratio": 0.95, "lost_percent": 0.1, "flows": 3}, STOP) is None
    )
    assert bm.traffic_verdict(None, STOP) is None


def test_step_metrics():
    host = [
        {
            "t": float(t),
            "mem_used": 1000 if t < 10 else 1000 + 50 * 10,
            "vm_cpu_pct": float(t),
            "dockerd_rss": 100,
            "containerd_shim_rss": 10 if t < 10 else 10 + 20 * 10,
            "sweep_ms": 5.0,
            "dockerd_cpu_pct": 30.0,
            "containerd_cpu_pct": 20.0,
        }
        for t in range(30)
    ]
    agg = [
        {
            "t": float(t),
            "count": 10,
            "mem_mean": 2.0,
            "mem_p95": 3.0,
            "cpu_mean": 1.0,
            "cpu_p95": 2.0,
            "rx_sum": 100.0,
        }
        for t in range(30)
    ]
    out = bm.step_metrics(
        host, agg, {"pre": (0, 9), "settle": (10, 19), "hold": (20, 29)}, nodes=10
    )
    assert out["marginal_mem_per_node"] == 50 and out["docker_mem_per_node"] == 20
    assert out["node_mem_mean"] == 2 and out["node_mem_p95"] == 3 and out["nodes_seen"] == 10
    assert out["hold_cpu_mean"] == 24.5 and out["hold_cpu_p95"] == 28.55
    assert out["sweep_ms_p95"] == 5.0
    assert out["hold_docker_cpu_mean"] == 50.0
    empty = bm.step_metrics(host, agg, {"pre": None, "settle": None, "hold": None}, nodes=10)
    assert empty["marginal_mem_per_node"] is None and empty["hold_cpu_mean"] is None


def test_scales_ceiling_and_report():
    rows = [
        {"scale": 10, "rep": 1, "outcome": "ok", "deploy_s": 4.0, "nodes": 16},
        {"scale": 10, "rep": 2, "outcome": "ok", "deploy_s": 6.0, "nodes": 16},
        {"scale": 20, "rep": 1, "outcome": "ok", "deploy_s": 9.0, "nodes": 27},
        {
            "scale": 40,
            "rep": 1,
            "outcome": "stopped",
            "reason": "memory",
            "detail": "host memory 95%",
        },
    ]
    scales = bm.by_scale(rows)
    assert [s["scale"] for s in scales] == [10, 20, 40]
    assert scales[0]["deploy_s"] == {"mean": 5.0, "std": 1.414, "min": 4.0, "max": 6.0}
    assert bm.ceiling(rows) == 20
    md = bm.markdown_report(
        {"rows": rows, "ceiling": 20, "reason": "memory", "detail": "host memory 95%"},
        {"label": "idle", "scale": [10, 20, 40], "topology": {"generate": {}}},
        {"fingerprint": "abc"},
    )
    assert "# Benchmark: idle" in md and "ceiling 20 hosts" in md
    assert "| 40 | 1 |" in md and "stopped: host memory 95%" in md


def test_projected_memory():
    rows = [{"outcome": "ok", "marginal_mem_per_node": 10e6}]
    host = {"mem_used": 2e9, "mem_total": 8e9}
    assert bm.projected_memory(rows, host, 400, {"max_mem_pct": 90}) is None  # 6 GB of 7.2
    reason, detail = bm.projected_memory(rows, host, 600, {"max_mem_pct": 90})
    assert reason == "projected_memory" and "~8.0 GB" in detail
    assert (
        bm.projected_memory(rows, host, 600, {"max_mem_pct": 90, "project_memory": False}) is None
    )
    assert bm.projected_memory([], host, 600, {"max_mem_pct": 90}) is None  # nothing measured yet


def test_report_of_a_running_sweep():
    md = bm.markdown_report(
        {"rows": [], "started_at": "2026-09-27T00:00:00+00:00", "ended_at": None, "phase": "x"},
        {"label": "live", "scale": [10], "topology": {"generate": {}}},
        {},
    )
    assert "→ still running" in md


def test_per_image_numbers_and_table():
    image_of = {"h1": "ae3gis.local/firefox", "h2": "kathara/base", "h3": "kathara/base"}
    rows = []
    for t, firefox_mb in ((10, 300e6), (20, 320e6), (40, 999e6)):
        nodes = [
            {"target": "h1", "kind": "node", "mem_used": firefox_mb, "cpu_pct": 2.0},
            {"target": "h2", "kind": "node", "mem_used": 1e6, "cpu_pct": 0.0},
            {"target": "h3", "kind": "node", "mem_used": 3e6, "cpu_pct": None},
            {"target": "collector", "kind": "tool", "mem_used": 8e6, "cpu_pct": 1.0},
            {"target": "gone", "kind": "node", "mem_used": 5e6, "cpu_pct": 1.0},
        ]
        rows += bm.image_sweep(t, nodes, image_of)
    assert {r["image"] for r in rows} == {"ae3gis.local/firefox", "kathara/base"}
    windows = {"settle": (5, 25), "hold": (30, 45)}
    by_image = bm.image_metrics(rows, windows)
    assert by_image["ae3gis.local/firefox"] == {"count": 1, "mem_mean": 310e6, "cpu_mean": 2.0}
    assert by_image["kathara/base"] == {"count": 2, "mem_mean": 2e6, "cpu_mean": 0.0}

    steps = [
        {"scale": 10, "rep": 1, "outcome": "ok", "by_image": by_image},
        {"scale": 20, "rep": 1, "outcome": "failed", "by_image": {"x": {"count": 1}}},
    ]
    spec = {
        "label": "mixed",
        "scale": [10, 20],
        "topology": {
            "generate": {
                "host_mix": [
                    {"type": "workstation", "image": "ae3gis.local/firefox", "weight": 1},
                    {"type": "workstation", "weight": 3},
                ],
                "server_mix": [
                    {"type": "dns-server", "count": 1},
                    {"type": "web-server", "image": "ae3gis.local/nginx", "per_hosts": 50},
                ],
                "core_type": "firewall",
                "core_image": "ae3gis.local/iptables",
                "seed": 1,
            }
        },
    }
    md = bm.markdown_report({"rows": steps}, spec, {})
    assert "Per image at 10 hosts" in md
    assert "| `ae3gis.local/firefox` | 1 | 310.0 | 98.7% | 2.00 |" in md
    assert "| `kathara/base` | 2 | 2.0 | 1.3% | 0.00 |" in md
    assert "`x`" not in md  # only the largest passing scale
    assert "Hosts: workstation · firefox 25%, workstation 75%" in md
    assert "dns-server ×1, web-server · nginx 1/50 hosts" in md
    assert "Core: firewall · iptables" in md
    # a custom core alone is reported too
    core_only = {"label": "fw", "topology": {"generate": {"core_type": "firewall"}}}
    assert "Core: firewall" in bm.markdown_report({"rows": []}, core_only, {})


def test_next_scale_climbs_fast_then_slows_near_the_target():
    a = {"target_mem_pct": 93, "reach_mem_pct": 90, "approach": 0.6, "max_factor": 2.0}
    a["min_step"] = 25
    total = 16e9

    def nodes_for(hosts):  # ~1.1 nodes per host, like the generated campus
        return round(hosts * 1.1) + 5

    def row(scale, peak, per_node=12e6, pre=1e9):
        return {
            "scale": scale,
            "hold_mem_pct_max": peak,
            "marginal_mem_per_node": per_node,
            "mem_pre": pre,
        }

    # 93% of 16 GB with 1 GB resting at 12 MB/node: ~1156 nodes, 1046 hosts
    nxt, code, why = bm.next_scale(
        row(400, 35), a, mem_total=total, nodes_for=nodes_for, max_scale=14720
    )
    assert code == "next" and nxt == 800  # 400 + 0.6 × 646 ≈ 788, in steps of 25
    assert "projected at 1046 hosts" in why
    nxt, _, _ = bm.next_scale(
        row(200, 18), a, mem_total=total, nodes_for=nodes_for, max_scale=14720
    )
    assert nxt == 400  # at most ×2
    nxt, _, _ = bm.next_scale(
        row(1000, 88), a, mem_total=total, nodes_for=nodes_for, max_scale=14720
    )
    assert nxt == 1025  # 0.6 × 48 → rounds to the 25-host minimum
    nxt, code, why = bm.next_scale(
        row(1050, 89), a, mem_total=total, nodes_for=nodes_for, max_scale=14720
    )
    assert (nxt, code) == (1075, "next") and "+25" in why  # projected at/below: nudge
    # done: the peak reached the target, or the generator's largest topology
    assert bm.next_scale(row(1075, 90.4), a, mem_total=total, nodes_for=nodes_for, max_scale=14720)[
        :2
    ] == (None, "limit_reached")
    assert bm.next_scale(row(500, 40), a, mem_total=total, nodes_for=nodes_for, max_scale=500)[
        :2
    ] == (None, "max_scale")
    nxt, _, _ = bm.next_scale(row(400, 40), a, mem_total=total, nodes_for=nodes_for, max_scale=450)
    assert nxt == 425  # the projection stops at the largest topology: 400 + 0.6 × 50
    nxt, _, why = bm.next_scale(
        row(400, 35, per_node=None), a, mem_total=total, nodes_for=nodes_for, max_scale=14720
    )
    assert nxt == 600 and "×1.5" in why
    # ×max_factor caps min_step and its rounding too
    nxt, _, _ = bm.next_scale(
        row(100, 35),
        {**a, "max_factor": 1.1},
        mem_total=total,
        nodes_for=nodes_for,
        max_scale=14720,
    )
    assert nxt == 110  # not 125
    nxt, _, _ = bm.next_scale(row(10, 2), a, mem_total=total, nodes_for=nodes_for, max_scale=14720)
    assert nxt == 20  # ×2 from 10 hosts, though the minimum step is 25
