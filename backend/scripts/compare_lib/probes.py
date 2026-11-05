"""The probes, run the same way on both platforms: containers of the tools image
next to the lab's nodes, started through a ``Target`` (the local Docker, or the
GNS3 VM's over SSH), with the same flags AE3GIS gives its own helpers.

- **monitor** (``ae3gis-collect``): one JSON line per sweep (VM CPU, memory,
  stalls and disk; every container's cgroup CPU and memory; the platform's own
  processes). Host PID and cgroup namespaces, the cgroup tree read-only.
- **traffic driver** (``ae3gis-netns``): pings and iperf3 inside nodes' network
  namespaces. Host PID namespace, ``CAP_SYS_ADMIN`` + ``CAP_SYS_PTRACE``, its
  spec on stdin.

Probe containers are named, so stopping one removes it even when the runner
only holds an SSH client to it.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from typing import Any

from .target import Target

MONITOR = "ae3gis-compare-monitor"
DRIVER = "ae3gis-compare-driver"


class Monitor:
    def __init__(self, target: Target, image: str, interval: float = 2.0) -> None:
        self.target, self.image, self.interval = target, image, interval
        self.lines: list[dict[str, Any]] = []  # each sweep, with "rt": runner time
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.target.run(self.target.docker("rm", "-f", MONITOR), timeout=60)
        cmd = self.target.docker(
            "run", "--rm", "-i", "--name", MONITOR, "--network", "none",
            "--pid", "host", "--cgroupns", "host",
            "-v", "/sys/fs/cgroup:/host/cgroup:ro",
            self.image, "ae3gis-collect", "--interval", str(self.interval),
        )
        self._proc = self.target.popen(cmd)
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    def _read(self) -> None:
        assert self._proc and self._proc.stdout
        for raw in self._proc.stdout:
            try:
                line = json.loads(raw)
            except ValueError:
                continue
            line["rt"] = time.time()
            self.lines.append(line)

    def wait_first(self, timeout: float = 60) -> None:
        deadline = time.monotonic() + timeout
        while not self.lines:
            if time.monotonic() > deadline:
                err = self._proc.stderr.read(2000).decode(errors="replace") if self._proc else ""
                raise RuntimeError(f"the monitor sent nothing in {timeout:.0f}s: {err}")
            time.sleep(0.2)

    def stop(self) -> None:
        self.target.run(self.target.docker("rm", "-f", MONITOR), timeout=60)
        if self._proc:
            try:
                self._proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self._proc.kill()

    def window(self, t0: float, t1: float) -> list[dict[str, Any]]:
        return [x for x in self.lines if t0 <= x["rt"] <= t1]


def driver(
    target: Target, image: str, spec: dict[str, Any], *, security_opt: list[str] | None = None,
    timeout: float = 900,
) -> list[dict[str, Any]]:
    """Run the traffic driver to completion; its events, one per line."""
    target.run(target.docker("rm", "-f", DRIVER), timeout=60)
    cmd = target.docker(
        "run", "--rm", "-i", "--name", DRIVER, "--network", "none", "--pid", "host",
        "--cap-add", "SYS_ADMIN", "--cap-add", "SYS_PTRACE",
        "--ulimit", "nofile=65536:65536",
        *[x for opt in security_opt or [] for x in ("--security-opt", opt)],
        image, "sh", "-c", "cat > /tmp/spec.json && exec ae3gis-netns --spec /tmp/spec.json",
    )
    p = target.run(cmd, input=json.dumps(spec).encode(), timeout=timeout)
    events = []
    for raw in p.stdout.splitlines():
        try:
            events.append(json.loads(raw))
        except ValueError:
            continue
    if p.returncode != 0 and not events:
        raise RuntimeError(f"driver failed ({p.returncode}): {p.stderr.decode(errors='replace')[-600:]}")
    return events


def readiness(
    target: Target, image: str, lab_readiness: list[dict[str, Any]], pids: dict[str, int], *,
    timeout_s: float = 300, security_opt: list[str] | None = None,
) -> dict[str, Any]:
    """Every host pings its targets until they answer (the same check AE3GIS's
    benchmarks use); ``{ok, failed, elapsed, missing}``."""
    probes = [
        {"node": r["node"], "pid": pids[r["node"]], "target": r["target"]}
        for r in lab_readiness
        if r["node"] in pids
    ]
    missing = sorted({r["node"] for r in lab_readiness if r["node"] not in pids})
    spec = {"mode": "probe", "timeout_s": timeout_s, "parallel": 64, "interval_s": 1, "probes": probes}
    t0 = time.monotonic()
    events = driver(target, image, spec, security_opt=security_opt, timeout=timeout_s + 120)
    done = next((e for e in events if e.get("k") == "done"), {})
    errors = [e for e in events if e.get("k") == "error"]
    return {
        "ok": done.get("ok", 0),
        "failed": done.get("failed", len(probes)),
        "elapsed": done.get("elapsed", round(time.monotonic() - t0, 3)),
        "missing": missing,
        "error": errors[0].get("message") if errors else None,
    }
