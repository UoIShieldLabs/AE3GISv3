"""The live lab view: one collector for the whole host, shared by every viewer.

While someone has a lab's live view open (the editor's Tutorials panel), this
service keeps one ``ae3gis-collect --procs`` helper running and turns each of
its sweeps into, per watched topology, the links that carry traffic and what
runs in each node (``domain.pulse``). A viewer subscribes to its topology's
channel over a WebSocket (``api/pulse.py``); a message goes out only when the
picture changed, and a late joiner gets the latest one.

The collector is a job (kind ``pulse``, subject ``pulse``: one at a time,
host-wide) so its image is ensured and its helper cleaned up like any tool
job's. It starts with the first viewer and winds down ``LINGER_S`` after the
last one leaves. It reads /proc and cgroups only, so its cost does not grow
with viewers: thirty students watching thirty labs share one sweep.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC
from typing import Any

import catalog
from db.models import Topology
from domain import monitor as m
from domain import pulse
from engine.base import EngineState, HelperSpec, Sidecar
from services import deployment, jobs
from services.jobs import JobRunner
from services.live import Channel

log = logging.getLogger(__name__)

KIND = "pulse"
SUBJECT = "pulse"
INTERVAL_S = 1.0
# Keep the collector this long after the last viewer left (a reload, a tab switch).
LINGER_S = 10.0
# How often a watch re-reads its topology (deployed? links? since when?) and the
# service re-lists the host's containers.
REFRESH_S = 5.0
UNKNOWN_REFRESH_S = 1.0
_STARTING = "(starting)"


@dataclass
class _Watch:
    topology_id: str
    channel: Channel
    refs: int = 0
    loaded: float = 0.0  # monotonic; 0 = never
    lab_hash: str | None = None
    node_for_machine: dict[str, str] = field(default_factory=dict)
    links: list[dict[str, Any]] = field(default_factory=list)
    since: float = 0.0
    prev: pulse.Counters | None = None
    prev_t: float = 0.0
    activity: pulse.LinkActivity = field(default_factory=pulse.LinkActivity)
    tracker: pulse.ProcessTracker = field(default_factory=pulse.ProcessTracker)
    last: dict[str, Any] | None = None


class PulseService:
    """Who watches which topology, and the job that feeds them. Loop-only."""

    def __init__(self, runner: JobRunner) -> None:
        self.runner = runner
        self._watches: dict[str, _Watch] = {}
        self._job_id: str | None = None
        self._idle_since: float | None = None
        # short container id -> (lab hash, machine name) of every Kathara node
        self._containers: dict[str, tuple[str, str]] = {}
        self._listed = 0.0

    # ── viewers ──
    async def acquire(self, topology_id: str) -> Channel:
        """A viewer arrived: its topology's channel, with the collector running."""
        watch = self._watches.get(topology_id)
        if watch is None:
            watch = _Watch(topology_id, Channel(asyncio.get_running_loop(), replay=1))
            self._watches[topology_id] = watch
        watch.refs += 1
        self._idle_since = None
        if self._job_id is None:
            self._job_id = _STARTING
            try:
                self._job_id = await asyncio.to_thread(self._create_job)
            except BaseException:
                self._job_id = None
                self.release(topology_id)
                raise
            self.runner.submit(self._job_id)
        return watch.channel

    def release(self, topology_id: str, channel: Channel | None = None) -> None:
        """A viewer left. ``channel`` is the one it was given: a viewer of a
        collector that ended must not release its successor's watch."""
        watch = self._watches.get(topology_id)
        if watch is None or (channel is not None and watch.channel is not channel):
            return
        watch.refs -= 1
        if watch.refs <= 0:
            del self._watches[topology_id]
            watch.channel.close()
        if not self._watches:
            self._idle_since = time.monotonic()

    def idle_for(self) -> float:
        """Seconds since the last viewer left (0 while someone watches)."""
        return 0.0 if self._idle_since is None else time.monotonic() - self._idle_since

    def watching(self) -> list[str]:
        return list(self._watches)

    def _create_job(self) -> str:
        with self.runner.session_factory() as db:
            job = jobs.create_job(db, KIND, subject=SUBJECT, params={"label": "Live lab view"})
            db.commit()
            return job.id

    def detach(self, job_id: str) -> None:
        """The job is winding down: a viewer arriving from now on starts the next one."""
        if self._job_id == job_id:
            self._job_id = None

    def job_ended(self, job_id: str, error: str | None) -> None:
        """The collector is gone. Unless the next one is already on its way,
        viewers still here are told and let go (they reconnect to retry)."""
        self.detach(job_id)
        self._containers, self._listed = {}, 0.0
        if self._job_id is not None:
            return
        watches, self._watches = self._watches, {}
        for watch in watches.values():
            watch.channel.close({"type": "unavailable", "reason": error or "stopped"})

    # ── sweeps ──
    async def on_sweep(self, sweep: m.Sweep) -> None:
        if not self._watches:
            return
        now = time.monotonic()
        age = now - self._listed
        unknown = any(cid not in self._containers for cid in sweep.containers)
        if age > REFRESH_S or (unknown and age > UNKNOWN_REFRESH_S):
            await self._list_containers()
        for watch in list(self._watches.values()):
            if now - watch.loaded > REFRESH_S or not watch.loaded:
                with contextlib.suppress(Exception):
                    self._apply(watch, await asyncio.to_thread(self._load, watch.topology_id))
                watch.loaded = now
            message = self._picture(watch, sweep)
            if message != watch.last:
                watch.last = message
                watch.channel.publish(message)

    async def _list_containers(self) -> None:
        try:
            refs = await self.runner.engine.list_containers()
        except Exception as exc:  # pragma: no cover - engine hiccup; keep the old map
            log.debug("Pulse could not list containers: %s", exc)
            return
        self._containers = {
            ref.id[:12]: (labels.get("lab_hash", ""), labels.get("name", ""))
            for ref in refs
            if (labels := ref.labels or {}).get("app") == "kathara"
        }
        self._listed = time.monotonic()

    def _load(self, topology_id: str) -> dict[str, Any] | None:
        """What a watch needs from the DB; None when the topology is not deployed."""
        with self.runner.session_factory() as db:
            topo = db.get(Topology, topology_id)
            state = EngineState.from_dict(topo.engine_state) if topo else None
            if topo is None or topo.status != "deployed" or state is None:
                return None
            links, _ = deployment.deployed_links(topo)
            deployed = jobs.last_deploy_finished(db, topology_id)
            since = deployed.replace(tzinfo=UTC).timestamp() if deployed else 0.0
            return {
                "lab_hash": state.lab_hash,
                "node_for_machine": {mname: nid for nid, mname in state.nodes.items()},
                "links": pulse.keyed_links(links, topo.data or {}),
                "since": since + pulse.DEPLOY_GRACE_S if since else 0.0,
            }

    @staticmethod
    def _apply(watch: _Watch, loaded: dict[str, Any] | None) -> None:
        lab_hash = loaded["lab_hash"] if loaded else None
        if lab_hash != watch.lab_hash or (loaded and loaded["since"] != watch.since):
            # Another lab (or none): nothing carries over.
            watch.prev = None
            watch.activity = pulse.LinkActivity()
            watch.tracker = pulse.ProcessTracker()
        watch.lab_hash = lab_hash
        watch.node_for_machine = loaded["node_for_machine"] if loaded else {}
        watch.links = loaded["links"] if loaded else []
        watch.since = loaded["since"] if loaded else 0.0

    def _picture(self, watch: _Watch, sweep: m.Sweep) -> dict[str, Any]:
        if not watch.lab_hash:
            return pulse.payload({}, {})
        counters: pulse.Counters = {}
        procs: dict[str, list[pulse.Proc]] = {}
        for cid, raw in sweep.containers.items():
            lab_hash, machine = self._containers.get(cid, ("", ""))
            node = watch.node_for_machine.get(machine) if lab_hash == watch.lab_hash else None
            if node is None:
                continue
            counters[node] = raw.ifaces
            if cid in sweep.procs and sweep.btime:
                parent, rows = sweep.procs[cid]
                procs[node] = pulse.node_processes(
                    parent, rows, btime=sweep.btime, clk_tck=sweep.clk_tck, since=watch.since
                )
        rates = (
            pulse.link_rates(watch.links, watch.prev, counters, sweep.t - watch.prev_t)
            if watch.prev is not None
            else {}
        )
        watch.prev, watch.prev_t = counters, sweep.t
        nodes = watch.tracker.update(procs, sweep.t)
        return pulse.payload(watch.activity.update(rates, sweep.t), nodes)


# ── the job ───────────────────────────────────────────────────────────


async def run_pulse(runner: JobRunner, job_id: str) -> None:
    settings = runner.settings
    service: PulseService | None = runner.pulse
    assert settings is not None and service is not None
    engine = runner.engine
    image = catalog.tool_image("collector")
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()
    stderr: deque[str] = deque(maxlen=20)
    helper: Sidecar | None = None
    pump: asyncio.Future | None = None
    error: str | None = None
    buf = b""

    def on_stdout(chunk: bytes) -> None:
        nonlocal buf
        buf += chunk
        *lines, buf = buf.split(b"\n")
        for line in lines:
            if line.strip():
                loop.call_soon_threadsafe(queue.put_nowait, line)

    def on_stderr(chunk: bytes) -> None:
        stderr.extend(s.strip() for s in chunk.decode("utf-8", "replace").splitlines() if s.strip())

    try:
        async with runner.step(job_id, "images"):
            assert runner.images is not None
            await runner.images.ensure_images(
                runner, job_id, [image], stale_event="pulse.images_stale", rebuild_stale=True
            )
        async with runner.step(job_id, "collect"):
            helper = await engine.start_helper(
                HelperSpec(
                    image=image,
                    command=["ae3gis-collect", "--interval", str(INTERVAL_S), "--procs"],
                    purpose="collector",
                    job_id=job_id,
                    owner=settings.ensure_instance_id(),
                    lab_hash="",
                    pid_host=True,
                    cgroupns_host=True,
                    binds={settings.collector_cgroup_root: "/host/cgroup"},
                )
            )
            pump = asyncio.ensure_future(helper.pump(on_stdout, on_stderr))
            pump.add_done_callback(lambda _f: loop.call_soon(queue.put_nowait, None))
            while not runner.stop_requested(job_id) and service.idle_for() < LINGER_S:
                try:
                    line = await asyncio.wait_for(queue.get(), timeout=1.0)
                except TimeoutError:
                    continue
                if line is None:
                    raise RuntimeError(
                        "The collector stopped: " + ("; ".join(stderr) or "no output")
                    )
                sweep = m.parse_line(line)
                if sweep is not None:
                    await service.on_sweep(sweep)
            service.detach(job_id)
    except BaseException as exc:
        error = str(exc) or type(exc).__name__
        raise
    finally:
        if helper is not None:
            with contextlib.suppress(Exception):
                await helper.remove()
        if pump is not None:
            pump.cancel()
            with contextlib.suppress(BaseException):
                await pump
        with contextlib.suppress(Exception):
            await engine.remove_sidecars(job_id=job_id)
        service.job_ended(job_id, error)


def register(runner: JobRunner) -> PulseService:
    service = PulseService(runner)
    runner.pulse = service
    runner.register(KIND, run_pulse, cancellable=True, stoppable=True)
    return service
