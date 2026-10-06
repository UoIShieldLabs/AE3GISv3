"""The fake engine's helper containers: a collector and a netns driver.

They print what the real helpers (``tools/nettools/ae3gis_collect.py`` and
``ae3gis_netns.py``) print, driven by the fake engine's labs instead of a
kernel, so the monitor, traffic and benchmark services run unchanged on
``AE3GIS_ENGINE=fake``.

The collector's host memory falls by ``FakeEngine.fake_mem_per_node`` for
every running node (plus a fixed base), so marginal-memory math has a known
answer; nodes in ``oom_nodes`` report a new OOM kill every sweep.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import time
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from engine import fake_tools as tools
from engine.base import HelperSpec

if TYPE_CHECKING:
    from engine.fake import FakeEngine

GiB = 1024**3


def fake_container_id(key: str) -> str:
    """A stable 64-hex container id for a fake node/sidecar/helper."""
    return hashlib.sha256(key.encode()).hexdigest()


def arg(argv: list[str], flag: str, default: str | None = None) -> str | None:
    return (
        argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else default
    )


class FakeHelper:
    """A helper whose output is produced by a task instead of a container."""

    def __init__(self, engine: FakeEngine, spec: HelperSpec) -> None:
        self.engine = engine
        self.spec = spec
        self.node_id = ""
        self.name = f"ae3gis-{spec.purpose}-{spec.job_id[:8]}-{uuid.uuid4().hex[:4]}"
        self.id = fake_container_id(self.name)
        self.status = "running"
        self.signalled = asyncio.Event()
        self._out: asyncio.Queue[tuple[str, bytes] | int] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self.exit_code: int | None = None

    def emit(self, stream: str, data: bytes) -> None:
        self._out.put_nowait((stream, data))

    def line(self, obj: dict[str, Any]) -> None:
        self.emit("stdout", (json.dumps(obj, separators=(",", ":")) + "\n").encode())

    def exit(self, code: int) -> None:
        if self.exit_code is None:
            self.exit_code = code
            self.status = "exited"
            self._out.put_nowait(code)

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._guarded())

    async def _guarded(self) -> None:
        try:
            fail = self.engine.fail_helper.get(self.spec.purpose)
            if fail:
                self.emit("stderr", (fail + "\n").encode())
                self.exit(1)
                return
            await self.run()
        except asyncio.CancelledError:
            self.exit(-1)

    async def run(self) -> None:
        await self.signalled.wait()
        self.exit(0)

    async def sleep(self, seconds: float) -> bool:
        """Sleep unless signalled first; True if signalled."""
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self.signalled.wait(), timeout=max(seconds, 0.001))
        return self.signalled.is_set()

    # Sidecar protocol
    async def pump(
        self, on_stdout: Callable[[bytes], None], on_stderr: Callable[[bytes], None]
    ) -> int:
        try:
            while True:
                item = await self._out.get()
                if isinstance(item, int):
                    return item
                stream, data = item
                (on_stdout if stream == "stdout" else on_stderr)(data)
        except asyncio.CancelledError:
            await self.remove()
            raise

    async def signal(self, sig: str = "SIGINT") -> None:
        self.signalled.set()

    async def exec(self, cmd: list[str], timeout: float = 5.0) -> tuple[int, str]:
        if "--version" in " ".join(cmd):
            return 0, "iperf 3.19.1 (fake)\n"
        return 0, ""

    async def remove(self) -> None:
        self.engine.helpers.pop(self.name, None)
        self.engine.calls.append(("remove_helper", self.name))
        self.signalled.set()
        if self._task and not self._task.done():
            self._task.cancel()
        self.exit(-1)


class FakeCollector(FakeHelper):
    """Prints ``ae3gis-collect`` sweeps for every fake container."""

    NCPU = 8
    CLK_TCK = 100

    def __init__(self, engine: FakeEngine, spec: HelperSpec) -> None:
        super().__init__(engine, spec)
        self.cpu = [0] * 8
        self.psi_total = 0
        self.oom: dict[str, int] = {}  # node -> OOM kills so far (grows while in oom_nodes)
        self.last = time.monotonic()

    async def run(self) -> None:
        interval = self.engine.monitor_interval or float(arg(self.spec.command, "--interval", "1"))
        while True:
            self.line(self.sweep())
            if await self.sleep(interval):
                break
        self.exit(0)

    def _oom(self, nid: str) -> int:
        """Like memory.events: a node in ``oom_nodes`` loses a process every sweep."""
        if nid in self.engine.oom_nodes:
            self.oom[nid] = self.oom.get(nid, 0) + 1
        return self.oom.get(nid, 0)

    def sweep(self) -> dict[str, Any]:
        eng = self.engine
        now = time.monotonic()
        dt = max(now - self.last, 1e-3)
        self.last = now
        nodes = [
            (lab, nid, i) for lab in eng.labs.values() for i, nid in enumerate(sorted(lab.running))
        ]
        tools = list(eng.sidecars.values()) + list(eng.helpers.values())
        busy = min(0.05 + 0.002 * len(nodes), 0.95)
        ticks = dt * self.NCPU * self.CLK_TCK
        self.cpu[0] += int(ticks * busy * 0.7)
        self.cpu[2] += int(ticks * busy * 0.3)
        self.cpu[3] += int(ticks * (1 - busy))
        self.psi_total += int(dt * 1e6 * busy * 0.01)
        used = 1 * GiB + eng.fake_mem_per_node * len(nodes) + 5_000_000 * len(tools)
        total = 8 * GiB
        links = sum(len(lab.plan.collision_domains) if lab.plan else 0 for lab in eng.labs.values())
        containers: dict[str, list[Any]] = {}
        for lab, nid, i in nodes:
            age = now - lab.started
            ifaces = {
                iface.name: [int(age * 1000 * (1 + i % 4))] * 2
                + [0, 0]
                + [int(age * 1000 * (1 + i % 4))] * 2
                + [0, 0]
                for n in (lab.plan.nodes if lab.plan else [])
                if n.id == nid
                for iface in n.interfaces
            }
            for counters in ifaces.values():  # packets: bytes / 1000
                counters[1] = counters[0] // 1000
                counters[5] = counters[4] // 1000
            containers[eng.node_container_id(lab.state.lab_hash, nid)[:12]] = [
                int(age * 1e6 * 0.01 * (1 + i % 5)),
                1_500_000 + (i % 3) * 100_000,
                0,
                None,
                1,
                self._oom(nid),
                ifaces,
            ]
        for tool in tools:
            containers[tool.id[:12]] = [int(now * 1e4) % 10**9, 5_000_000, 0, None, 2, 0, {}]
        n_containers = len(nodes) + len(tools)
        return {
            "v": 1,
            "t": round(time.time(), 3),
            "sweep_ms": round(0.5 + 0.01 * n_containers, 1),
            "ncpu": self.NCPU,
            "clk_tck": self.CLK_TCK,
            "page": 4096,
            "host": {
                "cpu": list(self.cpu),
                "mem": {"MemTotal": total, "MemFree": total - used, "MemAvailable": total - used},
                "load": [round(len(nodes) / 100, 2)] * 3,
                "disk": [
                    60 * GiB,
                    60 * GiB - 20 * GiB - eng.fake_disk_per_node * len(nodes),
                ],
                "psi": {
                    "cpu": {"some": [round(busy, 2), self.psi_total], "full": [0.0, 0]},
                    "memory": {"some": [0.0, 0], "full": [0.0, 0]},
                    "io": {"some": [0.0, 0], "full": [0.0, 0]},
                },
                "procs": 150 + 3 * n_containers,
            },
            "infra": {
                "dockerd": [1, 150_000_000 + 1_000_000 * n_containers, int(now * 10)],
                "containerd": [1, 80_000_000, int(now * 5)],
                "containerd-shim": [n_containers, 15_000_000 * n_containers, n_containers],
                "vde_switch": [links, 600_000 * links, links],
            },
            "c": containers,
        }


class FakeDriver(FakeHelper):
    """Prints ``ae3gis-netns`` events. ``run``: servers listen (unless their node
    is in ``fail_listen``), then each client drives its server with iperf3-like
    output every ``traffic_interval`` seconds until its duration ends or the
    driver is signalled. Client and server procs pair up by id
    (``<flow>.c`` / ``<flow>.s``). ``probe``: every target answers unless the
    probing node is in ``unreachable``."""

    def __init__(self, engine: FakeEngine, spec: HelperSpec) -> None:
        super().__init__(engine, spec)
        self.spec_doc = json.loads(spec.files.get("/ae3gis/spec.json", b"{}"))
        self._served: set[str] = set()  # servers a client connected to

    def out(self, proc: str, data: bytes) -> None:
        for line in data.decode().splitlines():
            self.line({"k": "out", "p": proc, "line": line})

    async def run(self) -> None:
        if self.spec_doc.get("mode") == "probe":
            await self._probe()
        else:
            await self._run()
        self.exit(0)

    async def _probe(self) -> None:
        ok = failed = 0
        for p in self.spec_doc.get("probes", []):
            node = self.engine.node_for_pid(int(p["pid"]))
            reachable = node is not None and node not in self.engine.unreachable
            ok += reachable
            failed += not reachable
            self.line(
                {
                    "k": "probe",
                    "node": p["node"],
                    "target": p["target"],
                    "ok": reachable,
                    "t": 0.01 if reachable else float(self.spec_doc.get("timeout_s", 1)),
                    "attempts": 1,
                }
            )
        self.line({"k": "done", "ok": ok, "failed": failed, "elapsed": 0.01})

    async def _run(self) -> None:
        procs = self.spec_doc.get("procs", [])
        servers = {p["id"]: p for p in procs if p.get("role") == "server"}
        clients = [p for p in procs if p.get("role") != "server"]
        failed: list[str] = []
        for s in servers.values():
            self.line({"k": "started", "p": s["id"], "t": round(time.time(), 3), "attempt": 1})
            if self.engine.node_for_pid(int(s["pid"])) in self.engine.fail_listen:
                self.out(
                    s["id"],
                    tools.iperf_error("unable to start listener for connections: Address in use"),
                )
                self.line({"k": "exit", "p": s["id"], "code": 1, "t": round(time.time(), 3)})
                failed.append(s["id"])
            else:
                self.line({"k": "listening", "p": s["id"]})
        self.line({"k": "servers_ready", "n": len(servers) - len(failed), "failed": failed})
        offered = sum(tools.IperfArgs(c["argv"]).bitrate for c in clients)
        cap = self.engine.traffic_capacity_bps
        share = min(1.0, cap / offered) if cap and offered else 1.0
        await asyncio.gather(
            *(self._client(c, servers.get(c["id"][:-2] + ".s"), failed, share) for c in clients)
        )
        for s in servers.values():
            if s["id"] not in failed and s["id"] not in self._served:
                self.line({"k": "exit", "p": s["id"], "code": 0, "t": round(time.time(), 3)})
        self.line({"k": "done", "exited": {}, "never_started": []})

    async def _client(
        self,
        c: dict[str, Any],
        server: dict[str, Any] | None,
        failed: list[str],
        share: float = 1.0,
    ) -> None:
        cid, sid = c["id"], (server or {}).get("id")
        now = lambda: round(time.time(), 3)  # noqa: E731
        self.line({"k": "started", "p": cid, "t": now(), "attempt": 1})
        args = tools.IperfArgs(c["argv"])
        args.bitrate *= share  # what the fake network lets through
        if server is None or sid in failed:
            self.out(
                cid,
                tools.iperf_error(
                    "unable to connect to server - server may have stopped running or use a "
                    "different port, firewall issue, etc.: Connection refused"
                ),
            )
            self.line({"k": "exit", "p": cid, "code": 1, "t": now()})
            return
        self._served.add(sid)
        self.out(cid, tools.iperf_start(args, client=True))
        self.out(sid, tools.iperf_start(args, client=False))
        interval = self.engine.traffic_interval
        until_stopped = args.duration == 0
        i = 0
        while until_stopped or i < args.duration:
            if await self.sleep(max(interval, 0.01 if until_stopped else 0)):
                break
            i += 1
            self.out(cid, tools.iperf_interval(args, i, client=True))
            self.out(sid, tools.iperf_interval(args, i, client=False))
        interrupted = self.signalled.is_set()
        if interrupted:
            self.out(
                cid,
                tools.iperf_error("interrupt - the client has terminated by signal Interrupt(2)"),
            )
            self.out(sid, tools.iperf_error("the client has terminated"))
        self.out(cid, tools.iperf_end(args, float(i), client=True, interrupted=interrupted))
        self.out(sid, tools.iperf_end(args, float(i), client=False, interrupted=False))
        self.line({"k": "exit", "p": cid, "code": 0, "t": now()})
        self.line({"k": "exit", "p": sid, "code": 0, "t": now()})
