"""The AE3GIS vs GNS3 comparison runner's pure parts (scripts/compare_lib)."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from compare_lib import hostsample, labs, metrics, traffic  # noqa: E402
from compare_lib.gns3 import Gns3  # noqa: E402
from compare_lib.steps import Runner, rate_bps  # noqa: E402
from compare_lib.target import Target  # noqa: E402


def test_host_sampler_parsers():
    assert hostsample.cputime("1:23.45") == pytest.approx(83.45)
    assert hostsample.cputime("2:01:00.00") == 7260
    assert hostsample.cputime("1-00:00:01.5") == pytest.approx(86401.5)
    assert hostsample.size("5042M") == 5042 * 2**20
    assert hostsample.size("8.5G+") == int(8.5 * 2**30)
    assert hostsample.size("n/a") is None
    assert hostsample.parse_cpu_line("CPU usage: 9.72% user, 14.3% sys, 76.23% idle") == {
        "user": 9.72,
        "sys": 14.3,
        "idle": 76.23,
    }
    pm = hostsample.parse_physmem("PhysMem: 31G used (2836M wired, 9573M compressor), 182M unused.")
    assert pm == {
        "used": 31 * 2**30,
        "wired": 2836 * 2**20,
        "compressor": 9573 * 2**20,
        "unused": 182 * 2**20,
    }


def test_lab_files_pin_images_and_their_start_commands():
    lab = labs.load(25)
    images = lab.doc["images"]
    assert set(images) == {n["image"] for n in lab.nodes}
    assert all(v["digest"].startswith("sha256:") and v["run"] for v in images.values())
    roles = {n["role"]: n["image"] for n in lab.nodes}
    assert roles["switch"].startswith("kathara/base") and roles["router"].startswith("tollan/")


def test_gns3_nodes_set_links_up_then_boot_then_exec_the_image_command():
    lab = labs.load(25)
    g = Gns3("http://vm", Target("t"))
    router = next(n for n in lab.nodes if n["role"] == "router")
    script = shlex.split(g.node_body(lab, router)["properties"]["start_command"])[2]
    links, boot, run = (
        script.index("ip link set"),
        script.index("/ae3gis-init.sh"),
        script.index("exec"),
    )
    assert links < boot < run
    assert script.endswith("exec " + shlex.join(lab.run(router)))


def _iperf_line(start: float, end: float, nbytes: int, sender: bool, **extra) -> str:
    data = {
        "streams": [],
        "sum": {
            "start": start,
            "end": end,
            "seconds": end - start,
            "bytes": nbytes,
            "bits_per_second": nbytes * 8 / (end - start),
            "sender": sender,
            **extra,
        },
    }
    return json.dumps({"event": "interval", "data": data})


def test_load_summary_counts_receiver_bytes_in_the_window():
    events = [
        {"k": "started", "p": "f1.s", "t": 100.0, "attempt": 0},
        {"k": "started", "p": "f1.c", "t": 100.5, "attempt": 0},
        {"k": "clients_started", "n": 1, "failed": [], "never_started": [], "t": 100.5},
    ]
    # The server receives 125000 bytes a second (1 Mb/s) for 12 s; the window is 10 s.
    for i in range(12):
        events.append(
            {
                "k": "out",
                "p": "f1.s",
                "line": _iperf_line(
                    i + 0.5,
                    i + 1.5,
                    125000,
                    False,
                    packets=100,
                    lost_packets=1 if i == 3 else 0,
                    jitter_ms=0.2,
                ),
            }
        )
    s = traffic.load_summary(events, n_flows=1, rate_bps=1e6, window_s=10)
    assert s["flows_measured"] == 1
    assert s["delivered_ratio"] == pytest.approx(1.0, abs=0.11)
    assert s["loss"] == pytest.approx(1 / 1000, rel=0.2)
    assert s["jitter_ms"] == pytest.approx(0.2)
    assert traffic.load_summary(events[:2], n_flows=1, rate_bps=1e6, window_s=10)["error"]


def test_ping_summary():
    events = [{"k": "started", "p": "ping0", "t": 1}] + [
        {"k": "out", "p": "ping0", "line": f"64 bytes from 10.0.0.1: seq={i} ttl=64 time={t} ms"}
        for i, t in enumerate([0.5, 0.6, 0.7, 2.0])
    ]
    s = traffic.ping_summary(events, count=5)
    assert (s["replies"], s["sent"], s["max_ms"]) == (4, 5, 2.0)
    assert s["p50_ms"] in (0.6, 0.7)


def test_vm_cpu_and_container_metrics():
    def line(t, ticks, c):
        return {
            "t": t,
            "ncpu": 4,
            "clk_tck": 100,
            "host": {"cpu": ticks, "mem": {"MemTotal": 1000, "MemAvailable": 400}},
            "c": c,
            "infra": {"ubridge": [2, 50, t * 100]},
        }

    # 400 ticks per second across 4 CPUs; 100 of them busy → a quarter, 1 core.
    lines = [
        line(0, [0, 0, 0, 0, 0, 0, 0, 0], {"aaa": [0, 300, 100, None, 1, 0, {}]}),
        line(1, [100, 0, 0, 300, 0, 0, 0, 0], {"aaa": [500000, 300, 100, None, 1, 0, {}]}),
    ]
    cpu = metrics.vm_cpu(lines)
    assert cpu == [(1, 0.25, 1.0)]
    w = metrics.monitor_window(lines, {"aaa"})
    assert w["mem_used"] == 600
    assert w["containers"]["lab_mem"] == 200 and w["containers"]["lab_cores"] == 0.5
    assert w["infra"]["ubridge"]["cores"] == pytest.approx(1.0)


def test_rates():
    assert rate_bps("100K") == 1e5 and rate_bps("2M") == 2e6 and rate_bps("1G") == 1e9


def test_the_extra_size_runs_only_when_its_projected_memory_fits(tmp_path):
    plan = {"e1": {"sizes": [25, 400], "extra_size": 800, "extra_max_mem_share": 0.85}}
    runner = Runner(plan, {}, "img", tmp_path, log=lambda *_: None)

    class P:
        name = "ae3gis"

    def record(ref, hold, total):
        path = tmp_path / "ae3gis" / "e1-h400-r1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "phases": {
                        "reference": {"vm": {"mem_used": ref}},
                        "hold": {"vm": {"mem_used": hold, "mem_total": total}},
                    }
                }
            )
        )

    assert not runner.extra_fits(P, 1)  # no 400 result yet
    record(ref=2, hold=7, total=16)  # 2 + 2 × 5 = 12 ≤ 13.6
    assert runner.extra_fits(P, 1)
    record(ref=2, hold=8, total=16)  # 2 + 2 × 6 = 14 > 13.6
    assert not runner.extra_fits(P, 1)


# ── summaries ──


def _e1_record(platform, size, rep, *, ref_mem, hold_mem, lab_mem, nodes, status="ok"):
    def window(mem, lab=0.0, fp=1.0 * 2**30, cores=0.5):
        return {
            "t": [0, 1],
            "vm": {
                "mem_used": mem,
                "mem_used_max": mem,
                "cpu_cores": 0.1,
                "containers": {"lab_mem": lab},
                "infra": {},
            },
            "host": {
                "vm": {"footprint": fp, "footprint_max": fp, "cores": cores},
                "helpers": {"footprint": 0.25 * 2**30, "footprint_max": 0.25 * 2**30, "cores": 0.1},
            },
        }

    return {
        "exp": "e1",
        "platform": platform,
        "size": size,
        "rep": rep,
        "nodes": nodes,
        "status": status,
        # the runner's first version: the teardown's timings landed in "deploy"
        "deploy": {"deploy_s": 10.0, "stop_s": 2.0},
        "destroy_s": 4.0,
        "phases": {
            "reference": window(ref_mem),
            "deploy": window(hold_mem, lab_mem, fp=2.0 * 2**30),
            "ready": {**window(hold_mem, lab_mem), "t": [10, 12.5]},
            "hold": window(hold_mem, lab_mem, fp=1.5 * 2**30, cores=1.0),
            "after": window(ref_mem + 100),
        },
    }


def test_an_e1_row_is_growth_over_its_own_reference():
    from compare_lib import summary

    rec = _e1_record("ae3gis", 25, 1, ref_mem=1000, hold_mem=4000, lab_mem=1000, nodes=30)
    r = summary.e1_row(rec)
    assert r["usable_s"] == pytest.approx(12.5)
    assert r["vm_mem_growth"] == 3000 and r["vm_mem_per_node"] == 100
    assert r["platform_mem_growth"] == 2000  # growth minus the lab's containers
    assert r["vm_mem_after"] == 100
    assert r["host_footprint_growth"] == pytest.approx(0.5 * 2**30)
    assert r["host_footprint_peak_growth"] == pytest.approx(1.0 * 2**30)
    assert r["host_cores_hold"] == pytest.approx(1.1)
    assert r["timings"]["stop_s"] == 2.0


def test_e1_table_counts_only_ok_reps(tmp_path):
    from compare_lib import summary

    for rep, (hold, st) in enumerate([(4000, "ok"), (6000, "ok"), (9999, "not_ready")], 1):
        write = tmp_path / "gns3" / f"e1-h25-r{rep}.json"
        write.parent.mkdir(parents=True, exist_ok=True)
        rec = _e1_record(
            "gns3", 25, rep, ref_mem=1000, hold_mem=hold, lab_mem=0, nodes=30, status=st
        )
        write.write_text(json.dumps(rec))
    cell = summary.e1_table(summary.load(tmp_path))["gns3"][25]
    assert (cell["reps"], cell["ok"]) == (3, 2)
    assert cell["vm_mem_growth"] == {"n": 2, "mean": 4000, "min": 3000, "max": 5000}
    assert cell["statuses"] == ["not_ready", "ok"]


def _step(rate, passed, repeat=False, delivered=None, flows=10):
    return {
        "rate": rate,
        "passed": passed,
        "repeat": repeat,
        "flows": flows,
        "delivered_bps": delivered if delivered is not None else rate_bps(rate) * flows,
    }


def test_a_ladder_keeps_the_highest_rate_every_run_passed():
    from compare_lib import summary

    # 1M passed, then failed its repeat: 500K is the result.
    steps = [
        _step("500K", True),
        _step("1M", True),
        _step("2M", False),
        _step("1M", False, True),
        _step("2M", False, True),
    ]
    assert summary.ladder_result(steps)["max_rate"] == "500K"
    # A failure that passes on its repeat stays a failure.
    steps = [
        _step("500K", True),
        _step("1M", False),
        _step("500K", True, True),
        _step("1M", True, True),
    ]
    r = summary.ladder_result(steps)
    assert r["max_rate"] == "500K" and r["max_offered_bps"] == 5e6
    # Nothing passed.
    assert (
        summary.ladder_result([_step("100K", False), _step("100K", False, True)])["max_rate"]
        is None
    )


def test_cpu_per_100mbps_is_over_the_idle_reference():
    from compare_lib import summary

    ref = {"host": {"vm": {"cores": 0.5}}, "vm": {"cpu_cores": 0.1}}
    s = {"delivered_bps": 2e8, "host": {"vm": {"cores": 2.5}}, "vm": {"cpu_cores": 1.1}}
    cpu = summary._step_cpu(s, ref)
    assert cpu["host_cores_per_100m"] == pytest.approx(1.0)
    assert cpu["vm_cores_per_100m"] == pytest.approx(0.5)


def test_the_summary_renders_from_step_files(tmp_path):
    from compare_lib import summary

    (tmp_path / "manifest.json").write_text(json.dumps({"host": {"host": "h"}, "commit": "abc"}))
    for p, hold in (("ae3gis", 3000), ("gns3", 4000)):
        d = tmp_path / p
        d.mkdir()
        (d / "e1-h25-r1.json").write_text(
            json.dumps(_e1_record(p, 25, 1, ref_mem=1000, hold_mem=hold, lab_mem=0, nodes=30))
        )
        (d / "e1-h50-r1.json").write_text(
            json.dumps({"exp": "e1", "platform": p, "size": 50, "rep": 1, "status": "capped"})
        )
        ladder = [{**_step("1M", True), "pattern": "cs", "protocol": "udp"}]
        (d / "e2.json").write_text(
            json.dumps({"status": "ok", "latency": {"same_lan": {"p50_ms": 0.4}}, "ladder": ladder})
        )
    s = summary.summarize(tmp_path)
    md = summary.markdown(s)
    assert "| 25 | 30 | 1/1 / 1/1 |" in md
    assert "capped / capped" in md
    assert s["e2_common"]["cs/udp"]["rate"] == "1M"
    assert "- ae3gis e1-h50-r1: capped" in md
