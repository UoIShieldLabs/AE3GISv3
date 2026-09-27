#!/usr/bin/env python3
"""AE3GIS resource collector: one JSON line per sweep on stdout.

Runs in a helper container that shares the host's PID and cgroup namespaces,
with the host's cgroup tree mounted read-only (``--root``). Each sweep reads,
for the host (on Docker Desktop: its Linux VM) and every Docker container:

- host: ``/proc/stat`` CPU ticks, ``/proc/meminfo``, load, PSI stall totals,
  process count; per-name totals for Docker's own processes (``infra``)
- containers: cgroup v2 CPU usage, memory, pids and OOM kills, and the
  interface counters of the container's network namespace (read through
  ``/proc/<pid>/net/dev`` of any process in it, no ``setns`` needed)

One process reads files; nothing asks the Docker daemon, so the cost stays
flat as containers are added (``sweep_ms`` reports it). Counters are
cumulative; the backend turns them into rates. The parsing functions are pure
so the backend's tests import this file.

Line format (compact on purpose, ~120 bytes per container)::

    {"v": 1, "t": <unix s>, "sweep_ms": .., "ncpu": .., "clk_tck": .., "page": ..,
     "host": {"cpu": [user, nice, system, idle, iowait, irq, softirq, steal],
              "mem": {"MemTotal": bytes, ...}, "load": [1, 5, 15], "procs": n,
              "psi": {"cpu": {"some": [avg10, total_us], "full": [...]}, ...}},
     "infra": {"dockerd": [count, rss_bytes, cpu_ticks], ...},
     "c": {"<id12>": [usage_usec, mem_current, inactive_file, mem_max|null,
                      pids|null, oom_kills|null, {"eth0": [rx_bytes, rx_packets,
                      rx_errs, rx_drop, tx_bytes, tx_packets, tx_errs, tx_drop]}]}}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
import time

# Interfaces every network namespace has (the kernel's fallback tunnel devices).
SKIP_IFACES = frozenset(
    {"lo", "tunl0", "gre0", "gretap0", "erspan0", "ip_vti0", "ip6_vti0", "sit0", "ip6tnl0"}
    | {"ip6gre0"}
)
# /proc/<pid>/stat comm (truncated to 15 characters) -> reported name.
INFRA = {
    "dockerd": "dockerd",
    "containerd": "containerd",
    "containerd-shim": "containerd-shim",
    "vde_switch": "vde_switch",
}
MEM_KEYS = ("MemTotal", "MemFree", "MemAvailable", "Cached", "Slab", "SwapTotal", "SwapFree")
_ID = re.compile(r"^[0-9a-f]{64}$")
_SCOPE = re.compile(r"^docker-([0-9a-f]{64})\.scope$")


# ── pure parsers ──────────────────────────────────────────────────────


def parse_cpu(text: str) -> list[int]:
    """The aggregate ``cpu`` line of /proc/stat: the first 8 tick counters."""
    for line in text.splitlines():
        if line.startswith("cpu "):
            return [int(x) for x in line.split()[1:9]]
    return []


def parse_meminfo(text: str) -> dict[str, int]:
    """Selected /proc/meminfo fields, in bytes."""
    out: dict[str, int] = {}
    for line in text.splitlines():
        key, _, rest = line.partition(":")
        if key in MEM_KEYS:
            out[key] = int(rest.split()[0]) * 1024
    return out


def parse_psi(text: str) -> dict[str, list[float]]:
    """A /proc/pressure file: {"some": [avg10, total_us], "full": [...]}."""
    out: dict[str, list[float]] = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        fields = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
        out[parts[0]] = [float(fields.get("avg10", 0)), int(fields.get("total", 0))]
    return out


def parse_net_dev(text: str) -> dict[str, list[int]]:
    """/proc/net/dev → {iface: [rx_bytes, rx_packets, rx_errs, rx_drop,
    tx_bytes, tx_packets, tx_errs, tx_drop]}, without lo and tunnel stubs."""
    out: dict[str, list[int]] = {}
    for line in text.splitlines()[2:]:
        name, _, rest = line.partition(":")
        name = name.strip()
        if not name or name in SKIP_IFACES:
            continue
        v = [int(x) for x in rest.split()]
        if len(v) >= 12:
            out[name] = [v[0], v[1], v[2], v[3], v[8], v[9], v[10], v[11]]
    return out


def parse_flat_keyed(text: str) -> dict[str, int]:
    """cgroup ``key value`` files (cpu.stat, memory.stat, memory.events)."""
    out: dict[str, int] = {}
    for line in text.splitlines():
        key, _, value = line.partition(" ")
        if value:
            try:
                out[key] = int(value)
            except ValueError:
                pass
    return out


def parse_proc_stat(text: str) -> tuple[str, int, int]:
    """/proc/<pid>/stat → (comm, utime + stime ticks, rss pages)."""
    lp, rp = text.find("("), text.rfind(")")
    comm = text[lp + 1 : rp]
    rest = text[rp + 2 :].split()
    # rest[0] is field 3 (state): utime = field 14, stime = 15, rss = 24.
    return comm, int(rest[11]) + int(rest[12]), int(rest[21])


def container_dirs(root: str) -> dict[str, str]:
    """Docker container cgroups under ``root``: {full id: path}. Covers the
    cgroupfs driver (``docker/<id>``, Docker Desktop) and systemd
    (``system.slice/docker-<id>.scope``)."""
    out: dict[str, str] = {}
    base = os.path.join(root, "docker")
    try:
        for name in os.listdir(base):
            if _ID.match(name):
                out[name] = os.path.join(base, name)
    except OSError:
        pass
    base = os.path.join(root, "system.slice")
    try:
        for name in os.listdir(base):
            m = _SCOPE.match(name)
            if m:
                out[m.group(1)] = os.path.join(base, name)
    except OSError:
        pass
    return out


# ── reading ───────────────────────────────────────────────────────────


def _read(path: str) -> str | None:
    try:
        with open(path) as fh:
            return fh.read()
    except OSError:
        return None


def _int(text: str | None) -> int | None:
    if text is None:
        return None
    text = text.strip()
    if not text or text == "max":
        return None
    try:
        return int(text)
    except ValueError:
        return None


def read_host(proc: str) -> dict:
    host: dict = {
        "cpu": parse_cpu(_read(f"{proc}/stat") or ""),
        "mem": parse_meminfo(_read(f"{proc}/meminfo") or ""),
        "load": [float(x) for x in (_read(f"{proc}/loadavg") or "0 0 0").split()[:3]],
        "psi": {},
    }
    for res in ("cpu", "memory", "io"):
        text = _read(f"{proc}/pressure/{res}")
        if text:
            host["psi"][res] = parse_psi(text)
    return host


def read_infra(proc: str) -> tuple[dict[str, list[int]], int]:
    """Per-name [count, rss_bytes, cpu_ticks] of Docker's own processes, and
    how many processes the host runs."""
    page = os.sysconf("SC_PAGE_SIZE")
    out: dict[str, list[int]] = {}
    procs = 0
    try:
        names = os.listdir(proc)
    except OSError:
        return out, 0
    for name in names:
        if not name.isdigit():
            continue
        procs += 1
        text = _read(f"{proc}/{name}/stat")
        if not text:
            continue
        try:
            comm, ticks, rss = parse_proc_stat(text)
        except (ValueError, IndexError):
            continue
        key = INFRA.get(comm)
        if key is None:
            continue
        acc = out.setdefault(key, [0, 0, 0])
        acc[0] += 1
        acc[1] += rss * page
        acc[2] += ticks
    return out, procs


def read_container(path: str, proc: str) -> list:
    cpu = parse_flat_keyed(_read(f"{path}/cpu.stat") or "")
    mstat = parse_flat_keyed(_read(f"{path}/memory.stat") or "")
    events = parse_flat_keyed(_read(f"{path}/memory.events") or "")
    ifaces: dict[str, list[int]] = {}
    procs = _read(f"{path}/cgroup.procs")
    if procs:
        first = procs.split("\n", 1)[0].strip()
        if first:
            ifaces = parse_net_dev(_read(f"{proc}/{first}/net/dev") or "")
    return [
        cpu.get("usage_usec", 0),
        _int(_read(f"{path}/memory.current")) or 0,
        mstat.get("inactive_file"),
        _int(_read(f"{path}/memory.max")),
        _int(_read(f"{path}/pids.current")),
        events.get("oom_kill"),
        ifaces,
    ]


def sweep(root: str, proc: str, *, infra: bool = True) -> dict:
    started = time.monotonic()
    line: dict = {
        "v": 1,
        "t": round(time.time(), 3),
        "ncpu": os.cpu_count(),
        "clk_tck": os.sysconf("SC_CLK_TCK"),
        "page": os.sysconf("SC_PAGE_SIZE"),
        "host": read_host(proc),
        "infra": {},
        "c": {},
    }
    for cid, path in container_dirs(root).items():
        line["c"][cid[:12]] = read_container(path, proc)
    if infra:
        line["infra"], line["host"]["procs"] = read_infra(proc)
    line["sweep_ms"] = round((time.monotonic() - started) * 1000, 1)
    return line


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--root", default="/host/cgroup", help="the host's cgroup v2 tree")
    ap.add_argument("--proc", default="/proc")
    args = ap.parse_args(argv)
    stop = False

    def _stop(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    if not os.path.isdir(args.root):
        print(json.dumps({"error": f"no cgroup tree at {args.root}"}), flush=True)
        return 2
    interval = max(args.interval, 0.1)
    next_at = time.monotonic()
    while not stop:
        line = sweep(args.root, args.proc)
        sys.stdout.write(json.dumps(line, separators=(",", ":")) + "\n")
        sys.stdout.flush()
        # Fixed rate: a slow sweep eats into the wait, never shifts the schedule;
        # sweeps that fall behind are skipped rather than bunched up.
        next_at += interval
        now = time.monotonic()
        if next_at < now:
            next_at = now + interval - ((now - next_at) % interval)
        while not stop and time.monotonic() < next_at:
            time.sleep(min(0.2, max(0.0, next_at - time.monotonic())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
