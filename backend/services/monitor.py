"""Resource monitoring of a deployed lab and of its host, as a job.

One collector helper container (``ae3gis-collect`` in the tools image, see
``engine.base.HelperSpec``) reads the host's and every container's counters
from ``/proc`` and the cgroup tree once per interval; the Docker daemon is
never asked, so watching 500 nodes costs about what watching 5 does.
``MonitorSession`` turns its lines into rates (``domain/monitor``), writes
them to CSV and fans a live summary out to WebSockets. Benchmarks run a
session of their own across every step (``services/benchmark``).

Artifacts (``data/artifacts/<job>/``), gzipped when the monitor ends:

- ``host.csv``: per sweep, the host (VM CPU, memory, load, PSI, sweep time),
  Docker's own processes, and CPU/memory totals per group (node, tool,
  other_lab, other)
- ``nodes.csv``: per sweep, each recorded node (CPU, memory, pids, OOM kills,
  interface totals) and each AE3GIS sidecar/helper
- ``ifaces.csv``: per sweep, each recorded node's interfaces
- ``markers.csv``: what happened when (traffic started, a step began…)
- ``monitor.json``: the request, the environment, the targets and a summary

Jobs: kind ``monitor``, subject ``monitor:<topology>`` (one per topology),
stoppable. Steps: ``images`` → ``prepare`` (collector running, first sweep in,
environment recorded) → ``run``.
"""

from __future__ import annotations

import asyncio
import contextlib
import csv
import gzip
import io
import json
import logging
import shutil
import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

import catalog
from api.errors import Conflict, Invalid
from db.models import Job, Topology
from domain import monitor as m
from domain import selectors
from engine.base import DeploymentEngine, EngineState, HelperSpec, Sidecar
from services import environment, events, jobs
from services.jobs import JobRunner
from services.live import Channel

log = logging.getLogger(__name__)

KIND = "monitor"
INFO_NAME = "monitor.json"
HOST_NAME, NODES_NAME, IFACES_NAME, MARKERS_NAME = (
    "host.csv",
    "nodes.csv",
    "ifaces.csv",
    "markers.csv",
)
CSV_NAMES = (HOST_NAME, NODES_NAME, IFACES_NAME, MARKERS_NAME)
REFRESH_S = 10.0  # re-read container labels at least this often
UNKNOWN_REFRESH_S = 2.0  # …and sooner when an unknown container shows up
FIRST_SWEEP_TIMEOUT_S = 30.0
LIVE_NODE_LIMIT = 50  # per-node rows in live messages up to this many nodes
RING = 120  # live messages kept for late subscribers

HOST_COLUMNS = [
    "t",
    "step",
    *m.HOST_FIELDS,
    *(f"{n.replace('-', '_')}_{k}" for n in m.INFRA_NAMES for k in ("count", "rss", "cpu_pct")),
    *(f"{g}_{k}" for g in m.GROUPS for k in ("count", "cpu_pct", "mem_used")),
]
NODE_COLUMNS = [
    "t",
    "step",
    "target",
    "kind",
    "purpose",
    "cpu_pct",
    "mem_used",
    "mem_limit",
    "pids",
    "oom_kills",
    "rx_bps",
    "tx_bps",
    "rx_pps",
    "tx_pps",
    "drops",
    "errors",
]
IFACE_COLUMNS = [
    "t",
    "step",
    "target",
    "iface",
    "rx_bps",
    "tx_bps",
    "rx_pps",
    "tx_pps",
    "rx_dropped",
    "tx_dropped",
    "errors",
]
MARKER_COLUMNS = ["t", "step", "source", "text"]
SUMMARY_HOST_FIELDS = (
    "vm_cpu_pct",
    "cores_used",
    "mem_used",
    "mem_used_pct",
    "load1",
    "psi_cpu_some",
    "psi_mem_some",
    "psi_mem_full",
    "psi_io_some",
    "sweep_ms",
)

# Sessions running now, by job id (monitor jobs and benchmarks).
_SESSIONS: dict[str, MonitorSession] = {}


def subject(topology_id: str) -> str:
    return f"monitor:{topology_id}"


def active_session(job_id: str) -> MonitorSession | None:
    return _SESSIONS.get(job_id)


def register_session(key: str, session: MonitorSession) -> None:
    """Make a session others can mark (a benchmark's, keyed by its job id)."""
    _SESSIONS[key] = session


def unregister_session(key: str) -> None:
    _SESSIONS.pop(key, None)


def mark(topology_id: str, source: str, text: str) -> None:
    """Note an event on every running monitor of the topology."""
    for session in list(_SESSIONS.values()):
        if session.topology_id == topology_id:
            session.mark(source, text)


def host_csv_row(t: float, step: str, host: dict[str, Any], groups: dict) -> dict[str, Any]:
    row: dict[str, Any] = {"t": t, "step": step, **{k: host.get(k) for k in m.HOST_FIELDS}}
    for name in m.INFRA_NAMES:
        v = (host.get("infra") or {}).get(name) or {}
        key = name.replace("-", "_")
        for k in ("count", "rss", "cpu_pct"):
            row[f"{key}_{k}"] = v.get(k)
    for g, v in groups.items():
        for k in ("count", "cpu_pct", "mem_used"):
            row[f"{g}_{k}"] = v.get(k)
    return row


class _CsvFile:
    def __init__(self, path: Path, columns: list[str]) -> None:
        self.path = path
        self._fh = path.open("w", newline="")
        self._w = csv.DictWriter(self._fh, fieldnames=columns, extrasaction="ignore")
        self._w.writeheader()

    def write(self, rows: list[dict[str, Any]]) -> None:
        self._w.writerows(rows)

    def flush(self) -> None:
        self._fh.flush()

    def close(self, *, compress: bool) -> None:
        with contextlib.suppress(OSError):
            self._fh.close()
        if compress and self.path.exists():
            with self.path.open("rb") as src, gzip.open(f"{self.path}.gz", "wb") as dst:
                shutil.copyfileobj(src, dst)
            self.path.unlink()


class MonitorSession:
    """A running collector and what it has recorded so far.

    ``scope`` says which lab's nodes are nodes and which of them are recorded
    one by one (a benchmark swaps it per step with ``set_scope``). Callbacks in
    ``on_sweep`` get each ``SweepResult`` and its live message on the loop.
    """

    def __init__(
        self,
        engine: DeploymentEngine,
        *,
        directory: Path,
        interval: float,
        job_id: str,
        owner: str,
        image: str,
        cgroup_root: str,
        scope: m.Scope,
        topology_id: str | None = None,
        channel: Channel | None = None,
        compress: bool = True,
    ) -> None:
        self.engine = engine
        self.dir = directory
        self.interval = interval
        self.job_id = job_id
        self.owner = owner
        self.image = image
        self.cgroup_root = cgroup_root
        self.scope = scope
        self.topology_id = topology_id
        self.channel = channel
        self.compress = compress
        self.t0 = time.time()
        self.latest: dict[str, Any] | None = None
        self.ring: deque[dict[str, Any]] = deque(maxlen=RING)
        self.host_rows: list[dict[str, Any]] = []  # one per sweep (benchmarks slice these)
        self.markers: list[dict[str, Any]] = []
        self.on_sweep: list[Callable[[m.SweepResult, dict[str, Any]], None]] = []
        self.error: str | None = None
        self.sweeps = 0
        self.helper: Sidecar | None = None
        self._targets: dict[str, m.Target] = {}
        self._refreshed = 0.0
        self._prev: m.Sweep | None = None
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._buf = b""
        self._stderr: deque[str] = deque(maxlen=20)
        self._pump: asyncio.Future | None = None
        self._consumer: asyncio.Task | None = None
        self._first = asyncio.Event()
        self._node_stats: dict[str, dict[str, m.RunningStats]] = {}
        self._oom: dict[str, int] = {}
        self._seen_ever: set[str] = set()
        self._missing: set[str] = set()
        self._closed = False
        directory.mkdir(parents=True, exist_ok=True)
        self._files = {
            HOST_NAME: _CsvFile(directory / HOST_NAME, HOST_COLUMNS),
            NODES_NAME: _CsvFile(directory / NODES_NAME, NODE_COLUMNS),
            IFACES_NAME: _CsvFile(directory / IFACES_NAME, IFACE_COLUMNS),
            MARKERS_NAME: _CsvFile(directory / MARKERS_NAME, MARKER_COLUMNS),
        }

    # ── lifecycle ──
    async def start(self) -> None:
        """Start the collector and wait for its first sweep."""
        loop = asyncio.get_running_loop()

        def on_stdout(chunk: bytes) -> None:
            self._buf += chunk
            *lines, self._buf = self._buf.split(b"\n")
            for line in lines:
                if line.strip():
                    loop.call_soon_threadsafe(self._queue.put_nowait, line)

        def on_stderr(chunk: bytes) -> None:
            for line in chunk.decode("utf-8", "replace").splitlines():
                if line.strip():
                    self._stderr.append(line.strip())

        self.helper = await self.engine.start_helper(
            HelperSpec(
                image=self.image,
                command=["ae3gis-collect", "--interval", str(self.interval)],
                purpose="collector",
                job_id=self.job_id,
                owner=self.owner,
                lab_hash=self.scope.lab_hash or "",
                pid_host=True,
                cgroupns_host=True,
                binds={self.cgroup_root: "/host/cgroup"},
            )
        )
        self._pump = asyncio.ensure_future(self.helper.pump(on_stdout, on_stderr))
        self._pump.add_done_callback(lambda _f: loop.call_soon(self._queue.put_nowait, None))
        self._consumer = asyncio.ensure_future(self._consume())
        first = asyncio.ensure_future(self._first.wait())
        done, _ = await asyncio.wait(
            {first, self._consumer},
            timeout=FIRST_SWEEP_TIMEOUT_S,
            return_when=asyncio.FIRST_COMPLETED,
        )
        first.cancel()
        if not self._first.is_set():
            raise RuntimeError(f"The resource collector did not start: {self._why()}")

    def _why(self) -> str:
        return self.error or "; ".join(self._stderr) or "no output"

    def died(self) -> str | None:
        """Why the collector stopped on its own, or None while it runs."""
        if self._closed or self._consumer is None or not self._consumer.done():
            return None
        return self._why()

    def set_scope(self, scope: m.Scope) -> None:
        self.scope = scope
        self._refreshed = 0.0  # re-classify on the next sweep
        self._seen_ever = set()
        self._missing = set()

    def mark(self, source: str, text: str) -> None:
        if self._closed:
            return
        row = {
            "t": round(time.time() - self.t0, 3),
            "step": self.scope.step,
            "source": source,
            "text": text,
        }
        self.markers.append(row)
        self._files[MARKERS_NAME].write([row])
        self._files[MARKERS_NAME].flush()
        if self.channel is not None:
            self.channel.publish({"type": "marker", **row}, replay=False)

    async def stop(self) -> dict[str, Any]:
        """Stop the collector, finish the files; returns the summary."""
        if self.helper is not None:
            with contextlib.suppress(Exception):
                await self.helper.signal("SIGINT")
        if self._pump is not None:
            with contextlib.suppress(TimeoutError, asyncio.CancelledError, Exception):
                await asyncio.wait_for(asyncio.shield(self._pump), timeout=5.0)
        if self.helper is not None:
            with contextlib.suppress(Exception):
                await self.helper.remove()
        if self._consumer is not None:
            self._queue.put_nowait(None)
            with contextlib.suppress(TimeoutError, asyncio.CancelledError, Exception):
                await asyncio.wait_for(self._consumer, timeout=10.0)
        self._closed = True
        await asyncio.to_thread(self._close_files)
        return self.summary()

    def _close_files(self) -> None:
        for f in self._files.values():
            f.close(compress=self.compress)

    # ── processing ──
    async def _refresh(self) -> None:
        try:
            refs = await self.engine.list_containers()
        except Exception as exc:  # pragma: no cover - engine hiccup; keep the old map
            log.debug("Monitor could not list containers: %s", exc)
            return
        self._targets = m.classify(refs, self.scope)
        self._refreshed = time.monotonic()

    async def _consume(self) -> None:
        while True:
            line = await self._queue.get()
            if line is None:
                return
            sweep = m.parse_line(line)
            if sweep is None:
                with contextlib.suppress(ValueError, AttributeError):
                    self.error = json.loads(line).get("error") or self.error
                continue
            age = time.monotonic() - self._refreshed
            unknown = any(cid not in self._targets for cid in sweep.containers)
            if age > REFRESH_S or (unknown and age > UNKNOWN_REFRESH_S):
                await self._refresh()
            try:
                result = await asyncio.to_thread(self._record, sweep)
            except Exception as exc:  # pragma: no cover - never let one bad sweep stop the monitor
                log.warning("Monitor sweep failed: %s", exc)
                continue
            payload = self._payload(result)
            self.latest = payload
            self.ring.append(payload)
            if self.channel is not None:
                self.channel.publish(payload, replay=False)
            for cb in list(self.on_sweep):
                try:
                    cb(result, payload)
                except Exception as exc:  # pragma: no cover - a caller's bug
                    log.warning("Monitor callback failed: %s", exc)
            self._first.set()

    def _record(self, sweep: m.Sweep) -> m.SweepResult:
        scope = self.scope
        result = m.process(self._prev, sweep, self._targets, scope, self.t0)
        self._prev = sweep
        self.sweeps += 1
        step = scope.step
        hrow = host_csv_row(result.t, step, result.host, result.groups)
        self.host_rows.append(hrow)
        self._files[HOST_NAME].write([hrow])
        self._files[NODES_NAME].write([{"t": result.t, "step": step, **r} for r in result.nodes])
        self._files[IFACES_NAME].write([{"t": result.t, "step": step, **r} for r in result.ifaces])
        for f in self._files.values():
            f.flush()
        for row in result.nodes:
            if row["kind"] != "node":
                continue
            per = self._node_stats.setdefault(
                row["target"],
                {k: m.RunningStats() for k in ("cpu_pct", "mem_used", "rx_bps", "tx_bps")},
            )
            for k, rs in per.items():
                rs.add(row.get(k))
        for node in result.oom:
            self._oom[node] = self._oom.get(node, 0) + 1
        self._missing = (self._seen_ever - result.seen_nodes) | (self._missing - result.seen_nodes)
        self._seen_ever |= result.seen_nodes
        return result

    def _payload(self, r: m.SweepResult) -> dict[str, Any]:
        nodes = [row for row in r.nodes if row["kind"] == "node"]
        return {
            "type": "sweep",
            "t": r.t,
            "step": self.scope.step,
            "host": r.host,
            "groups": r.groups,
            "selection": m.selection_summary(r.nodes),
            "nodes": nodes if len(nodes) <= LIVE_NODE_LIMIT else None,
            "tools": [row for row in r.nodes if row["kind"] == "tool"],
            "oom": r.oom,
            "missing": sorted(self._missing),
        }

    # ── results ──
    def host_series(self, key: str, since: float = 0.0, until: float | None = None) -> list[float]:
        return [
            row[key]
            for row in self.host_rows
            if row.get(key) is not None
            and row["t"] >= since
            and (until is None or row["t"] <= until)
        ]

    def summary(self) -> dict[str, Any]:
        nodes = {
            node: {k: rs.to_dict() for k, rs in per.items()}
            for node, per in sorted(self._node_stats.items())
        }
        return {
            "duration_s": round(time.time() - self.t0, 3),
            "sweeps": self.sweeps,
            "interval_s": self.interval,
            "host": {k: m.series_summary(self.host_series(k)) for k in SUMMARY_HOST_FIELDS},
            "node_count": len(nodes),
            "nodes": nodes,
            "oom": dict(self._oom),
            "missing": sorted(self._missing),
            "error": self.error,
        }


# ── reading recorded samples ──────────────────────────────────────────


def _num(value: str) -> Any:
    if value == "":
        return None
    try:
        f = float(value)
    except ValueError:
        return value
    return int(f) if f.is_integer() and "." not in value else f


def read_csv(directory: Path, name: str) -> list[dict[str, Any]]:
    """Rows of a monitor CSV, live (plain) or finished (gzipped)."""
    plain, gz = directory / name, directory / f"{name}.gz"
    if plain.exists():
        text = plain.read_text()
    elif gz.exists():
        with gzip.open(gz, "rt") as fh:
            text = fh.read()
    else:
        return []
    return [
        {
            k: (
                _num(v)
                if k not in ("step", "target", "kind", "purpose", "iface", "source", "text")
                else v
            )
            for k, v in row.items()
        }
        for row in csv.DictReader(io.StringIO(text))
    ]


# ── starting (request side) ──────────────────────────────────────────


def start_monitor(db: Session, runner: JobRunner, topo: Topology, req: dict[str, Any]) -> Job:
    settings = runner.settings
    assert settings is not None
    with runner.admission:
        db.refresh(topo)
        if topo.status != "deployed" or not topo.engine_state:
            raise Conflict(
                "Deploy the topology before monitoring it", code="bad_state", status=topo.status
            )
        existing = jobs.active_for_subject(db, subject(topo.id))
        if existing is not None:
            raise Conflict(
                "A monitor is already running on this topology; stop it first",
                code="monitor_active",
                job_id=existing.id,
            )
        state = EngineState.from_dict(topo.engine_state)
        assert state is not None
        selector = req.get("nodes") or "all"
        try:
            monitored = selectors.resolve(topo.data, state.nodes, selector)
        except ValueError as exc:
            raise Invalid(str(exc), code="bad_selector") from exc
        if not monitored:
            raise Invalid("The selection matches no deployed node", code="no_nodes")
        duration = req.get("duration_s")
        params = {
            "label": req.get("label") or "",
            "notes": req.get("notes") or "",
            "selector": selector,
            "monitored": monitored,
            "interval_s": float(req.get("interval_s") or 1.0),
            "duration_s": min(duration, settings.monitor_max_seconds) if duration else None,
            # Activity badges: a monitor marks no node or link as busy.
            "node_ids": [],
            "connection_ids": [],
        }
        job = jobs.create_job(
            db, KIND, subject=subject(topo.id), topology_id=topo.id, params=params
        )
        events.record(
            db,
            type="monitor.requested",
            message=f"Monitor requested ({len(monitored)} node(s), every {params['interval_s']:g}s)",
            topology_id=topo.id,
            job_id=job.id,
        )
        db.commit()
    db.refresh(job)
    runner.submit(job.id)
    return job


# ── the job ───────────────────────────────────────────────────────────


def _load(runner: JobRunner, job_id: str) -> tuple[dict[str, Any], Topology, EngineState | None]:
    with runner.session_factory() as db:
        job = db.get(Job, job_id)
        topo = db.get(Topology, job.topology_id)
        db.expunge(topo)
        return dict(job.params or {}), topo, EngineState.from_dict(topo.engine_state)


def write_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(path)


def lean_result(summary: dict[str, Any], stopped_by: str | None, started: datetime) -> dict:
    """What goes on the job row: the host summary and the notable nodes (the
    per-node table stays in monitor.json)."""
    nodes = summary.get("nodes") or {}

    def top(metric: str, n: int = 5) -> list[list[Any]]:
        ranked = sorted(
            ((node, (v.get(metric) or {}).get("mean")) for node, v in nodes.items()),
            key=lambda x: x[1] or 0,
            reverse=True,
        )
        return [[node, value] for node, value in ranked[:n] if value is not None]

    return {
        "started_at": started.isoformat(),
        "ended_at": datetime.now(UTC).isoformat(),
        "duration_s": summary.get("duration_s"),
        "stopped_by": stopped_by,
        "sweeps": summary.get("sweeps"),
        "interval_s": summary.get("interval_s"),
        "node_count": summary.get("node_count"),
        "host": summary.get("host"),
        "top": {"cpu_pct": top("cpu_pct"), "mem_used": top("mem_used")},
        "oom": summary.get("oom"),
        "missing": summary.get("missing"),
        "error": summary.get("error"),
    }


async def run_monitor(runner: JobRunner, job_id: str) -> None:
    settings, store, hub = runner.settings, runner.artifacts, runner.live
    assert settings is not None and store is not None and hub is not None
    engine = runner.engine
    channel = hub.open(job_id, replay=0)
    params, topo, state = _load(runner, job_id)
    interval = float(params.get("interval_s") or 1.0)
    duration = params.get("duration_s")
    directory = store.dir(job_id, create=True)
    started = datetime.now(UTC)
    image = catalog.tool_image("collector")
    session: MonitorSession | None = None
    env: dict[str, Any] = {}
    stopped_by: str | None = None
    try:
        async with runner.step(job_id, "images"):
            assert runner.images is not None
            await runner.images.ensure_images(
                runner, job_id, [image], stale_event="monitor.images_stale", rebuild_stale=True
            )

        async with runner.step(job_id, "prepare", message=f"{len(params['monitored'])} node(s)"):
            if topo.status != "deployed" or state is None:
                raise RuntimeError("The topology is not deployed")
            scope = m.Scope(
                lab_hash=state.lab_hash,
                node_for_machine={mname: nid for nid, mname in state.nodes.items()},
                selected=set(params["monitored"]),
            )
            session = MonitorSession(
                engine,
                directory=directory,
                interval=interval,
                job_id=job_id,
                owner=settings.ensure_instance_id(),
                image=image,
                cgroup_root=settings.collector_cgroup_root,
                scope=scope,
                topology_id=topo.id,
                channel=channel,
            )
            _SESSIONS[job_id] = session
            await session.start()
            env = await environment.snapshot(
                engine,
                settings,
                topo,
                state,
                tool_ref=image,
                extra={"monitor": {"interval_s": interval, "nodes": len(params["monitored"])}},
            )
            write_json(
                directory / INFO_NAME,
                {"kind": KIND, "params": params, "environment": env, "started_at": started},
            )

        label = f"every {interval:g}s" + (f" for {duration}s" if duration else ", until stopped")
        async with runner.step(job_id, "run", message=label):
            stopped_by = await _wait(
                runner, job_id, session, duration, settings.monitor_max_seconds
            )
    finally:
        _SESSIONS.pop(job_id, None)
        summary = await session.stop() if session is not None else {}
        result = lean_result(summary, stopped_by, started) | {
            "environment_fingerprint": env.get("fingerprint")
        }
        with contextlib.suppress(Exception):
            runner.set_result(job_id, result)
        with contextlib.suppress(Exception):
            write_json(
                directory / INFO_NAME,
                {
                    "kind": KIND,
                    "params": params,
                    "environment": env,
                    "started_at": started,
                    "summary": summary,
                    "result": result,
                },
            )
        channel.close({"type": "end", "result": result})
        hub.prune()


async def _wait(
    runner: JobRunner, job_id: str, session: MonitorSession, duration: float | None, cap: float
) -> str:
    limit = duration or cap
    stop = runner.stop_event(job_id)
    t0 = time.monotonic()
    while True:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=1.0)
        if stop.is_set():
            return runner.stop_code(job_id) or "user"
        died = session.died()
        if died is not None:
            raise RuntimeError(f"The resource collector stopped: {died}")
        if time.monotonic() - t0 >= limit:
            return "completed" if duration else "limit:time"
        p = session.latest
        if p:
            h = p["host"]
            parts = [f"{p['selection']['count']} node(s)"]
            if h.get("vm_cpu_pct") is not None:
                parts.append(f"host CPU {h['vm_cpu_pct']:.0f}%")
            if h.get("mem_used_pct") is not None:
                parts.append(f"memory {h['mem_used_pct']:.0f}%")
            runner.progress(job_id, "run", " · ".join(parts), min_interval=5.0)


def register(runner: JobRunner) -> None:
    runner.register(KIND, run_monitor, cancellable=True, stoppable=True)
