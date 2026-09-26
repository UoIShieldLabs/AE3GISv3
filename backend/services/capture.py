"""Live packet capture on a deployed node interface or link, as a job.

A capture runs ``tcpdump -w -`` in a sidecar sharing the node's network
namespace (engine seam), so it works whatever image the node runs. The pcap
stream is relayed into ``artifacts/<job>/capture.pcap`` one whole record at a
time, so the file is a valid capture at every moment (downloads and the live
Wireshark stream read only up to ``committed``). Packet summaries go to the
job's live channel for the browser, rate-limited; the pcap always has
everything.

Jobs: kind ``capture``, subject ``capture:<topology>:<node>:<interface>`` (a
second request for the same interface returns the running job), stoppable:
stopping keeps the pcap and finishes the job as ``succeeded``. Steps:
``images`` (the tool image) → ``attach`` (checks the interface, starts the
sidecar, records the environment) → ``capture``.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
import threading
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

import catalog
from api.errors import Conflict
from db.models import Job, Topology
from domain.links import TargetError, resolve_target
from domain.packets import summarize
from domain.pcap import PcapError, PcapSplitter
from engine.base import EngineState, SidecarSpec
from services import deployment, environment, events, jobs
from services.jobs import JobRunner
from services.live import Channel

log = logging.getLogger(__name__)

KIND = "capture"
PCAP_NAME = "capture.pcap"
RUN_NAME = "run.json"
DEFAULT_SNAPLEN = 262144
STDERR_KEEP = 16_384
PUBLISH_EVERY_S = 0.25
BATCH_MAX = 200
RECENT_KEPT = 200

# Relays of running captures, by job id: downloads and the live Wireshark
# stream read the pcap only up to what a relay has committed.
_ACTIVE: dict[str, PcapRelay] = {}


def subject(topology_id: str, node_id: str, interface: str) -> str:
    return f"capture:{topology_id}:{node_id}:{interface}"


def active_relay(job_id: str) -> PcapRelay | None:
    return _ACTIVE.get(job_id)


# ── the relay (runs on the sidecar's pump thread) ─────────────────────


class PcapRelay:
    """Splits the pcap stream into records, appends them to the file, counts,
    enforces the caps and batches packet summaries for the live channel."""

    def __init__(
        self,
        path: Path,
        channel: Channel,
        loop: asyncio.AbstractEventLoop,
        *,
        max_bytes: int,
        max_packets: int | None,
        ui_max_pps: int,
    ) -> None:
        self.path = path
        self._fh = path.open("wb")
        self._channel = channel
        self._loop = loop
        self._splitter = PcapSplitter()
        self._lock = threading.Lock()
        self.max_bytes = max_bytes
        self.max_packets = max_packets
        self.ui_max_pps = ui_max_pps
        self.committed = 0  # file bytes that are whole, flushed records
        self.packets = 0
        self.wire_bytes = 0
        self.undecoded = 0
        self.limit_hit: str | None = None
        self.error: str | None = None
        self.done = False
        self.stopped = asyncio.Event()  # set (on the loop) when a cap is hit
        self._stderr = bytearray()
        self._batch: list[dict[str, Any]] = []
        # The last records, whether or not anyone watches: a live view opened
        # mid-capture starts from these.
        self._recent: deque[tuple[int, float, bytes, int]] = deque(maxlen=RECENT_KEPT)
        self._window = (0.0, 0)  # (second started, packets decoded in it)
        self._last_publish = 0.0

    @property
    def linktype(self) -> int | None:
        return self._splitter.linktype

    def _hit(self, why: str) -> None:
        if self.limit_hit is None:
            self.limit_hit = why
            self._loop.call_soon_threadsafe(self.stopped.set)

    def on_stdout(self, chunk: bytes) -> None:
        with self._lock:
            if self.limit_hit or self.done:
                return
            had_header = self._splitter.header is not None
            try:
                records = self._splitter.feed(chunk)
            except PcapError as exc:
                self.error = str(exc)
                self._hit("corrupt")
                return
            if not had_header and self._splitter.header is not None:
                self._fh.write(self._splitter.header)
                self.committed += len(self._splitter.header)
            watching = self._channel.subscribers > 0
            now = time.monotonic()
            for rec in records:
                if self.committed + len(rec.raw) > self.max_bytes:
                    self._hit("limit:size")
                    break
                self._fh.write(rec.raw)
                self.committed += len(rec.raw)
                self.packets += 1
                self.wire_bytes += rec.origlen
                self._recent.append((self.packets, rec.ts, rec.data, rec.origlen))
                if watching:
                    start, count = self._window
                    if now - start >= 1.0:
                        start, count = now, 0
                    if count < self.ui_max_pps:
                        self._batch.append(
                            summarize(
                                self.packets, rec.ts, rec.data, rec.origlen, self.linktype
                            ).to_dict()
                        )
                        count += 1
                    else:
                        self.undecoded += 1
                    self._window = (start, count)
                if self.max_packets and self.packets >= self.max_packets:
                    self._hit("limit:packets")
                    break
            self._fh.flush()
            if self._batch and (
                now - self._last_publish >= PUBLISH_EVERY_S or len(self._batch) >= BATCH_MAX
            ):
                self._publish_locked(now)

    def on_stderr(self, chunk: bytes) -> None:
        with self._lock:
            self._stderr.extend(chunk)
            if len(self._stderr) > STDERR_KEEP:
                del self._stderr[: len(self._stderr) - STDERR_KEEP]

    def _publish_locked(self, now: float) -> None:
        batch, self._batch = self._batch, []
        self._last_publish = now
        self._channel.publish_threadsafe(
            {"type": "packets", "items": batch, "undecoded": self.undecoded}
        )

    def recent_summaries(self) -> list[dict[str, Any]]:
        with self._lock:
            recent = list(self._recent)
        return [
            summarize(n, ts, data, origlen, self.linktype).to_dict()
            for n, ts, data, origlen in recent
        ]

    def flush_live(self) -> None:
        with self._lock:
            if self._batch:
                self._publish_locked(time.monotonic())

    @property
    def stderr(self) -> str:
        with self._lock:
            return self._stderr.decode("utf-8", "replace")

    def close(self) -> None:
        self.flush_live()
        with self._lock:
            self.done = True
            with contextlib.suppress(OSError):
                self._fh.close()


_TCPDUMP_TOTALS = {
    "captured": re.compile(r"(\d+) packets? captured"),
    "received_by_filter": re.compile(r"(\d+) packets? received by filter"),
    "dropped_by_kernel": re.compile(r"(\d+) packets? dropped by kernel"),
}


def tcpdump_totals(stderr: str) -> dict[str, int]:
    out = {}
    for key, rx in _TCPDUMP_TOTALS.items():
        m = rx.search(stderr)
        if m:
            out[key] = int(m.group(1))
    return out


def last_error_line(stderr: str) -> str:
    lines = [ln.strip() for ln in stderr.splitlines() if ln.strip()]
    lines = [ln for ln in lines if not ln.startswith("tcpdump: listening on")]
    return lines[-1] if lines else "tcpdump exited"


def tcpdump_argv(interface: str, snaplen: int, bpf: str) -> list[str]:
    argv = [
        "tcpdump",
        "-i",
        interface,
        "-n",
        "-U",
        "--immediate-mode",
        "-B",
        "4096",
        "-s",
        str(snaplen or DEFAULT_SNAPLEN),
        "-w",
        "-",
    ]
    if bpf.strip():
        # One argument after "--": never a shell, never parsed as an option.
        argv += ["--", bpf.strip()]
    return argv


# ── starting (request side) ──────────────────────────────────────────


def start_capture(db: Session, runner: JobRunner, topo: Topology, req: dict[str, Any]):
    """Create (or return the running) capture job; (job, created)."""
    settings = runner.settings
    assert settings is not None
    with runner.admission:
        db.refresh(topo)
        if topo.status != "deployed":
            raise Conflict(
                "Deploy the topology before capturing", code="bad_state", status=topo.status
            )
        links, mapping = deployment.deployed_links(topo)
        try:
            ep = resolve_target(links, req["target"])
        except TargetError as exc:
            raise Conflict(str(exc), code=exc.code) from None
        subj = subject(topo.id, ep.node_id, ep.interface)
        existing = jobs.active_for_subject(db, subj)
        if existing is not None:
            return existing, False
        running = sum(
            1 for _ in db.query(Job.id).filter(Job.kind == KIND, Job.status.in_(jobs.ACTIVE))
        )
        if running >= settings.max_active_captures:
            raise Conflict(
                f"{running} captures are already running (the limit is "
                f"{settings.max_active_captures}); stop one first",
                code="too_many_captures",
            )
        limits = {
            "max_seconds": min(
                req.get("max_seconds") or settings.capture_max_seconds, settings.capture_max_seconds
            ),
            "max_bytes": min(
                req.get("max_bytes") or settings.capture_max_bytes, settings.capture_max_bytes
            ),
            "max_packets": req.get("max_packets") or None,
        }
        node_ids = [ep.node_id] + ([ep.peer_node_id] if ep.peer_node_id else [])
        params = {
            "target": req["target"],
            "endpoint": ep.to_dict(),
            "mapping": mapping,
            "filter": (req.get("filter") or "").strip(),
            "snaplen": req.get("snaplen") or 0,
            "limits": limits,
            "label": req.get("label") or f"{ep.machine} {ep.interface}",
            "node_ids": node_ids,
            "connection_ids": [ep.connection_id] if ep.connection_id else [],
        }
        job = jobs.create_job(db, KIND, subject=subj, topology_id=topo.id, params=params)
        events.record(
            db,
            type="capture.requested",
            message=f"Capture requested on {ep.machine} {ep.interface}",
            topology_id=topo.id,
            job_id=job.id,
        )
        db.commit()
    db.refresh(job)
    runner.submit(job.id)
    return job, True


# ── the job ───────────────────────────────────────────────────────────


def _load(runner: JobRunner, job_id: str) -> tuple[dict[str, Any], Topology, EngineState | None]:
    with runner.session_factory() as db:
        job = db.get(Job, job_id)
        topo = db.get(Topology, job.topology_id)
        db.expunge(topo)
        return dict(job.params or {}), topo, EngineState.from_dict(topo.engine_state)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(path)


async def run_capture(runner: JobRunner, job_id: str) -> None:
    settings, store, hub = runner.settings, runner.artifacts, runner.live
    assert settings is not None and store is not None and hub is not None
    engine = runner.engine
    channel = hub.open(job_id)
    params, topo, state = _load(runner, job_id)
    ep = params["endpoint"]
    limits = params.get("limits") or {}
    run_path = store.path(job_id, RUN_NAME, create_dir=True)
    started = datetime.now(UTC)
    relay: PcapRelay | None = None
    sidecar = None
    env: dict[str, Any] = {}
    stopped_by: str | None = None
    exit_code: int | None = None
    try:
        async with runner.step(job_id, "images"):
            tool = catalog.tool_image("capture")
            assert runner.images is not None
            await runner.images.ensure_images(
                runner, job_id, [tool], stale_event="capture.images_stale"
            )

        async with runner.step(job_id, "attach", message=f"{ep['machine']} {ep['interface']}"):
            if topo.status != "deployed" or state is None:
                raise RuntimeError("The topology is not deployed")
            attached = {i.name: i for i in await engine.node_interfaces(state, ep["node_id"])}
            live = attached.get(ep["interface"])
            if live is None or (
                live.collision_domain and live.collision_domain != ep["collision_domain"]
            ):
                raise RuntimeError(
                    f"{ep['machine']} {ep['interface']} is no longer attached to "
                    f"{ep['collision_domain']} (redeploy the topology)"
                )
            relay = PcapRelay(
                store.path(job_id, PCAP_NAME),
                channel,
                asyncio.get_running_loop(),
                max_bytes=int(limits.get("max_bytes") or settings.capture_max_bytes),
                max_packets=limits.get("max_packets"),
                ui_max_pps=settings.capture_ui_max_pps,
            )
            _ACTIVE[job_id] = relay
            sidecar = await engine.start_sidecar(
                state,
                SidecarSpec(
                    node_id=ep["node_id"],
                    image=tool,
                    command=tcpdump_argv(
                        ep["interface"], params.get("snaplen") or 0, params.get("filter") or ""
                    ),
                    purpose="capture",
                    job_id=job_id,
                    owner=settings.ensure_instance_id(),
                ),
            )
            runner.log(job_id, f"Sidecar {sidecar.name}")
            versions = {}
            with contextlib.suppress(Exception):
                _, text = await sidecar.exec(["tcpdump", "--version"])
                versions["tcpdump"] = text.splitlines()[0].strip() if text else ""
            env = await environment.snapshot(
                engine, settings, topo, state, tool_ref=tool, tool_versions=versions
            )
            _write_json(
                run_path,
                {"kind": KIND, "params": params, "environment": env, "started_at": started},
            )

        async with runner.step(
            job_id, "capture", message=f"Capturing on {ep['machine']} {ep['interface']}"
        ):
            pump = asyncio.ensure_future(sidecar.pump(relay.on_stdout, relay.on_stderr))
            stop = asyncio.ensure_future(runner.stop_event(job_id).wait())
            capped = asyncio.ensure_future(relay.stopped.wait())
            deadline = time.monotonic() + float(
                limits.get("max_seconds") or settings.capture_max_seconds
            )
            last = (time.monotonic(), 0, 0)
            try:
                while True:
                    done, _ = await asyncio.wait(
                        {pump, stop, capped}, timeout=1.0, return_when=asyncio.FIRST_COMPLETED
                    )
                    now = time.monotonic()
                    t0, p0, b0 = last
                    pps = (relay.packets - p0) / max(now - t0, 1e-6)
                    bps = (relay.wire_bytes - b0) * 8 / max(now - t0, 1e-6)
                    last = (now, relay.packets, relay.wire_bytes)
                    relay.flush_live()
                    channel.publish(
                        {
                            "type": "status",
                            "packets": relay.packets,
                            "bytes": relay.wire_bytes,
                            "file_bytes": relay.committed,
                            "pps": round(pps, 1),
                            "bps": round(bps),
                            "undecoded": relay.undecoded,
                        },
                        replay=False,
                    )
                    runner.progress(
                        job_id,
                        "capture",
                        f"{relay.packets} packets · {relay.committed / 1e6:.1f} MB",
                        min_interval=2.0,
                    )
                    if pump in done:
                        stopped_by = "sidecar_exit"
                        break
                    if stop in done:
                        stopped_by = runner.stop_code(job_id) or "user"
                        break
                    if capped in done:
                        stopped_by = relay.limit_hit or "limit"
                        break
                    if now >= deadline:
                        stopped_by = "limit:time"
                        break
                if not pump.done():
                    await sidecar.signal("SIGINT")
                    with contextlib.suppress(TimeoutError):
                        await asyncio.wait_for(asyncio.shield(pump), timeout=5.0)
                if pump.done() and not pump.cancelled():
                    exit_code = pump.result()
            finally:
                for task in (stop, capped):
                    task.cancel()
                if not pump.done():
                    await sidecar.remove()
                    with contextlib.suppress(BaseException):
                        await pump
            if relay.error:
                raise RuntimeError(f"The capture stream broke: {relay.error}")
            if stopped_by == "sidecar_exit" and exit_code not in (0, None) and relay.packets == 0:
                raise RuntimeError(last_error_line(relay.stderr))
            runner.progress(
                job_id, "capture", f"{relay.packets} packets · {relay.committed / 1e6:.1f} MB"
            )
    finally:
        if sidecar is not None:
            with contextlib.suppress(Exception):
                await sidecar.remove()
        result = _result(params, relay, started, stopped_by, exit_code)
        _ACTIVE.pop(job_id, None)
        if relay is not None:
            relay.close()
        with contextlib.suppress(Exception):
            runner.set_result(job_id, result)
        with contextlib.suppress(Exception):
            _write_json(
                run_path,
                {
                    "kind": KIND,
                    "params": params,
                    "environment": env,
                    "started_at": started,
                    "result": result,
                },
            )
        channel.close({"type": "end", "result": result})
        hub.prune()


def _result(
    params: dict[str, Any],
    relay: PcapRelay | None,
    started: datetime,
    stopped_by: str | None,
    exit_code: int | None,
) -> dict[str, Any]:
    ended = datetime.now(UTC)
    totals = tcpdump_totals(relay.stderr) if relay else {}
    return {
        "endpoint": params.get("endpoint"),
        "filter": params.get("filter") or "",
        "snaplen": params.get("snaplen") or DEFAULT_SNAPLEN,
        "packets": relay.packets if relay else 0,
        "bytes": relay.wire_bytes if relay else 0,
        "file_bytes": relay.committed if relay else 0,
        "undecoded": relay.undecoded if relay else 0,
        "dropped_by_kernel": totals.get("dropped_by_kernel"),
        "received_by_filter": totals.get("received_by_filter"),
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_s": round((ended - started).total_seconds(), 3),
        "stopped_by": stopped_by,
        "exit_code": exit_code,
        "pcap": PCAP_NAME if relay and relay.committed else None,
    }


def register(runner: JobRunner) -> None:
    runner.register(KIND, run_capture, cancellable=True, stoppable=True)
