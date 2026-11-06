"""The host's side of a platform: what its VM and helper processes cost the
machine itself, sampled every few seconds.

**macOS** (``HostSampler``):

- **footprint** (``top``'s MEM, Activity Monitor's "Memory"): resident plus
  compressed memory. Both VMs keep memory the host gave them after the guest
  frees it, so it is the host's real cost, a high-water mark since the VM
  started; compare it against the reference after each restart.
- **RSS** and **CPU time** (``ps``), CPU as cores from the time's growth.
- the host's own CPU and memory (``top``'s header lines).

One ``top -l 0`` runs for the whole window (its first sample costs ~0.9 s of
CPU, later ones ~0.1 s); ``ps`` is ~20 ms. Neither needs root, so both VMs
(``vmware-vmx`` runs as root) are read the same way.

**Windows** (``PsutilSampler``, also Linux): ``psutil`` per process. The
footprint is the working set (Task Manager's "Memory" for ``vmmem`` /
``vmmemWSL``), and private bytes are kept beside it; ``compare.py memcheck``
shows which one follows the VM on a machine before a run. A process psutil
may not read (``vmmem`` without an Administrator terminal) is listed in the
sample's ``denied``.
"""

from __future__ import annotations

import re
import subprocess
import sys
import threading
import time
from typing import Any

_UNIT = {"B": 1, "K": 2**10, "M": 2**20, "G": 2**30, "T": 2**40}
_SIZE = re.compile(r"^([\d.]+)([BKMGT])[+-]?$")


def size(text: str) -> int | None:
    m = _SIZE.match(text.strip())
    return int(float(m.group(1)) * _UNIT[m.group(2)]) if m else None


def cputime(text: str) -> float:
    """``ps`` TIME (``[[dd-]hh:]mm:ss.cc``) in seconds."""
    days, _, rest = text.strip().rpartition("-")
    parts = [float(x) for x in rest.split(":")]
    secs = 0.0
    for p in parts:
        secs = secs * 60 + p
    return secs + (int(days) * 86400 if days else 0)


def parse_cpu_line(line: str) -> dict[str, float]:
    """``CPU usage: 9.72% user, 14.3% sys, 76.23% idle``."""
    return {k: float(v) for v, k in re.findall(r"([\d.]+)% (\w+)", line)}


def parse_physmem(line: str) -> dict[str, int]:
    """``PhysMem: 31G used (2836M wired, 9573M compressor), 182M unused.``"""
    out = {}
    for v, k in re.findall(r"([\d.]+[BKMGT]) (\w+)", line):
        b = size(v)
        if b is not None:
            out[k] = b
    return out


class HostSampler:
    def __init__(self, groups: dict[str, list[int]], interval: float = 2.0) -> None:
        self.groups = {g: list(p) for g, p in groups.items()}
        self.interval = interval
        self.samples: list[dict[str, Any]] = []
        self._top: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._prev: dict[int, tuple[float, float]] = {}

    @property
    def pids(self) -> list[int]:
        return sorted({p for ps in self.groups.values() for p in ps})

    def start(self) -> None:
        argv = ["top", "-l", "0", "-s", str(max(1, round(self.interval))), "-stats", "pid,mem"]
        for p in self.pids:
            argv += ["-pid", str(p)]
        self._top = subprocess.Popen(argv, stdout=subprocess.PIPE, text=True, bufsize=1)
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._top:
            self._top.terminate()
            try:
                self._top.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._top.kill()
        if self._thread:
            self._thread.join(timeout=5)

    def _ps(self) -> dict[int, tuple[int, float]]:
        if not self.pids:
            return {}
        out = subprocess.run(
            ["ps", "-o", "pid=,rss=,time=", "-p", ",".join(map(str, self.pids))],
            capture_output=True,
            text=True,
        ).stdout
        got = {}
        for line in out.splitlines():
            parts = line.split()
            if len(parts) == 3:
                got[int(parts[0])] = (int(parts[1]) * 1024, cputime(parts[2]))
        return got

    def _read(self) -> None:
        assert self._top and self._top.stdout
        block: dict[str, Any] = {}
        footprint: dict[int, int] = {}
        for line in self._top.stdout:
            if line.startswith("Processes:"):
                if block:
                    self._emit(block, footprint)
                block, footprint = {"rt": time.time()}, {}
            elif line.startswith("CPU usage:"):
                block["cpu"] = parse_cpu_line(line)
            elif line.startswith("PhysMem:"):
                block["physmem"] = parse_physmem(line)
            else:
                parts = line.split()
                if len(parts) == 2 and parts[0].isdigit():
                    b = size(parts[1])
                    if b is not None:
                        footprint[int(parts[0])] = b
        if block:
            self._emit(block, footprint)

    def _emit(self, block: dict[str, Any], footprint: dict[int, int]) -> None:
        now = time.time()
        ps = self._ps()
        groups = {}
        for g, pids in self.groups.items():
            fp = sum(footprint.get(p, 0) for p in pids)
            rss = sum(ps[p][0] for p in pids if p in ps)
            # Cores over the interval since the last sample; None on the first.
            cores: float | None = None
            for p in pids:
                if p in ps and p in self._prev:
                    t_prev, cpu_prev = self._prev[p]
                    if now > t_prev:
                        cores = (cores or 0.0) + max(0.0, ps[p][1] - cpu_prev) / (now - t_prev)
            groups[g] = {
                "footprint": fp,
                "rss": rss,
                "cores": None if cores is None else round(cores, 4),
            }
        for p, (_, cpu) in ps.items():
            self._prev[p] = (now, cpu)
        self.samples.append({**block, "g": groups})

    def window(self, t0: float, t1: float) -> list[dict[str, Any]]:
        return [s for s in self.samples if t0 <= s["rt"] <= t1]


class PsutilSampler:
    """The same samples as ``HostSampler``, from ``psutil`` (Windows, Linux)."""

    def __init__(self, groups: dict[str, list[int]], interval: float = 2.0) -> None:
        import psutil

        self.psutil = psutil
        self.groups = {g: list(p) for g, p in groups.items()}
        self.interval = interval
        self.samples: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._prev: dict[int, tuple[float, float]] = {}
        self._procs: dict[int, Any] = {}

    def start(self) -> None:
        self.psutil.cpu_times_percent(interval=None)  # primes the host's CPU deltas
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            self.samples.append(self.sample())

    def _read(self, pid: int) -> tuple[int, int | None, float] | None:
        """(working set, private bytes, CPU seconds), None when unreadable."""
        ps = self.psutil
        try:
            proc = self._procs.get(pid) or self._procs.setdefault(pid, ps.Process(pid))
            with proc.oneshot():
                mi = proc.memory_info()
                ct = proc.cpu_times()
            return mi.rss, getattr(mi, "private", None), ct.user + ct.system
        except (ps.NoSuchProcess, ps.AccessDenied, ps.ZombieProcess, OSError):
            return None

    def sample(self) -> dict[str, Any]:
        now = time.time()
        ps = self.psutil
        cpu = ps.cpu_times_percent(interval=None)
        vm = ps.virtual_memory()
        got = {p: self._read(p) for ps_ in self.groups.values() for p in ps_}
        groups, denied = {}, sorted(p for p, v in got.items() if v is None)
        for g, pids in self.groups.items():
            vals = [got[p] for p in pids if got.get(p)]
            cores: float | None = None
            for p in pids:
                v = got.get(p)
                if v and p in self._prev and now > self._prev[p][0]:
                    t_prev, cpu_prev = self._prev[p]
                    cores = (cores or 0.0) + max(0.0, v[2] - cpu_prev) / (now - t_prev)
            groups[g] = {
                "footprint": sum(v[0] for v in vals),
                "rss": sum(v[0] for v in vals),
                "private": sum(v[1] or 0 for v in vals),
                "cores": None if cores is None else round(cores, 4),
            }
        for p, v in got.items():
            if v:
                self._prev[p] = (now, v[2])
        return {
            "rt": now,
            "cpu": {"user": cpu.user, "sys": cpu.system, "idle": cpu.idle},
            "physmem": {"used": vm.total - vm.available, "unused": vm.available},
            "g": groups,
            **({"denied": denied} if denied else {}),
        }

    def window(self, t0: float, t1: float) -> list[dict[str, Any]]:
        return [s for s in self.samples if t0 <= s["rt"] <= t1]


def sampler(groups: dict[str, list[int]], interval: float = 2.0):
    """This host's sampler: ``top`` on macOS, ``psutil`` elsewhere."""
    if sys.platform == "darwin":
        return HostSampler(groups, interval)
    return PsutilSampler(groups, interval)
