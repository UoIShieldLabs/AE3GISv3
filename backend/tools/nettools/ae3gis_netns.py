#!/usr/bin/env python3
"""AE3GIS netns driver: run processes inside node network namespaces.

One helper container (host PID namespace, CAP_SYS_ADMIN for ``setns``,
CAP_SYS_PTRACE to open namespaces of nodes holding capabilities it lacks) drives a whole
traffic run: each process is started with ``setns`` into the network
namespace of a node's process, so it sends from the node's addresses and
routes whatever image the node runs, without a container per flow. The tool
binaries come from this image. Processes' CPU is charged to this container.

This process is the only writer to stdout, so events never interleave. The
spec is a JSON file (``--spec``):

``run``::

    {"mode": "run", "ramp_s": 0, "ready_timeout_s": 10, "grace_s": 10,
     "procs": [{"id": "f1.server", "pid": 1234, "role": "server", "port": 5201,
                "argv": ["iperf3", "-s", ...]},
               {"id": "f1.client", "pid": 5678, "role": "client", "retries": 3,
                "argv": ["iperf3", "-c", ...]}]}

Servers start first; they are ready when their port shows up as LISTEN in
``/proc/<pid>/net/tcp`` or ``tcp6`` (dual-stack listeners only appear in the
latter). Clients then start, spread over ``ramp_s``; a client that fails
within its first seconds is restarted up to ``retries`` times. SIGINT/SIGTERM:
clients get SIGINT (iperf3 then prints its end), servers follow, stragglers are
killed after ``grace_s``.

``probe``: ping each ``target`` from each node until it answers or
``timeout_s`` passes (the "network ready" check)::

    {"mode": "probe", "timeout_s": 300, "parallel": 64, "interval_s": 1,
     "probes": [{"node": "h1", "pid": 1234, "target": "10.0.1.1"}]}

Events (one JSON object per line): ``started`` {p, t, attempt}, ``out`` / ``err``
{p, line}, ``exit`` {p, code, t}, ``retry`` {p, attempt}, ``listening`` {p},
``servers_ready`` {n, failed}, ``probe`` {node, target, ok, t, attempts},
``error`` {code, message}, ``done`` {...}.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import signal
import sys
import time

PROC = "/proc"
RETRY_WINDOW_S = 10.0
LINE_LIMIT = 1 << 20


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def listening_ports(tcp_text: str) -> set[int]:
    """Local ports in LISTEN state (st 0A) in a /proc/net/tcp{,6} table."""
    ports: set[int] = set()
    for line in tcp_text.splitlines()[1:]:
        parts = line.split()
        if len(parts) > 3 and parts[3] == "0A":
            ports.add(int(parts[1].rsplit(":", 1)[1], 16))
    return ports


def is_listening(pid: int, port: int, proc: str = PROC) -> bool:
    for table in ("tcp", "tcp6"):
        try:
            with open(f"{proc}/{pid}/net/{table}") as fh:
                if port in listening_ports(fh.read()):
                    return True
        except OSError:
            pass
    return False


async def spawn_in(pid: int, argv: list[str], **kwargs) -> asyncio.subprocess.Process:
    """Start ``argv`` in the network namespace of ``pid``."""
    fd = os.open(f"{PROC}/{pid}/ns/net", os.O_RDONLY)
    try:
        return await asyncio.create_subprocess_exec(
            *argv,
            preexec_fn=lambda: os.setns(fd, os.CLONE_NEWNET),
            start_new_session=True,
            **kwargs,
        )
    finally:
        os.close(fd)


class Proc:
    def __init__(self, spec: dict) -> None:
        self.id: str = spec["id"]
        self.pid: int = int(spec["pid"])
        self.argv: list[str] = list(spec["argv"])
        self.role: str = spec.get("role", "client")
        self.port: int | None = spec.get("port")
        self.retries: int = int(spec.get("retries", 0))
        self.process: asyncio.subprocess.Process | None = None
        self.attempt = 0
        self.code: int | None = None
        self.finished = asyncio.Event()

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    def signal(self, sig: int) -> None:
        if self.running:
            with contextlib.suppress(ProcessLookupError):
                self.process.send_signal(sig)


async def _pipe(proc: Proc, stream: asyncio.StreamReader, kind: str) -> None:
    while True:
        try:
            line = await stream.readline()
        except ValueError:  # a line over LINE_LIMIT: skip it
            continue
        if not line:
            return
        emit({"k": kind, "p": proc.id, "line": line.decode("utf-8", "replace").rstrip("\n")})


async def supervise(proc: Proc, stop: asyncio.Event) -> None:
    """Run ``proc`` to completion, restarting an early failure if allowed."""
    while True:
        proc.attempt += 1
        started = time.monotonic()
        try:
            proc.process = await spawn_in(
                proc.pid,
                proc.argv,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=LINE_LIMIT,
            )
        except Exception as exc:  # the node is gone, or setns refused
            emit({"k": "err", "p": proc.id, "line": f"cannot start: {exc}"})
            proc.code = -2
            emit({"k": "exit", "p": proc.id, "code": proc.code, "t": round(time.time(), 3)})
            proc.finished.set()
            return
        emit({"k": "started", "p": proc.id, "t": round(time.time(), 3), "attempt": proc.attempt})
        await asyncio.gather(
            _pipe(proc, proc.process.stdout, "out"), _pipe(proc, proc.process.stderr, "err")
        )
        code = await proc.process.wait()
        early = time.monotonic() - started < RETRY_WINDOW_S
        if code != 0 and early and proc.attempt <= proc.retries and not stop.is_set():
            emit({"k": "retry", "p": proc.id, "attempt": proc.attempt + 1})
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=1.0)
            if not stop.is_set():
                continue
        proc.code = code
        emit({"k": "exit", "p": proc.id, "code": code, "t": round(time.time(), 3)})
        proc.finished.set()
        return


async def _wait(procs: list[Proc], timeout: float) -> list[Proc]:
    """Wait for ``procs`` to finish; return those still running after ``timeout``."""
    pending = [p for p in procs if not p.finished.is_set()]
    if pending:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(
                asyncio.gather(*(p.finished.wait() for p in pending)), timeout=timeout
            )
    return [p for p in procs if not p.finished.is_set()]


async def self_test(pid: int) -> str | None:
    """Why this container cannot enter node namespaces, or None if it can."""
    try:
        p = await spawn_in(pid, ["true"])
        await p.wait()
        return None if p.returncode == 0 else f"exit {p.returncode}"
    except Exception as exc:  # PermissionError surfaces as SubprocessError
        return f"{type(exc).__name__}: {exc}"


async def run(spec: dict, stop: asyncio.Event) -> int:
    procs = [Proc(p) for p in spec.get("procs", [])]
    servers = [p for p in procs if p.role == "server"]
    clients = [p for p in procs if p.role != "server"]
    grace = float(spec.get("grace_s", 10))
    if procs:
        problem = await self_test(procs[0].pid)
        if problem:
            emit(
                {
                    "k": "error",
                    "code": "setns",
                    "message": "Cannot enter node network namespaces "
                    f"({problem}); the driver needs the host PID namespace, "
                    "CAP_SYS_ADMIN and CAP_SYS_PTRACE, and on AppArmor/SELinux "
                    "hosts a security_opt (AE3GIS_DRIVER_SECURITY_OPT)",
                }
            )
            return 3
    tasks = [asyncio.ensure_future(supervise(p, stop)) for p in servers]

    # Servers first, each ready once its port is listening.
    deadline = time.monotonic() + float(spec.get("ready_timeout_s", 10))
    waiting = [p for p in servers if p.port]
    while waiting and not stop.is_set() and time.monotonic() < deadline:
        for p in list(waiting):
            if p.finished.is_set():
                waiting.remove(p)
            elif is_listening(p.pid, p.port):
                emit({"k": "listening", "p": p.id})
                waiting.remove(p)
        if waiting:
            await asyncio.sleep(0.1)
    failed = [p.id for p in servers if p.port and (p.finished.is_set() or p in waiting)]
    emit({"k": "servers_ready", "n": len(servers) - len(failed), "failed": failed})

    # Then clients, spread over the ramp.
    ramp = float(spec.get("ramp_s", 0))
    started: list[Proc] = []
    for i, p in enumerate(clients):
        if stop.is_set():
            break
        if ramp and i:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=ramp / len(clients))
            if stop.is_set():
                break
        tasks.append(asyncio.ensure_future(supervise(p, stop)))
        started.append(p)

    # Until every client is done, or a stop.
    stopper = asyncio.ensure_future(stop.wait())
    everyone = asyncio.ensure_future(asyncio.gather(*(p.finished.wait() for p in started)))
    await asyncio.wait({stopper, everyone}, return_when=asyncio.FIRST_COMPLETED)
    for f in (stopper, everyone):
        f.cancel()

    # Wind down: clients first (SIGINT makes iperf3 print its end), then servers.
    for p in started:
        p.signal(signal.SIGINT)
    for p in await _wait(started, grace):
        p.signal(signal.SIGKILL)
    left = await _wait(servers, grace if not stop.is_set() else 3.0)
    for p in left:
        p.signal(signal.SIGINT)
    for p in await _wait(left, 3.0):
        p.signal(signal.SIGKILL)
    await _wait(procs, 5.0)
    for t in tasks:
        if not t.done():
            t.cancel()
    emit(
        {
            "k": "done",
            "exited": {p.id: p.code for p in procs if p.code is not None},
            "never_started": [p.id for p in clients if p not in started],
        }
    )
    return 0


async def probe(spec: dict, stop: asyncio.Event) -> int:
    probes = spec.get("probes", [])
    timeout = float(spec.get("timeout_s", 300))
    interval = float(spec.get("interval_s", 1))
    sem = asyncio.Semaphore(int(spec.get("parallel", 64)))
    t0 = time.monotonic()

    async def ping(pid: int, target: str) -> bool:
        async with sem:
            try:
                p = await spawn_in(
                    pid,
                    ["ping", "-c", "1", "-W", "1", target],
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                return await p.wait() == 0
            except Exception:
                return False

    async def one(pr: dict) -> bool:
        attempts = 0
        while True:
            attempts += 1
            ok = await ping(int(pr["pid"]), pr["target"])
            elapsed = round(time.monotonic() - t0, 3)
            if ok or stop.is_set() or elapsed >= timeout:
                emit(
                    {
                        "k": "probe",
                        "node": pr["node"],
                        "target": pr["target"],
                        "ok": ok,
                        "t": elapsed,
                        "attempts": attempts,
                    }
                )
                return ok
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=interval)

    results = await asyncio.gather(*(one(p) for p in probes))
    emit(
        {
            "k": "done",
            "ok": sum(results),
            "failed": len(results) - sum(results),
            "elapsed": round(time.monotonic() - t0, 3),
        }
    )
    return 0


async def amain(args) -> int:
    with open(args.spec) as fh:
        spec = json.load(fh)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    if spec.get("mode") == "probe":
        return await probe(spec, stop)
    return await run(spec, stop)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spec", default="/ae3gis/spec.json")
    return asyncio.run(amain(ap.parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
