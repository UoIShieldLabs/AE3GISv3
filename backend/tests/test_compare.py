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
