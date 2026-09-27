"""The tools image's helper scripts: their pure parsers and one full sweep
over a fake /proc and cgroup tree (the scripts run in Python 3.12 on Alpine)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools" / "nettools"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collect = _load("ae3gis_collect")
netns = _load("ae3gis_netns")

PROC_STAT = """cpu  1745 0 453 205565 154 0 232 0 0 0
cpu0 200 0 50 25000 10 0 30 0 0 0
intr 12345
"""
MEMINFO = """MemTotal:        8022576 kB
MemFree:         7016828 kB
MemAvailable:    7285724 kB
Buffers:           10000 kB
Cached:           387352 kB
Slab:              55712 kB
SwapTotal:       1048572 kB
SwapFree:        1048572 kB
"""
PSI = """some avg10=1.23 avg60=0.50 avg300=0.10 total=1077691
full avg10=0.00 avg60=0.00 avg300=0.00 total=0
"""
NET_DEV = """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo:     500       5    0    0    0     0          0         0      500       5    0    0    0     0       0          0
 tunl0:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0
  eth0:    1106      13    1    2    0     0          0         0      126       3    0    4    0     0       0          0
  eth1:    9000      90    0    0    0     0          0         0     8000      80    0    0    0     0       0          0
"""
TCP6 = """  sl  local_address                         remote_address                        st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 00000000000000000000000000000000:1451 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 1 1 0000000000000000 100 0 0 10 0
   1: 00000000000000000000000000000000:1452 00000000000000000000000000000000:0000 01 00000000:00000000 00:00000000 00000000     0        0 1 1 0000000000000000 100 0 0 10 0
"""


def test_proc_parsers():
    assert collect.parse_cpu(PROC_STAT) == [1745, 0, 453, 205565, 154, 0, 232, 0]
    mem = collect.parse_meminfo(MEMINFO)
    assert mem["MemTotal"] == 8022576 * 1024 and mem["MemAvailable"] == 7285724 * 1024
    assert "Buffers" not in mem
    assert collect.parse_psi(PSI) == {"some": [1.23, 1077691], "full": [0.0, 0]}
    assert collect.parse_net_dev(NET_DEV) == {
        "eth0": [1106, 13, 1, 2, 126, 3, 0, 4],
        "eth1": [9000, 90, 0, 0, 8000, 80, 0, 0],
    }
    assert collect.parse_flat_keyed("usage_usec 15131\nuser_usec 9\nbad x\n") == {
        "usage_usec": 15131,
        "user_usec": 9,
    }


def test_proc_stat_with_awkward_comm():
    fields = ["S"] + ["0"] * 10 + ["120", "30"] + ["0"] * 8 + ["2500"] + ["0"] * 20
    text = "4242 (my (odd) proc) " + " ".join(fields)
    assert collect.parse_proc_stat(text) == ("my (odd) proc", 150, 2500)


def test_listening_ports_from_tcp6():
    assert netns.listening_ports(TCP6) == {0x1451}  # 5201, LISTEN only


def _cgroup(root: Path, rel: str, pid: int, usage: int, mem: int) -> None:
    d = root / rel
    d.mkdir(parents=True)
    (d / "cpu.stat").write_text(f"usage_usec {usage}\nuser_usec 1\n")
    (d / "memory.current").write_text(f"{mem}\n")
    (d / "memory.stat").write_text("anon 10\ninactive_file 4096\n")
    (d / "memory.max").write_text("max\n")
    (d / "pids.current").write_text("2\n")
    (d / "memory.events").write_text("low 0\noom 0\noom_kill 1\n")
    (d / "cgroup.procs").write_text(f"{pid}\n{pid + 1}\n")


def test_full_sweep_over_a_fake_host(tmp_path):
    proc, cg = tmp_path / "proc", tmp_path / "cgroup"
    (proc / "pressure").mkdir(parents=True)
    (proc / "stat").write_text(PROC_STAT)
    (proc / "meminfo").write_text(MEMINFO)
    (proc / "loadavg").write_text("0.50 0.25 0.10 1/200 999\n")
    (proc / "pressure" / "memory").write_text(PSI)
    stat_fields = ["S"] + ["0"] * 10 + ["100", "50"] + ["0"] * 8 + ["1000"] + ["0"] * 20
    for pid, comm in (
        (10, "dockerd"),
        (11, "containerd-shim"),
        (12, "containerd-shim"),
        (13, "bash"),
    ):
        (proc / str(pid) / "net").mkdir(parents=True)
        (proc / str(pid) / "stat").write_text(f"{pid} ({comm}) " + " ".join(stat_fields))
        (proc / str(pid) / "net" / "dev").write_text(NET_DEV)
    a, b = "a" * 64, "b" * 64
    _cgroup(cg, f"docker/{a}", 11, 5000, 2_000_000)  # cgroupfs driver (Docker Desktop)
    _cgroup(cg, f"system.slice/docker-{b}.scope", 12, 7000, 3_000_000)  # systemd
    (cg / "docker" / "not-a-container").mkdir()

    line = collect.sweep(str(cg), str(proc))
    json.dumps(line)  # serialisable as printed
    assert line["v"] == 1 and set(line["c"]) == {"a" * 12, "b" * 12}
    assert line["c"]["a" * 12][:6] == [5000, 2_000_000, 4096, None, 2, 1]
    assert set(line["c"]["a" * 12][6]) == {"eth0", "eth1"}
    assert line["host"]["cpu"][3] == 205565 and line["host"]["load"] == [0.5, 0.25, 0.1]
    assert line["host"]["psi"]["memory"]["some"] == [1.23, 1077691]
    assert line["host"]["procs"] == 4
    page = line["page"]
    assert line["infra"] == {
        "dockerd": [1, 1000 * page, 150],
        "containerd-shim": [2, 2000 * page, 300],
    }


@pytest.mark.parametrize("missing", ["docker", "system.slice"])
def test_container_dirs_tolerate_missing_trees(tmp_path, missing):
    (tmp_path / ("system.slice" if missing == "docker" else "docker")).mkdir()
    assert collect.container_dirs(str(tmp_path)) == {}
