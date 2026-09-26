"""Background traffic between deployed nodes (iperf3 for now), as a job.

Each flow runs a server sidecar in the target node's network namespace and a
client sidecar in the source node's, so traffic leaves from the client's IP
and follows the lab's real routes (through routers, firewalls…) whatever
images the nodes run. While a run lasts, nodes and sidecars are sampled for
CPU, memory and per-interface rates. Everything lands in the job's artifacts:

- ``flows.ndjson``: one line per iperf3 interval sample (see domain/traffic)
- ``nodes.ndjson``: one line per node/sidecar telemetry sample
- ``raw/<flow>-<client|server>.ndjson``: iperf3's own output, verbatim
- ``run.json``: the request, the environment (host, versions, images; see
  domain/environment) and, once done, the summary

Jobs: kind ``traffic``, subject ``traffic:<topology>`` (one run at a time per
topology, so runs don't skew each other), stoppable. Steps: ``images`` →
``prepare`` (servers listening, environment recorded) → ``run``.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

import catalog
from api.errors import Conflict, Invalid
from db.models import Job, Topology
from domain import telemetry
from domain.topology import find_container
from domain.traffic.iperf3 import DEFAULT_PORT, FlowSample, is_interrupt
from domain.traffic.summary import summarize_flow
from engine.base import EngineState, RawStats, SidecarSpec
from services import environment, events, jobs
from services.jobs import JobRunner
from services.traffic_generators import GENERATORS

log = logging.getLogger(__name__)

KIND = "traffic"
RUN_NAME = "run.json"
FLOWS_NAME = "flows.ndjson"
NODES_NAME = "nodes.ndjson"
READY_TIMEOUT_S = 8.0
END_GRACE_S = 15.0

# Recorders of running runs, by job id (live views start from their backlog).
_ACTIVE: dict[str, RunRecorder] = {}


def subject(topology_id: str) -> str:
    return f"traffic:{topology_id}"


def active_recorder(job_id: str) -> RunRecorder | None:
    return _ACTIVE.get(job_id)


class RunRecorder:
    """Appends a run's samples to its artifact files (safe from any thread)."""

    def __init__(self, directory: Path) -> None:
        self.dir = directory
        (directory / "raw").mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._flows = (directory / FLOWS_NAME).open("a")
        self._nodes = (directory / NODES_NAME).open("a")
        self._raw: dict[str, Any] = {}
        self.flow_samples: dict[str, list[dict[str, Any]]] = {}
        self.node_samples: list[dict[str, Any]] = []
        self.sidecars: dict[str, dict[str, str]] = {}  # name -> {flow_id, role, node_id}
        self.last: dict[str, dict[str, float]] = {}  # flow -> direction -> latest bps

    def flows(self, samples: list[dict[str, Any]]) -> None:
        with self._lock:
            for s in samples:
                self._flows.write(json.dumps(s) + "\n")
                self.flow_samples.setdefault(s["flow_id"], []).append(s)
                # The receiver's view wins over the sender's for the live number.
                last = self.last.setdefault(s["flow_id"], {})
                if s["side"] == "receiver" or s["direction"] not in last:
                    last[s["direction"]] = s["bps"]
            self._flows.flush()

    def nodes(self, samples: list[dict[str, Any]]) -> None:
        with self._lock:
            for s in samples:
                self._nodes.write(json.dumps(s) + "\n")
            self.node_samples.extend(samples)
            self._nodes.flush()

    def raw(self, flow_id: str, role: str, chunk: bytes) -> None:
        with self._lock:
            fh = self._raw.get(f"{flow_id}-{role}")
            if fh is None:
                fh = self._raw[f"{flow_id}-{role}"] = (
                    self.dir / "raw" / f"{flow_id}-{role}.ndjson"
                ).open("ab")
            fh.write(chunk)
            fh.flush()

    def backlog(self) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            return {
                "flows": [s for rows in self.flow_samples.values() for s in rows],
                "nodes": list(self.node_samples),
            }

    def close(self) -> None:
        with self._lock:
            for fh in (self._flows, self._nodes, *self._raw.values()):
                with contextlib.suppress(OSError):
                    fh.close()


def read_backlog(directory: Path) -> dict[str, list[dict[str, Any]]]:
    """A finished run's samples, from its files."""
    out: dict[str, list[dict[str, Any]]] = {"flows": [], "nodes": []}
    for key, name in (("flows", FLOWS_NAME), ("nodes", NODES_NAME)):
        path = directory / name
        if path.exists():
            for line in path.read_text().splitlines():
                with contextlib.suppress(ValueError):
                    out[key].append(json.loads(line))
    return out


# ── starting (request side) ──────────────────────────────────────────


def _node_ip(data: dict[str, Any], node_id: str) -> str | None:
    c = find_container(data or {}, node_id)
    ip = (c or {}).get("ip")
    return str(ip).strip() if ip else None


def start_run(db: Session, runner: JobRunner, topo: Topology, req: dict[str, Any]) -> Job:
    settings = runner.settings
    assert settings is not None
    with runner.admission:
        db.refresh(topo)
        if topo.status != "deployed" or not topo.engine_state:
            raise Conflict(
                "Deploy the topology before generating traffic",
                code="bad_state",
                status=topo.status,
            )
        existing = jobs.active_for_subject(db, subject(topo.id))
        if existing is not None:
            raise Conflict(
                "A traffic run is already active on this topology; stop it first",
                code="traffic_active",
                job_id=existing.id,
            )
        state = EngineState.from_dict(topo.engine_state)
        assert state is not None
        flows = []
        ids: set[str] = set()
        for f in req["flows"]:
            if f["id"] in ids:
                raise Invalid(f"Flow id {f['id']!r} is used twice", code="duplicate_flow")
            ids.add(f["id"])
            for end in ("client", "server"):
                if f[end] not in state.nodes:
                    raise Invalid(
                        f"{end.capitalize()} {f[end]!r} of flow {f['id']!r} is not deployed",
                        code="node_not_deployed",
                    )
            if f["client"] == f["server"]:
                raise Invalid(f"Flow {f['id']!r} sends to itself", code="same_node")
            server_ip = f.get("server_address") or _node_ip(topo.data, f["server"])
            if not server_ip:
                raise Invalid(
                    f"{f['server']!r} has no IP address to send to; set server_address",
                    code="no_address",
                )
            flows.append({**f, "server_address": str(server_ip)})
        node_ids = list(dict.fromkeys(n for f in flows for n in (f["client"], f["server"])))
        monitor = req.get("monitor_nodes") or "all"
        if monitor == "all":
            monitored = list(state.nodes)
        elif monitor == "flows":
            monitored = node_ids
        else:
            monitored = [n for n in monitor if n in state.nodes]
        duration = req.get("duration_s")
        params = {
            "label": req.get("label") or "",
            "notes": req.get("notes") or "",
            "flows": flows,
            "duration_s": min(duration, settings.traffic_max_seconds) if duration else None,
            "interval_s": req.get("interval_s") or 1.0,
            "monitored": monitored,
            "node_ids": node_ids,
            "connection_ids": [],
        }
        job = jobs.create_job(
            db, KIND, subject=subject(topo.id), topology_id=topo.id, params=params
        )
        events.record(
            db,
            type="traffic.requested",
            message=f"Traffic run requested ({len(flows)} flow(s))",
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


def _write_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(path)


class _FlowRun:
    """One flow's two ends while the run lasts."""

    def __init__(self, flow: dict[str, Any], port: int) -> None:
        self.flow = flow
        self.id: str = flow["id"]
        self.port = port
        self.generator = GENERATORS[flow.get("generator") or "iperf3"]
        self.server = None
        self.client = None
        self.server_pump: asyncio.Future | None = None
        self.client_pump: asyncio.Future | None = None
        self.server_parser = self.generator.parser(self.id, "server", 0.0)
        self.client_parser = self.generator.parser(self.id, "client", 0.0)

    def errors(self) -> list[str]:
        return [
            e for e in self.client_parser.errors + self.server_parser.errors if not is_interrupt(e)
        ]


def _on_output(recorder: RunRecorder, channel, flow_id: str, role: str, parser):
    def feed(chunk: bytes) -> None:
        recorder.raw(flow_id, role, chunk)
        samples: list[FlowSample] = [s for e in parser.feed(chunk) for s in e.samples]
        if samples:
            rows = [s.to_dict() for s in samples]
            recorder.flows(rows)
            channel.publish_threadsafe({"type": "flow", "samples": rows}, replay=False)

    return feed


def _ignore(_chunk: bytes) -> None:
    pass


async def run_traffic(runner: JobRunner, job_id: str) -> None:
    settings, store, hub = runner.settings, runner.artifacts, runner.live
    assert settings is not None and store is not None and hub is not None
    engine = runner.engine
    channel = hub.open(job_id, replay=0)
    params, topo, state = _load(runner, job_id)
    interval = float(params.get("interval_s") or 1.0)
    duration = params.get("duration_s")
    run_dir = store.dir(job_id, create=True)
    recorder = RunRecorder(run_dir)
    _ACTIVE[job_id] = recorder
    flows = [_FlowRun(f, DEFAULT_PORT + i) for i, f in enumerate(params["flows"])]
    started = datetime.now(UTC)
    t0 = time.monotonic()
    env: dict[str, Any] = {}
    stopped_by: str | None = None
    telemetry_task: asyncio.Task | None = None
    try:
        async with runner.step(job_id, "images"):
            refs = list(dict.fromkeys(catalog.tool_image(fr.generator.tool_role) for fr in flows))
            assert runner.images is not None
            await runner.images.ensure_images(
                runner, job_id, refs, stale_event="traffic.images_stale"
            )

        async with runner.step(job_id, "prepare", message=f"{len(flows)} flow(s)"):
            if topo.status != "deployed" or state is None:
                raise RuntimeError("The topology is not deployed")
            owner = settings.ensure_instance_id()
            for fr in flows:
                image = catalog.tool_image(fr.generator.tool_role)
                fr.server = await engine.start_sidecar(
                    state,
                    SidecarSpec(
                        node_id=fr.flow["server"],
                        image=image,
                        command=fr.generator.server_argv(fr.flow, fr.port, interval),
                        purpose="iperf-server",
                        job_id=job_id,
                        owner=owner,
                    ),
                )
                recorder.sidecars[fr.server.name] = {
                    "flow_id": fr.id,
                    "role": "server",
                    "node_id": fr.flow["server"],
                }
                fr.server_pump = asyncio.ensure_future(
                    fr.server.pump(
                        _on_output(recorder, channel, fr.id, "server", fr.server_parser), _ignore
                    )
                )
                await _wait_listening(fr, READY_TIMEOUT_S)
                runner.progress(job_id, "prepare", f"{fr.id}: server listening on {fr.port}")
            versions = {}
            with contextlib.suppress(Exception):
                _, text = await flows[0].server.exec(["iperf3", "--version"])
                versions["iperf3"] = text.splitlines()[0].strip() if text else ""
            with runner.session_factory() as db:
                captures = [
                    {"job_id": j.id, "label": (j.params or {}).get("label")}
                    for j in jobs.active_jobs(db, topo.id, kinds=("capture",))
                ]
            env = await environment.snapshot(
                engine,
                settings,
                topo,
                state,
                tool_ref=refs[0],
                tool_versions=versions,
                extra={
                    "sampling": {"interval_s": interval, "monitored": params.get("monitored")},
                    "concurrent_captures": captures,
                },
            )
            _write_json(
                run_dir / RUN_NAME,
                {"kind": KIND, "params": params, "environment": env, "started_at": started},
            )
            channel.publish({"type": "sidecars", "items": recorder.sidecars}, replay=False)

        label = f"{len(flows)} flow(s)" + (f", {duration}s" if duration else ", until stopped")
        async with runner.step(job_id, "run", message=label):
            offset = time.monotonic() - t0
            for fr in flows:
                fr.server_parser.offset = fr.client_parser.offset = offset
                fr.client = await engine.start_sidecar(
                    state,
                    SidecarSpec(
                        node_id=fr.flow["client"],
                        image=catalog.tool_image(fr.generator.tool_role),
                        command=fr.generator.client_argv(
                            {**fr.flow, "duration_s": duration or 0},
                            fr.flow["server_address"],
                            fr.port,
                            interval,
                        ),
                        purpose="iperf-client",
                        job_id=job_id,
                        owner=settings.ensure_instance_id(),
                    ),
                )
                recorder.sidecars[fr.client.name] = {
                    "flow_id": fr.id,
                    "role": "client",
                    "node_id": fr.flow["client"],
                }
                fr.client_pump = asyncio.ensure_future(
                    fr.client.pump(
                        _on_output(recorder, channel, fr.id, "client", fr.client_parser), _ignore
                    )
                )
            channel.publish({"type": "sidecars", "items": recorder.sidecars}, replay=False)
            telemetry_task = asyncio.ensure_future(
                _telemetry(
                    engine, state, params.get("monitored") or [], recorder, channel, t0, interval
                )
            )
            stopped_by = await _wait_run(
                runner, job_id, flows, recorder, channel, t0, duration, settings
            )
            await _wind_down(flows)
            errors = [e for fr in flows for e in fr.errors()]
            if errors and all(fr.errors() for fr in flows):
                raise RuntimeError(errors[0])
    finally:
        if telemetry_task is not None:
            telemetry_task.cancel()
            with contextlib.suppress(BaseException):
                await telemetry_task
        for fr in flows:
            for sc in (fr.client, fr.server):
                if sc is not None:
                    with contextlib.suppress(Exception):
                        await sc.remove()
            for pump in (fr.client_pump, fr.server_pump):
                if pump is not None and not pump.done():
                    pump.cancel()
        with contextlib.suppress(Exception):
            await engine.remove_sidecars(job_id=job_id)
        result = _result(params, flows, recorder, started, stopped_by, env)
        _ACTIVE.pop(job_id, None)
        recorder.close()
        with contextlib.suppress(Exception):
            runner.set_result(job_id, result)
        with contextlib.suppress(Exception):
            _write_json(
                run_dir / RUN_NAME,
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


async def _wait_listening(fr: _FlowRun, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if fr.server_pump is not None and fr.server_pump.done():
            break
        with contextlib.suppress(Exception):
            _, out = await fr.server.exec(["ss", "-Hltn", f"sport = :{fr.port}"])
            if fr.generator.listening(out, fr.port):
                return
        await asyncio.sleep(0.2)
    raise RuntimeError(
        f"The traffic server for flow {fr.id!r} on {fr.flow['server']} did not start listening"
    )


async def _wait_run(runner, job_id, flows, recorder, channel, t0, duration, settings) -> str:
    """Until the clients finish, a stop, or the deadline; returns why it ended."""
    limit = (duration + END_GRACE_S) if duration else settings.traffic_max_seconds
    stop = asyncio.ensure_future(runner.stop_event(job_id).wait())
    try:
        while True:
            pending = [
                fr.client_pump for fr in flows if fr.client_pump and not fr.client_pump.done()
            ]
            if not pending:
                return "completed"
            done, _ = await asyncio.wait(
                {*pending, stop}, timeout=1.0, return_when=asyncio.FIRST_COMPLETED
            )
            elapsed = time.monotonic() - t0
            channel.publish(
                {"type": "status", "elapsed": round(elapsed, 1), "flows": recorder.last},
                replay=False,
            )
            parts = [
                f"{fid} {bps.get('fwd', bps.get('rev', 0)) / 1e6:.1f} Mb/s"
                for fid, bps in recorder.last.items()
            ]
            runner.progress(job_id, "run", " · ".join(parts) or "Starting flows", min_interval=2.0)
            if stop in done:
                return runner.stop_code(job_id) or "user"
            if elapsed >= limit:
                return "limit:time"
    finally:
        stop.cancel()


async def _wind_down(flows: list[_FlowRun]) -> None:
    """SIGINT clients still running (iperf3 then prints its end), then let the
    servers (``-s -1``) exit on their own; remove whatever doesn't."""
    for fr in flows:
        if fr.client_pump and not fr.client_pump.done():
            await fr.client.signal("SIGINT")
    for attr, sig_first in (("client", False), ("server", True)):
        pumps = [
            (fr, getattr(fr, f"{attr}_pump"))
            for fr in flows
            if getattr(fr, f"{attr}_pump") is not None
        ]
        waiting = [p for _, p in pumps if not p.done()]
        if waiting:
            _, still = await asyncio.wait(waiting, timeout=10.0)
            if still and sig_first:
                for fr, p in pumps:
                    if p in still:
                        await getattr(fr, attr).signal("SIGINT")
                _, still = await asyncio.wait(still, timeout=3.0)
            for fr, p in pumps:
                if p in still:
                    await getattr(fr, attr).remove()


async def _telemetry(engine, state, monitored, recorder, channel, t0, interval) -> None:
    prev: dict[str, RawStats] = {}
    while True:
        try:
            raws = await engine.sample_stats(state, monitored, list(recorder.sidecars))
        except Exception as exc:  # pragma: no cover - engine hiccup; keep sampling
            log.debug("Telemetry sample failed: %s", exc)
            raws = []
        t = time.monotonic() - t0
        samples = [telemetry.rates(prev.get(r.target), r, t) for r in raws]
        prev = {r.target: r for r in raws}
        if samples:
            recorder.nodes(samples)
            channel.publish({"type": "nodes", "samples": samples}, replay=False)
        await asyncio.sleep(interval)


def _result(params, flows, recorder, started, stopped_by, env) -> dict[str, Any]:
    ended = datetime.now(UTC)
    out_flows = []
    for fr in flows:
        f = fr.flow
        out_flows.append(
            {
                "id": fr.id,
                "generator": fr.generator.name,
                "client": f["client"],
                "server": f["server"],
                "server_address": f.get("server_address"),
                "protocol": f.get("protocol") or "tcp",
                "direction": f.get("direction") or "forward",
                "port": fr.port,
                "summary": summarize_flow(recorder.flow_samples.get(fr.id, [])),
                "errors": fr.errors(),
            }
        )
    return {
        "label": params.get("label") or "",
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_s": round((ended - started).total_seconds(), 3),
        "stopped_by": stopped_by,
        "flows": out_flows,
        "sidecars": recorder.sidecars,
        "environment_fingerprint": env.get("fingerprint"),
    }


def register(runner: JobRunner) -> None:
    runner.register(KIND, run_traffic, cancellable=True, stoppable=True)
