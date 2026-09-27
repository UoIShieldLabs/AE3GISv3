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
