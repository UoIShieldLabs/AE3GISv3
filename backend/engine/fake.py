"""In-memory DeploymentEngine for tests and for running the UI without Docker.

Select with ``AE3GIS_ENGINE=fake``. Deploys succeed instantly and every node
reports running. Test hooks:

- ``fail_deploy`` / ``fail_destroy``: raise instead of deploying/destroying.
- ``fail_after_create``: create the lab, then raise (a deploy that dies part-way).
- ``crash_nodes``: node id -> container output; those nodes exit right after start.
- ``pull_gate`` / ``build_gate``: an ``asyncio.Event`` that pulls / builds wait on.
- ``fail_build``: image ref -> error message.
- ``fail_sidecar``: sidecar purpose -> stderr text; that sidecar exits 1 at once.
- ``capture_packets``: frames every capture sidecar emits (default: pings at
  ``capture_pps``); ``traffic_interval``: seconds between iperf3 intervals.

Sidecars behave like the real tools: a capture sidecar streams a pcap and
prints tcpdump's totals when signalled; an iperf3 client drives the server
sidecar listening on its target (and fails to connect if there is none).
``calls`` records sidecar removals and lab teardown in order.

Images under ``ae3gis.local/`` (built by AE3GIS, never pulled) are absent until
built; other refs follow ``present_images``. ``build_delay`` paces the simulated
build output so the UI can show progress.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from domain.pcap import global_header, record
from domain.plan import LabPlan
from engine import fake_tools as tools
from engine.base import (
    BuildError,
    BuildSpec,
    BuildSupport,
    EngineState,
    IfaceCounters,
    ImageInfo,
    LabRef,
    NodeInterface,
    NodeLog,
    NodeRuntimeInfo,
    NodeStatus,
    Progress,
    RawStats,
    SidecarInfo,
    SidecarSpec,
    normalize_ref,
)
from engine.kathara.naming import lab_hash as hash_for_name

LOCAL_PREFIX = "ae3gis.local/"


@dataclass
class _Lab:
    state: EngineState
    running: set[str] = field(default_factory=set)
    plan: LabPlan | None = None
    started: float = field(default_factory=time.monotonic)


class FakeSidecar:
    """A sidecar whose output is produced by a task instead of a container."""

    def __init__(self, engine: FakeEngine, spec: SidecarSpec, lab: _Lab) -> None:
        self.engine = engine
        self.spec = spec
        self.lab = lab
        self.node_id = spec.node_id
        machine = lab.state.nodes.get(spec.node_id, spec.node_id)
        self.name = f"ae3gis-{spec.purpose}-{spec.job_id[:8]}-{machine}-{uuid.uuid4().hex[:4]}"
        self.status = "running"
        self.signalled = asyncio.Event()
        self._out: asyncio.Queue[tuple[str, bytes] | int] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self.exit_code: int | None = None

    # producer side
    def emit(self, stream: str, data: bytes) -> None:
        self._out.put_nowait((stream, data))

    def exit(self, code: int) -> None:
        if self.exit_code is None:
            self.exit_code = code
            self.status = "exited"
            self._out.put_nowait(code)

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._run())

    async def _run(self) -> None:
        try:
            fail = self.engine.fail_sidecar.get(self.spec.purpose)
            if fail:
                self.emit("stderr", (fail + "\n").encode())
                self.exit(1)
                return
            tool = self.spec.command[0] if self.spec.command else ""
            if tool == "tcpdump":
                await self._tcpdump()
            elif tool == "iperf3" and "-s" in self.spec.command:
                await self._iperf_server()
            elif tool == "iperf3":
                await self._iperf_client()
            else:
                await self.signalled.wait()
                self.exit(0)
        except asyncio.CancelledError:
            self.exit(-1)

    async def _tcpdump(self) -> None:
        argv = self.spec.command
        iface = argv[argv.index("-i") + 1] if "-i" in argv else "eth0"
        limit = int(argv[argv.index("-c") + 1]) if "-c" in argv else None
        self.emit("stderr", tools.tcpdump_banner(iface))
        self.emit("stdout", global_header())
        src, dst = self.engine._ping_pair(self.lab, self.node_id, iface)
        count = 0
        frames = self.engine.capture_packets
        if frames is not None:
            for frame in frames[:limit] if limit else frames:
                self.emit("stdout", record(time.time(), frame))
                count += 1
        else:
            seq = 0
            while not self.signalled.is_set() and (limit is None or count < limit):
                seq += 1
                self.emit("stdout", tools.ping_records(src, dst, seq, time.time()))
                count += 2
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        self.signalled.wait(), timeout=2 / max(self.engine.capture_pps, 0.001)
                    )
        if limit is None or count < limit:
            await self.signalled.wait()
        self.emit("stderr", tools.tcpdump_totals(count))
        self.exit(0)

    async def _iperf_server(self) -> None:
        args = tools.IperfArgs(self.spec.command)
        key = (self.lab.state.lab_hash, self.node_id, args.port)
        self.engine.iperf_servers[key] = self
        try:
            # Output comes from the client driving this server (see _iperf_client).
            await self.signalled.wait()
            self.exit(0)
        finally:
            self.engine.iperf_servers.pop(key, None)

    async def _iperf_client(self) -> None:
        args = tools.IperfArgs(self.spec.command)
        server = self.engine._iperf_server_for(self.lab, args.host, args.port)
        if server is None:
            self.emit(
                "stdout",
                tools.iperf_error(
                    "unable to connect to server - server may have stopped running or use a "
                    "different port, firewall issue, etc.: Connection refused"
                ),
            )
            self.exit(1)
            return
        self.emit("stdout", tools.iperf_start(args, client=True))
        server.emit("stdout", tools.iperf_start(args, client=False))
        i = 0
        interval = self.engine.traffic_interval
        until_stopped = args.duration == 0
        while until_stopped or i < args.duration:
            if self.signalled.is_set():
                break
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(
                    self.signalled.wait(), timeout=max(interval, 0.01 if until_stopped else 0)
                )
            if self.signalled.is_set():
                break
            i += 1
            self.emit("stdout", tools.iperf_interval(args, i, client=True))
            server.emit("stdout", tools.iperf_interval(args, i, client=False))
        interrupted = self.signalled.is_set()
        if interrupted:
            self.emit(
                "stdout",
                tools.iperf_error("interrupt - the client has terminated by signal Interrupt(2)"),
            )
            server.emit("stdout", tools.iperf_error("the client has terminated"))
        self.emit("stdout", tools.iperf_end(args, float(i), client=True, interrupted=interrupted))
        server.emit("stdout", tools.iperf_end(args, float(i), client=False, interrupted=False))
        server.exit(0)  # -s -1: one test, then exit
        self.exit(0)

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
        joined = " ".join(cmd)
        if cmd and cmd[0] == "ss":
            ports = [
                port
                for (lab, node, port) in self.engine.iperf_servers
                if lab == self.lab.state.lab_hash and node == self.node_id
            ]
            return 0, "".join(
                f"LISTEN 0 4096 *:{port} *:*\n" for port in ports if str(port) in joined
            )
        if "--version" in joined:
            return 0, "iperf 3.19.1 (fake)\ntcpdump version 4.99.5 (fake)\n"
        return 0, ""

    async def remove(self) -> None:
        self.engine.sidecars.pop(self.name, None)
        self.engine.calls.append(("remove_sidecar", self.name))
        self.signalled.set()
        if self._task and not self._task.done():
            self._task.cancel()
        self.exit(-1)


class FakeEngine:
    name = "fake"

    def __init__(self) -> None:
        self.labs: dict[str, _Lab] = {}
        self.fail_deploy: Exception | None = None
        self.fail_after_create: Exception | None = None
        self.fail_destroy: Exception | None = None
        self.crash_nodes: dict[str, str] = {}
        self.present_images: set[str] | None = None  # None = everything present
        self.pulled: list[str] = []
        self.pull_gate: asyncio.Event | None = None
        self.built: dict[str, ImageInfo] = {}  # normalized ref -> image
        self.builds: list[BuildSpec] = []
        self.build_gate: asyncio.Event | None = None
        self.fail_build: dict[str, str] = {}
        self.build_delay = 0.0
        self.platform = "linux/amd64"
        self.can_build = True
        self.sidecars: dict[str, FakeSidecar] = {}
        self.fail_sidecar: dict[str, str] = {}
        self.capture_packets: list[bytes] | None = None
        self.capture_pps = 20.0
        self.traffic_interval = 0.0
        self.iperf_servers: dict[tuple[str, str, int], FakeSidecar] = {}
        self.calls: list[tuple[str, str]] = []
        self.started_sidecars: list[SidecarSpec] = []

    @staticmethod
    def _hash(state: EngineState) -> str:
        # Same fallback as the Kathara engine: a provisional state has only a name.
        return state.lab_hash or hash_for_name(state.lab_name)

    async def is_available(self) -> tuple[bool, str]:
        return True, "fake engine"

    async def deploy(self, plan: LabPlan, on_progress: Progress) -> EngineState:
        if self.fail_deploy:
            raise self.fail_deploy
        state = EngineState(
            engine=self.name,
            lab_name=plan.name,
            lab_hash=hash_for_name(plan.name),
            user_prefix="fake",
            nodes={n.id: n.machine_name for n in plan.nodes},
        )
        running = {nid for nid in state.nodes if nid not in self.crash_nodes}
        self.labs[state.lab_hash] = _Lab(state=state, running=running, plan=plan)
        if self.fail_after_create:
            raise self.fail_after_create
        on_progress(f"Started {len(plan.nodes)} machines")
        return state

    async def destroy(self, state: EngineState) -> None:
        if self.fail_destroy:
            raise self.fail_destroy
        await self.remove_sidecars(lab_hash=self._hash(state))
        self.calls.append(("destroy", self._hash(state)))
        self.labs.pop(self._hash(state), None)

    async def status(self, state: EngineState) -> list[NodeStatus]:
        lab = self.labs.get(self._hash(state))
        return [
            NodeStatus(
                node_id=nid, name=m, state="running" if lab and nid in lab.running else "stopped"
            )
            for nid, m in state.nodes.items()
        ]

    async def resolve_container(self, state: EngineState, node_id: str) -> str:
        lab = self.labs.get(self._hash(state))
        if not lab or node_id not in lab.running:
            raise LookupError(f"Device '{node_id}' is not running")
        return f"fake_{state.nodes.get(node_id, node_id)}"

    async def node_logs(self, state: EngineState, tail: int = 30) -> list[NodeLog]:
        lab = self.labs.get(self._hash(state))
        if not lab:
            return []
        return [
            NodeLog(node_id=nid, name=m, exit_code=1, log=self.crash_nodes.get(nid, ""))
            for nid, m in lab.state.nodes.items()
            if nid not in lab.running
        ]

    async def list_labs(self) -> list[LabRef]:
        return [
            LabRef(
                lab_hash=h,
                user_prefix=lab.state.user_prefix,
                machines=sorted(lab.state.nodes.values()),
                running=len(lab.running),
                total=len(lab.state.nodes),
            )
            for h, lab in self.labs.items()
        ]

    async def purge(self, lab_hash: str) -> None:
        await self.remove_sidecars(lab_hash=lab_hash)
        self.labs.pop(lab_hash, None)

    def _local(self, ref: str) -> ImageInfo | None:
        built = self.built.get(normalize_ref(ref))
        if built is not None:
            return built
        if ref.startswith(LOCAL_PREFIX):
            return None
        if self.present_images is None or ref in self.present_images:
            return ImageInfo(ref=ref, id=f"sha256:{abs(hash(ref)):x}")
        return None

    async def images_present(self, images: list[str]) -> dict[str, bool]:
        return {i: self._local(i) is not None for i in images}

    async def inspect_images(self, refs: list[str]) -> dict[str, ImageInfo | None]:
        return {r: self._local(r) for r in refs}

    async def build_support(self) -> BuildSupport:
        detail = "fake builder" if self.can_build else "builds disabled"
        return BuildSupport(self.can_build, detail, self.platform)

    async def build_image(self, spec: BuildSpec, on_line: Progress) -> None:
        if self.build_gate is not None:
            await self.build_gate.wait()
        self.builds.append(spec)
        lines = [
            '#0 building with "default" instance using docker driver',
            f"#1 [internal] load build definition from {spec.dockerfile}",
            "#2 [1/3] FROM docker.io/library/ubuntu:24.04",
            "#3 [2/3] RUN apt-get update && apt-get install -y --no-install-recommends tools",
            "#4 [3/3] COPY . /opt/app",
            "#5 exporting to image",
        ]
        for line in lines:
            on_line(line)
            if self.build_delay:
                await asyncio.sleep(self.build_delay)
        if spec.ref in self.fail_build:
            on_line(f"ERROR: {self.fail_build[spec.ref]}")
            raise BuildError(self.fail_build[spec.ref])
        on_line(f"#5 naming to {normalize_ref(spec.ref)} done")
        self.built[normalize_ref(spec.ref)] = ImageInfo(
            ref=spec.ref,
            id=f"sha256:{len(self.builds):064x}",
            labels=dict(spec.labels),
            created=datetime.now(UTC).isoformat(),
            size=180_000_000,
            arch=self.platform.split("/")[-1],
        )

    async def pull_image(self, image: str, on_progress: Progress) -> None:
        if self.pull_gate is not None:
            await self.pull_gate.wait()
        self.pulled.append(image)
        on_progress(f"{image}: Pull complete")
        if self.present_images is not None:
            self.present_images.add(image)

    # ── sidecars ──
    def _lab_for(self, state: EngineState) -> _Lab:
        lab = self.labs.get(self._hash(state))
        if lab is None:
            raise LookupError("Lab is not deployed")
        return lab

    def _ping_pair(self, lab: _Lab, node_id: str, iface: str) -> tuple[str, str]:
        """Addresses for synthetic pings on a node interface: its IP and its peer's."""
        mine, peer = "10.0.0.1", "10.0.0.2"
        if lab.plan is None:
            return mine, peer
        cd = next(
            (
                i.collision_domain
                for n in lab.plan.nodes
                if n.id == node_id
                for i in n.interfaces
                if i.name == iface
            ),
            None,
        )
        for n in lab.plan.nodes:
            for i in n.interfaces:
                if i.collision_domain == cd and i.ip:
                    if n.id == node_id:
                        mine = i.ip
                    else:
                        peer = i.ip
        return mine, peer

    def _iperf_server_for(self, lab: _Lab, host: str | None, port: int) -> FakeSidecar | None:
        if lab.plan is None:
            return None
        for n in lab.plan.nodes:
            if any(i.ip == host for i in n.interfaces):
                return self.iperf_servers.get((lab.state.lab_hash, n.id, port))
        return None

    async def node_interfaces(self, state: EngineState, node_id: str) -> list[NodeInterface]:
        lab = self._lab_for(state)
        if node_id not in lab.running:
            raise LookupError(f"Device '{node_id}' is not running")
        node = next((n for n in (lab.plan.nodes if lab.plan else []) if n.id == node_id), None)
        return [
            NodeInterface(i.name, i.collision_domain) for i in (node.interfaces if node else [])
        ]

    async def start_sidecar(self, state: EngineState, spec: SidecarSpec) -> FakeSidecar:
        lab = self._lab_for(state)
        if spec.node_id not in lab.running:
            raise LookupError(f"Device '{spec.node_id}' is not running")
        sidecar = FakeSidecar(self, spec, lab)
        self.sidecars[sidecar.name] = sidecar
        self.started_sidecars.append(spec)
        sidecar.start()
        return sidecar

    async def list_sidecars(
        self, *, lab_hash: str | None = None, owner: str | None = None
    ) -> list[SidecarInfo]:
        return [
            SidecarInfo(
                name=sc.name,
                node_id=sc.node_id,
                job_id=sc.spec.job_id,
                purpose=sc.spec.purpose,
                lab_hash=sc.lab.state.lab_hash,
                owner=sc.spec.owner,
                status=sc.status,
            )
            for sc in list(self.sidecars.values())
            if (lab_hash is None or sc.lab.state.lab_hash == lab_hash)
            and (owner is None or sc.spec.owner == owner)
        ]

    async def remove_sidecars(
        self, *, lab_hash: str | None = None, job_id: str | None = None, owner: str | None = None
    ) -> int:
        if not (lab_hash or job_id or owner):
            raise ValueError("remove_sidecars needs a filter")
        doomed = [
            sc
            for sc in list(self.sidecars.values())
            if (lab_hash is None or sc.lab.state.lab_hash == lab_hash)
            and (job_id is None or sc.spec.job_id == job_id)
            and (owner is None or sc.spec.owner == owner)
        ]
        for sc in doomed:
            await sc.remove()
        return len(doomed)

    # ── telemetry ──
    async def sample_stats(
        self, state: EngineState, node_ids: list[str], sidecars: list[str] = ()
    ) -> list[RawStats]:
        lab = self._lab_for(state)
        elapsed = time.monotonic() - lab.started
        out: list[RawStats] = []
        ifaces_of: dict[str, list[str]] = {
            n.id: [i.name for i in n.interfaces] for n in (lab.plan.nodes if lab.plan else [])
        }

        def sample(target: str, kind: str, ifaces: list[str], load: float) -> RawStats:
            moved = int(elapsed * load * 1_000_000)
            return RawStats(
                target=target,
                kind=kind,  # type: ignore[arg-type]
                ts=time.time(),
                cpu_total_ns=int(elapsed * load * 1e8),
                system_cpu_ns=int(elapsed * 8e9),
                online_cpus=8,
                mem_usage=40_000_000 + int(load * 1_000_000),
                mem_inactive_file=4_000_000,
                mem_limit=8_000_000_000,
                pids=3,
                ifaces={
                    name: IfaceCounters(
                        rx_bytes=moved,
                        tx_bytes=moved,
                        rx_packets=moved // 1000,
                        tx_packets=moved // 1000,
                    )
                    for name in ifaces
                },
            )

        for i, nid in enumerate(node_ids):
            if nid in lab.running:
                out.append(sample(nid, "node", ifaces_of.get(nid, []), 1.0 + i))
        for name in sidecars:
            if name in self.sidecars:
                out.append(sample(name, "sidecar", [], 5.0))
        return out

    async def node_runtime_info(self, state: EngineState) -> list[NodeRuntimeInfo]:
        lab = self._lab_for(state)
        nodes = lab.plan.nodes if lab.plan else []
        return [
            NodeRuntimeInfo(
                node_id=n.id,
                machine=n.machine_name,
                container=f"fake_{n.machine_name}",
                image_ref=n.image,
                image_id=(self._local(n.image) or ImageInfo(ref=n.image, id="")).id,
                arch=self.platform.split("/")[-1],
            )
            for n in nodes
        ]

    async def environment(self) -> dict[str, Any]:
        return {
            "engine": self.name,
            "kathara": {"version": None, "network_plugin": {"name": "fake"}},
            "docker": {
                "server_version": "fake",
                "api_version": None,
                "os": "Fake OS",
                "os_type": "linux",
                "kernel": "0.0-fake",
                "arch": self.platform.split("/")[-1],
                "ncpu": 8,
                "mem_total": 8_000_000_000,
                "cgroup_version": "2",
                "cgroup_driver": "fake",
                "storage_driver": "fake",
                "default_runtime": "fake",
                "name": "fake",
            },
        }


def make_engine(name: str):
    """Engine factory used by the app (``Settings.engine``)."""
    if name == "fake":
        engine = FakeEngine()
        engine.build_delay = 0.5  # visible progress when driving the UI
        engine.traffic_interval = 1.0  # iperf3 reports once a second, as it does for real
        return engine
    from engine.kathara.engine import KatharaEngine

    return KatharaEngine()
