"""Scale benchmarks: deploy, measure, load, destroy, at growing scale, as a job.

A benchmark sweeps a topology through ``scale`` steps (generated topologies
of N hosts, see ``domain/generator``; or one existing topology, repeated),
each ``repetitions`` times, and stops at the first step that fails a stop
criterion. One monitor session (``services/monitor``) records the host and
every container for the whole sweep; each step marks its windows on that
timeline and runs, in order:

1. ``pre``: once host CPU is under ``quiet_cpu_pct`` again (the previous
   step's teardown drains after its destroy job), ``cooldown_s`` with nothing
   of ours deployed (the reference)
2. deploy, through the ordinary deploy job (its steps time the phases)
3. network ready: every host pings its gateway and a far address, through
   the netns driver (``services/netns_driver.probe``)
4. ``settle``: ``settle_s`` deployed, idle
5. ``hold``: ``hold_s`` under the step's traffic (``services/traffic``), or idle
6. destroy, through the ordinary destroy job

Stop criteria (``domain/benchmark.Watch``, per sweep while a step runs): host
memory over ``max_mem_pct`` or memory stalls over ``max_psi_mem_full`` for 3
sweeps, a node OOM-killed or gone, the collector falling behind its interval;
and per step: a failed, partial or slow deploy, hosts not reachable in time,
traffic that did not get through. The step's lab is destroyed before the sweep
ends, so a benchmark never leaves anything running (``keep_last`` keeps the
last one for inspection).

Jobs: kind ``benchmark``, subject ``benchmark`` (one at a time: a benchmark
owns the host), cancellable (clean up now) and stoppable (finish the step).
The benchmark's topology is one library row reused by every step (its deploy
and destroy jobs stay attached to it).

Artifacts (``data/artifacts/<job>/``): ``benchmark.json`` (spec, environment,
rows, outcome), ``results.csv`` (a row per step), ``report.md``, the monitor's
``host.csv`` / ``nodes.csv`` / ``ifaces.csv`` / ``markers.csv`` (with a
``step`` column), ``topologies/<step>.json``, and per traffic step
``traffic/<step>/`` (the run's ``run.json`` and ``totals.ndjson``).
"""

from __future__ import annotations

import asyncio
import contextlib
import csv
import io
import json
import logging
import re
import shutil
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import catalog
from api.errors import Conflict, Invalid
from db.models import Event, Job, Topology
from domain import benchmark as bm
from domain import monitor as m
from domain import selectors
from domain.generator import (
    GeneratorError,
    GeneratorParams,
    check,
    check_catalog,
    counts,
    generate,
    kinds_used,
    max_hosts,
)
from domain.topology import images_in
from engine.base import EngineState
from services import deployment, environment, events, jobs, netns_driver, topologies, traffic
from services import monitor as monitor_service
from services.jobs import JobRunner

log = logging.getLogger(__name__)

KIND = "benchmark"
SUBJECT = "benchmark"
INFO_NAME = "benchmark.json"
RESULTS_NAME = "results.csv"
REPORT_NAME = "report.md"
# Jobs that do not make the host busy (they don't load it for long).
QUIET_KINDS = ("build", "sync_source")


def list_benchmarks(db: Session, limit: int = 50) -> list[Job]:
    return list(
        db.scalars(select(Job).where(Job.kind == KIND).order_by(Job.created_at.desc()).limit(limit))
    )


# ── starting (request side) ──────────────────────────────────────────


def _gen_params(spec: dict[str, Any], hosts: int) -> GeneratorParams:
    g = dict((spec.get("topology") or {}).get("generate") or {})
    g.pop("hosts", None)
    return GeneratorParams(hosts=hosts, **g)


def start_benchmark(db: Session, runner: JobRunner, spec: dict[str, Any]) -> Job:
    with runner.admission:
        existing = jobs.active_for_subject(db, SUBJECT)
        if existing is not None:
            raise Conflict(
                "A benchmark is already running; stop it first",
                code="benchmark_active",
                job_id=existing.id,
            )
        topo_spec = spec.get("topology") or {}
        label = spec.get("label") or "benchmark"
        extra: dict[str, Any] = {}
        if topo_spec.get("topology_id") and spec.get("adaptive"):
            raise Invalid("An adaptive benchmark needs a generated topology", code="bad_adaptive")
        if topo_spec.get("topology_id"):
            topo = topologies.get_or_404(db, topo_spec["topology_id"])
            if topo.status != "idle" or jobs.active_job(db, topo.id):
                raise Conflict(
                    "The topology must be idle (not deployed) to benchmark it",
                    code="bad_state",
                    status=topo.status,
                )
            generated = False
            scale = [len(selectors.node_index(topo.data))]
        else:
            adaptive = spec.get("adaptive")
            scale = list(spec.get("scale") or [])
            if adaptive:
                scale = []
            elif not scale:
                raise Invalid("A generated benchmark needs a scale list", code="no_scale")
            first = int(adaptive["start"]) if adaptive else scale[0]
            try:
                for hosts in [first] if adaptive else [min(scale), max(scale)]:
                    check(_gen_params(spec, hosts))
                check_catalog(_gen_params(spec, first), catalog.node_types())
            except (GeneratorError, TypeError) as exc:
                raise Invalid(str(exc), code="bad_generator") from exc
            if adaptive:
                # The largest topology the generator makes with these params.
                extra["max_scale"] = max_hosts(_gen_params(spec, first))
            topo, _ = topologies.create(
                db, name=f"bench: {label}", data=generate(_gen_params(spec, first))
            )
            generated = True
        params = {
            **spec,
            **extra,
            "scale": scale,
            "topology_id": topo.id,
            "generated": generated,
        }
        job = jobs.create_job(db, KIND, subject=SUBJECT, params=params)
        events.record(
            db,
            type="benchmark.requested",
            message=f"Benchmark '{label}' requested ({len(scale)} step(s) × "
            f"{spec.get('repetitions', 1)})",
            topology_id=topo.id,
            job_id=job.id,
        )
        db.commit()
    db.refresh(job)
    runner.submit(job.id)
    return job


# ── the job ───────────────────────────────────────────────────────────


class Tripped(Exception):
    """A stop criterion fired."""


class Bench:
    """What a running benchmark knows between steps."""

    def __init__(self, runner: JobRunner, job_id: str, spec: dict[str, Any]) -> None:
        self.runner = runner
        self.job_id = job_id
        self.spec = spec
        self.stop = spec.get("stop") or {}
        self.interval = float((spec.get("monitor") or {}).get("interval_s") or 5.0)
        self.watch = bm.Watch(self.stop, self.interval)
        self.session: monitor_service.MonitorSession | None = None
        self.rows: list[dict[str, Any]] = []
        self.agg: list[dict[str, Any]] = []
        # The current step's node id → image, and per-sweep per-image numbers.
        self.image_of: dict[str, str] = {}
        self.by_image: list[dict[str, Any]] = []
        # How an adaptive sweep's climb ended.
        self.limit: str | None = None
        # The host at rest before the first step (``rest_s``).
        self.rest: dict[str, Any] | None = None
        self.armed = False
        self.trip: tuple[str, str] | None = None
        self.tripped = asyncio.Event()
        self.phase = "starting"
        self.is_last = False  # the sweep's last step (keep_last keeps its lab)

    # The monitor calls this on every sweep (on the loop).
    def on_sweep(self, result: m.SweepResult, payload: dict[str, Any]) -> None:
        sel = payload.get("selection") or {}
        self.agg.append(
            {
                "t": result.t,
                "count": result.groups["node"]["count"],
                "cpu_mean": (sel.get("cpu_pct") or {}).get("mean"),
                "cpu_p95": (sel.get("cpu_pct") or {}).get("p95"),
                "mem_mean": (sel.get("mem_used") or {}).get("mean"),
                "mem_p95": (sel.get("mem_used") or {}).get("p95"),
                "rx_sum": (sel.get("rx_bps") or {}).get("sum"),
            }
        )
        if self.image_of:
            self.by_image += bm.image_sweep(result.t, result.nodes, self.image_of)
        if self.armed and self.trip is None:
            hit = self.watch.check(result.host, payload)
            if hit is not None:
                self.trip = hit
                self.tripped.set()
                self.mark(f"stop criterion: {hit[1]}")

    def now(self) -> float:
        assert self.session is not None
        return round(time.time() - self.session.t0, 3)

    def mark(self, text: str) -> None:
        if self.session is not None:
            self.session.mark("benchmark", text)

    def progress(self, step: str, text: str) -> None:
        self.phase = text
        self.runner.progress(self.job_id, step, text)

    async def quiet(self, cpu_pct: float, timeout_s: float) -> float:
        """Wait until the host is quiet (VM CPU under ``cpu_pct`` for
        ``bm.SUSTAINED`` sweeps in a row) or ``timeout_s`` passes; returns the
        seconds waited. Docker keeps tearing down the previous step's lab
        (networks, shims) after its destroy job ends, which would skew the
        next reference."""
        assert self.session is not None
        start = time.monotonic()
        since = self.now()
        while time.monotonic() - start < timeout_s:
            recent = [
                r["vm_cpu_pct"]
                for r in self.session.host_rows
                if r["t"] > since and r.get("vm_cpu_pct") is not None
            ][-bm.SUSTAINED :]
            if len(recent) == bm.SUSTAINED and max(recent) < cpu_pct:
                break
            await asyncio.sleep(min(self.interval, 0.25))
        return round(time.monotonic() - start, 1)

    async def pause(self, seconds: float) -> bool:
        """Wait ``seconds`` unless a criterion trips first; True if it tripped."""
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self.tripped.wait(), timeout=max(seconds, 0))
        return self.tripped.is_set()

    def arm(self) -> None:
        self.watch.reset()
        self.trip = None
        self.tripped.clear()
        self.armed = True


def _topo(runner: JobRunner, topology_id: str) -> Topology:
    with runner.session_factory() as db:
        topo = db.get(Topology, topology_id)
        if topo is None:
            raise RuntimeError("The benchmark's topology was deleted")
        db.expunge(topo)
        return topo


async def _run_job(runner: JobRunner, start) -> Job:
    """Start a job with ``start(db)`` and wait for it to end."""
    with runner.session_factory() as db:
        job = start(db)
        job_id = job.id
    final = await runner.wait(job_id)
    assert final is not None
    return final


def _elapsed(job: Job) -> float | None:
    if job.started_at and job.finished_at:
        return round((job.finished_at - job.started_at).total_seconds(), 3)
    return None


async def _destroy(runner: JobRunner, topology_id: str) -> Job | None:
    """Destroy the topology's lab if there is one (waiting out a running deploy)."""
    with runner.session_factory() as db:
        active = jobs.active_job(db, topology_id)
    if active is not None:
        await runner.wait(active.id)
    topo = _topo(runner, topology_id)
    if topo.status not in ("deployed", "error") or not topo.engine_state:
        return None

    def start(db: Session) -> Job:
        t = db.get(Topology, topology_id)
        return deployment.start_destroy(db, runner, t)

    return await _run_job(runner, start)


async def _stop_traffic(runner: JobRunner, topology_id: str) -> Job | None:
    with runner.session_factory() as db:
        run = jobs.active_for_subject(db, traffic.subject(topology_id))
    if run is None:
        return None
    if not runner.request_stop(run.id, "Stopping: the benchmark step ends", code="benchmark"):
        runner.cancel(run.id, "Cancelled: the benchmark step ends")
    return await runner.wait(run.id)


def readiness_probes(data: dict[str, Any], pids: dict[str, int]) -> list[dict[str, Any]]:
    """Every host pings its gateway and a far address: the first host (in
    topology order) of another subnet, so routing is exercised too."""
    index = selectors.node_index(data)
    gateways: dict[str, str] = {}
    first_host: dict[str, str] = {}
    for site in data.get("sites") or []:
        for sub in site.get("subnets") or []:
            if sub.get("gateway"):
                gateways[sub["id"]] = sub["gateway"]
    for nid, info in index.items():
        if info["role"] == "host" and info["ip"]:
            first_host.setdefault(info["subnets"][0], nid)
    probes = []
    for nid, info in index.items():
        if info["role"] != "host" or nid not in pids:
            continue
        home = info["subnets"][0]
        targets = []
        if gateways.get(home):
            targets.append(gateways[home])
        far = next((h for s, h in first_host.items() if s != home), None)
        if far and index[far]["ip"]:
            targets.append(index[far]["ip"])
        probes += [{"node": nid, "pid": pids[nid], "target": t} for t in targets]
    return probes


Window = tuple[float, float] | None


def _fail(row: dict[str, Any], outcome: str, reason: str, detail: str) -> None:
    """Record a step's outcome; the first one that isn't ``ok`` sticks."""
    if row["outcome"] == "ok":
        row.update(outcome=outcome, reason=reason, detail=detail)


def _place(b: Bench, row: dict[str, Any], data: dict[str, Any] | None, artifact: str) -> Topology:
    """Put the step's topology (``data``; None keeps the stored one) on the
    benchmark's library row, keep a copy as ``topologies/<artifact>.json``,
    and note its size and images."""
    runner, topology_id = b.runner, b.spec["topology_id"]
    if data is not None:
        with runner.session_factory() as db:
            topologies.update(db, db.get(Topology, topology_id), data=data)
        store = runner.artifacts
        assert store is not None
        tdir = store.dir(b.job_id) / "topologies"
        tdir.mkdir(exist_ok=True)
        (tdir / f"{artifact}.json").write_text(json.dumps(data))
    topo = _topo(runner, topology_id)
    plan = topologies.plan_for(topo)
    row["nodes"] = len(plan.nodes)
    row["links"] = len(plan.collision_domains)
    row["composition"] = bm.composition((n.type, n.image) for n in plan.nodes)
    b.image_of = {n.id: n.image for n in plan.nodes}
    b.by_image = []
    return topo


async def _reference(b: Bench, row: dict[str, Any], name: str) -> Window:
    """The reference window: nothing of ours deployed, once the host is quiet."""
    spec = b.spec
    assert b.session is not None
    b.session.set_scope(m.Scope(step=name))
    b.progress(name, "waiting for the host to go quiet")
    row["quiet_wait_s"] = await b.quiet(
        float(spec.get("quiet_cpu_pct") or 10), float(spec.get("quiet_timeout_s") or 300)
    )
    b.progress(name, f"reference ({spec.get('cooldown_s', 20)}s, nothing deployed)")
    t0 = b.now()
    await asyncio.sleep(float(spec.get("cooldown_s") or 0))
    return (t0, b.now())


async def _deploy(b: Bench, row: dict[str, Any], name: str) -> EngineState | None:
    """Deploy the step's topology (arming the stop criteria); its engine state,
    or None when it was not deployed (projected to exhaust the host, refused,
    failed or partial). A slow deploy is marked but goes on."""
    runner, topology_id = b.runner, b.spec["topology_id"]
    assert b.session is not None
    # Would this step exhaust the host? (A deploy cannot be interrupted.)
    latest = b.session.host_rows[-1] if b.session.host_rows else None
    projected = bm.projected_memory(b.rows, latest, row["nodes"], b.stop)
    if projected is not None:
        _fail(row, "stopped", *projected)
        b.mark(f"{name}: not deployed ({projected[1]})")
        return None
    b.arm()
    b.mark(f"{name}: deploy ({row['nodes']} nodes, {row['links']} links)")
    b.progress(name, f"deploying {row['nodes']} nodes")
    try:
        deploy = await _run_job(
            runner,
            lambda db: deployment.start_deploy(db, runner, db.get(Topology, topology_id)),
        )
    except (Conflict, Invalid) as exc:  # e.g. the topology does not validate
        _fail(row, "failed", "deploy_refused", str(exc))
        return None
    row["deploy_job"] = deploy.id
    row["deploy_s"] = _elapsed(deploy)
    row["deploy_phases"] = bm.deploy_phases(deploy.steps or [])
    if deploy.status != "succeeded":
        _fail(row, "failed", "deploy_failed", deploy.error or deploy.status)
        return None
    with runner.session_factory() as db:
        partial = db.scalars(
            select(Event).where(Event.job_id == deploy.id, Event.type == "deploy.partial")
        ).first()
    if partial is not None:
        _fail(row, "failed", "deploy_partial", partial.message)
        return None
    if row["deploy_s"] and row["deploy_s"] > float(b.stop.get("deploy_timeout_s") or 1e9):
        _fail(row, "stopped", "deploy_slow", f"deploy took {row['deploy_s']:.0f}s")
    state = EngineState.from_dict(_topo(runner, topology_id).engine_state)
    assert state is not None
    b.session.set_scope(
        m.Scope(
            lab_hash=state.lab_hash,
            node_for_machine={mn: nid for nid, mn in state.nodes.items()},
            step=name,
        )
    )
    b.mark(f"{name}: deployed in {row['deploy_s']}s")
    return state


async def _ready(
    b: Bench, row: dict[str, Any], name: str, data: dict[str, Any], state: EngineState
) -> bool:
    """Network ready: every host reaches its gateway and a far host in time.
    True when the step can go on."""
    runner = b.runner
    settings = runner.settings
    assert settings is not None
    pids = await runner.engine.node_pids(state)
    probes = readiness_probes(data, pids)
    b.progress(name, f"checking {len(probes)} paths")
    ready = await netns_driver.probe(
        runner.engine,
        settings,
        image=catalog.tool_image("driver"),
        job_id=b.job_id,
        owner=settings.ensure_instance_id(),
        lab_hash=state.lab_hash,
        probes=probes,
        timeout_s=float(b.stop.get("ready_timeout_s") or 300),
    )
    ok_t = [r["t"] for r in ready["results"] if r.get("ok")]
    row["ready_s"] = max(ok_t) if ok_t else None
    row["probes"] = len(probes)
    row["probes_failed"] = ready["failed"]
    if ready.get("error"):
        _fail(row, "failed", "probe_error", ready["error"])
    elif ready["failed"]:
        bad = sorted({r["node"] for r in ready["results"] if not r.get("ok")})
        _fail(
            row,
            "failed",
            "not_ready",
            f"{ready['failed']} path(s) unreachable from {', '.join(bad[:5])}",
        )
    b.mark(f"{name}: network ready in {row['ready_s']}s")
    return row["outcome"] == "ok"


async def _settle(b: Bench, name: str) -> Window:
    """Deployed and idle for ``settle_s``; raises Tripped."""
    b.progress(name, f"settling ({b.spec.get('settle_s', 20)}s)")
    t1 = b.now()
    if await b.pause(float(b.spec.get("settle_s") or 0)):
        raise Tripped
    return (t1, b.now())


async def _hold(
    b: Bench,
    row: dict[str, Any],
    name: str,
    windows: dict[str, Window],
    hold_s: float,
    load: dict[str, Any] | None,
) -> None:
    """``hold_s`` idle, or under ``load`` (``patterns``, ``interval_s``,
    ``ramp_s``: one traffic run, its ramp left out of the window). Sets
    ``windows["hold"]``, then raises Tripped if a criterion fired."""
    runner, topology_id = b.runner, b.spec["topology_id"]
    t2 = b.now()
    if not load:
        b.progress(name, f"holding idle ({hold_s:g}s)")
        tripped = await b.pause(hold_s)
        windows["hold"] = (t2, b.now())
        if tripped:
            raise Tripped
        return
    b.progress(name, "starting traffic")
    with runner.session_factory() as db:
        run = traffic.start_run(
            db,
            runner,
            db.get(Topology, topology_id),
            {
                "label": f"benchmark {name}",
                "patterns": load.get("patterns") or [],
                "flows": [],
                "duration_s": None,
                "interval_s": load.get("interval_s") or b.interval,
                "ramp_s": load.get("ramp_s") or 0.0,
            },
        )
        row["traffic_job"] = run.id
    ramp = float(load.get("ramp_s") or 0.0)
    b.progress(name, f"traffic: ramp {ramp:.0f}s + hold {hold_s:g}s")
    tripped = await b.pause(ramp)
    t2 = b.now()
    if not tripped:
        tripped = await b.pause(hold_s)
    windows["hold"] = (t2, b.now())
    done = await _stop_traffic(runner, topology_id)
    totals = ((done.result or {}) if done else {}).get("totals") or {}
    row.update({k: totals.get(k) for k in bm.TRAFFIC_ROW_KEYS})
    _keep_traffic(b, row["traffic_job"], load.get("slug") or str(row["step"]))
    if done is not None and done.status == "failed":
        _fail(row, "failed", "traffic_failed", done.error or "the traffic run failed")
    if tripped:
        raise Tripped
    verdict = bm.traffic_verdict(totals, b.stop)
    if verdict:
        _fail(row, "degraded", *verdict)


def _keep_traffic(b: Bench, run_id: str, slug: str) -> None:
    """Copy a step's traffic run summary (``run.json``: every flow's summary;
    ``totals.ndjson``: what arrived per interval; ``flows.ndjson`` too with
    ``keep_samples``) into ``traffic/<slug>/``, so the benchmark's export
    holds its network results."""
    store = b.runner.artifacts
    assert store is not None
    names = [traffic.RUN_NAME, traffic.TOTALS_NAME]
    if b.spec.get("keep_samples"):
        names.append(traffic.FLOWS_NAME)
    dest = store.dir(b.job_id) / "traffic" / _slug(slug)
    for name in names:
        src = store.dir(run_id) / name
        if src.exists():
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest / name)


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "step"


async def _finish(b: Bench, row: dict[str, Any], windows: dict[str, Window]) -> None:
    """Disarm, measure the step's windows and stop its traffic."""
    runner, topology_id = b.runner, b.spec["topology_id"]
    assert b.session is not None
    b.armed = False
    if b.trip is not None:
        _fail(row, "stopped", *b.trip)
    row.update(bm.step_metrics(b.session.host_rows, b.agg, windows, row.get("nodes") or 0))
    row["by_image"] = bm.image_metrics(b.by_image, windows)
    await _stop_traffic(runner, topology_id)


async def _teardown(b: Bench, row: dict[str, Any], name: str, last: bool) -> None:
    """Destroy the step's lab unless it is the sweep's ``last`` and
    ``keep_last`` keeps it."""
    if last and b.spec.get("keep_last"):
        return
    b.progress(name, "destroying")
    destroy = await _destroy(b.runner, b.spec["topology_id"])
    if destroy is not None:
        row["destroy_job"] = destroy.id
        row["destroy_s"] = _elapsed(destroy)
        if destroy.status != "succeeded":
            _fail(row, "failed", "destroy_failed", destroy.error or destroy.status)
    b.mark(f"{name}: destroyed")


async def run_step(
    b: Bench,
    name: str,
    scale: int,
    rep: int,
    ends: Callable[[dict[str, Any]], bool] | None = None,
    *,
    data: dict[str, Any] | None = None,
    artifact: str | None = None,
) -> dict[str, Any]:
    """One step: place, reference, deploy, ready, settle, hold, measure,
    destroy. ``data``: the step's topology (default: generated at ``scale``,
    or the stored one). ``ends``: whether the sweep ends after this step
    (``keep_last`` keeps its lab), asked once the step is measured; by
    default a step that did not pass, or the plan's last (``b.is_last``)."""
    spec = b.spec
    row: dict[str, Any] = {"step": name, "scale": scale, "rep": rep, "outcome": "ok"}
    row["reason"] = row["detail"] = None
    if data is None and spec.get("generated"):
        data = generate(_gen_params(spec, scale))
    topo = _place(b, row, data, artifact or f"{scale}-{rep}")
    windows: dict[str, Window] = {"pre": None, "settle": None, "hold": None}
    windows["pre"] = await _reference(b, row, name)
    try:
        state = await _deploy(b, row, name)
        if state is None or not await _ready(b, row, name, topo.data, state):
            return row
        windows["settle"] = await _settle(b, name)
        load = spec.get("traffic")
        if load:
            load = {**load, "slug": f"{scale}-{rep}"}
        await _hold(b, row, name, windows, float(spec.get("hold_s") or 0), load)
    except Tripped:
        pass
    finally:
        await _finish(b, row, windows)
        last = ends(row) if ends else (row["outcome"] != "ok" or b.is_last)
        await _teardown(b, row, name, last)
    return row


def _write_results(directory: Path, rows: list[dict[str, Any]]) -> None:
    flat = []
    for r in rows:
        f = {k: v for k, v in r.items() if k not in ("deploy_phases", "by_image", "composition")}
        for phase, secs in (r.get("deploy_phases") or {}).items():
            f[f"deploy_{phase}_s"] = secs
        flat.append(f)
    columns = list(dict.fromkeys(k for r in flat for k in r))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns)
    w.writeheader()
    w.writerows(flat)
    (directory / RESULTS_NAME).write_text(buf.getvalue())


def _write_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(path)


async def _preflight(b: Bench) -> dict[str, Any]:
    """Other labs and jobs on the host (they would skew the numbers)."""
    runner = b.runner
    topo = _topo(runner, b.spec["topology_id"])
    own = (EngineState.from_dict(topo.engine_state) or EngineState("", "")).lab_hash
    labs = [
        lab.to_dict()
        for lab in await runner.engine.list_labs()
        if lab.running and lab.lab_hash != own
    ]
    with runner.session_factory() as db:
        busy_jobs = [
            {"id": j.id, "kind": j.kind, "topology_id": j.topology_id}
            for j in db.scalars(select(Job).where(Job.status.in_(jobs.ACTIVE), Job.id != b.job_id))
            if j.kind not in QUIET_KINDS
        ]
    return {"labs": labs, "jobs": busy_jobs}


def _halts(b: Bench, row: dict[str, Any]) -> bool:
    """Whether a step's outcome ends the sweep."""
    return row["outcome"] != "ok" and (
        row["outcome"] != "degraded" or b.stop.get("stop_on_degraded", True)
    )


async def _climb(b: Bench, adaptive: dict[str, Any], step, persist) -> str:
    """An adaptive sweep: each step's scale follows from the last one's memory
    (``bm.next_scale``) until memory peaks at the target or a step fails, then
    the highest passing scale runs ``confirm`` more times. A step that fails
    on a host limit is retried lower (``bm.retry_scale``: ``descend`` of a
    first step too big for the host, else halfway down to the best passing
    scale), and the climb stays below it."""
    runner, spec = b.runner, b.spec
    max_scale = int(spec.get("max_scale") or adaptive["start"])
    scale: int | None = min(int(adaptive["start"]), max_scale)
    confirm = int(adaptive.get("confirm") or 0)
    max_steps = int(adaptive.get("max_steps") or 20)
    descend = float(adaptive.get("descend") or 0)
    unit = max(1, int(adaptive.get("min_step") or 25))
    stopped_by = "max_steps"
    nxt: tuple[int | None, str, str] | None = None
    cap: int | None = None  # the lowest scale that failed on a host limit

    def passed(row: dict[str, Any]) -> bool:  # a scale for the confirm runs
        return any(r["outcome"] == "ok" for r in [*b.rows, row])

    def retry(row: dict[str, Any]) -> int | None:
        if row["reason"] not in bm.HOST_LIMITS:
            return None
        best = max((r["scale"] for r in b.rows if r["outcome"] == "ok"), default=None)
        return bm.retry_scale(best, int(row["scale"]), descend, unit)

    def climb_ends(final: bool) -> Callable[[dict[str, Any]], bool]:
        # A climb step's own memory decides whether the climb goes on, so the
        # step asks once it is measured, before its destroy (keep_last).
        def ends(row: dict[str, Any]) -> bool:
            nonlocal nxt
            if _halts(b, row):
                if not final and retry(row) is not None:
                    return False
                return not (confirm and passed(row))
            host = b.session.host_rows[-1] if b.session and b.session.host_rows else {}
            nxt = bm.next_scale(
                row,
                adaptive,
                mem_total=host.get("mem_total"),
                nodes_for=lambda h: counts(_gen_params(spec, h))["nodes"],
                max_scale=max_scale,
                cap=cap,
            )
            return (final or nxt[0] is None) and not (confirm and passed(row))

        return ends

    for i in range(max_steps):
        assert scale is not None
        nxt = None
        final = i == max_steps - 1
        row = await step(scale, 1, f"{scale} hosts", climb_ends(final))
        if runner.stop_requested(b.job_id):
            return runner.stop_code(b.job_id) or "user"
        if _halts(b, row):
            lower = None if final else retry(row)
            if lower is None:
                stopped_by = f"criterion:{row['reason']}"
                b.limit = f"{scale} hosts failed ({row['reason']})"
                break
            cap = scale if cap is None else min(cap, scale)
            why = f"{scale} hosts failed ({row['reason']}): trying {lower} hosts"
            row["next"] = why
            b.mark(why)
            persist()
            scale = lower
            continue
        assert nxt is not None
        scale, code, why = nxt
        row["next"] = why
        b.mark(why)
        persist()
        if scale is None:
            stopped_by, b.limit = code, why
            break
    best = max((r["scale"] for r in b.rows if r["outcome"] == "ok"), default=None)
    for rep in range(2, confirm + 2):
        if best is None:
            break
        row = await step(
            best, rep, f"{best} hosts #{rep}", lambda r, rep=rep: rep == confirm + 1 or _halts(b, r)
        )
        if runner.stop_requested(b.job_id):
            return runner.stop_code(b.job_id) or "user"
        if _halts(b, row):
            break
    return stopped_by


async def run_benchmark(runner: JobRunner, job_id: str) -> None:
    settings, store, hub = runner.settings, runner.artifacts, runner.live
    assert settings is not None and store is not None and hub is not None
    with runner.session_factory() as db:
        spec = dict(db.get(Job, job_id).params or {})
    b = Bench(runner, job_id, spec)
    directory = store.dir(job_id, create=True)
    channel = hub.open(job_id, replay=0)
    started = datetime.now(UTC)
    env: dict[str, Any] = {}
    stopped_by: str | None = None
    result: dict[str, Any] = {}
    scales = [int(s) for s in spec["scale"]]
    reps = int(spec.get("repetitions") or 1)
    adaptive = spec.get("adaptive") or None
    first_adaptive = int(adaptive["start"]) if adaptive else 0

    def snapshot(final: bool = False) -> dict[str, Any]:
        last = next((r for r in reversed(b.rows) if r["outcome"] != "ok"), None)
        out = {
            "label": spec.get("label") or "",
            "kind": bm.kind_of(spec),
            "started_at": started.isoformat(),
            "ended_at": datetime.now(UTC).isoformat() if final else None,
            "topology_id": spec["topology_id"],
            "rows": b.rows,
            "by_scale": bm.by_scale(b.rows),
            "ceiling": bm.ceiling(b.rows),
            "reason": last["reason"] if last else None,
            "detail": last["detail"] if last else None,
            "stopped_by": stopped_by,
            "limit": b.limit,
            "rest": b.rest,
            "phase": None if final else b.phase,
            "environment_fingerprint": env.get("fingerprint"),
        }
        return out

    def persist(final: bool = False) -> None:
        nonlocal result
        result = snapshot(final)
        with contextlib.suppress(Exception):
            runner.set_result(job_id, result)
        with contextlib.suppress(Exception):
            _write_json(
                directory / INFO_NAME,
                {"kind": KIND, "spec": spec, "environment": env, "result": result},
            )
            _write_results(directory, b.rows)
        if final:
            with contextlib.suppress(Exception):
                (directory / REPORT_NAME).write_text(bm.markdown_report(result, spec, env))
        channel.publish({"type": "status", "result": result}, replay=False)

    try:
        async with runner.step(job_id, "preflight"):
            busy = await _preflight(b)
            if (busy["labs"] or busy["jobs"]) and not spec.get("allow_busy_host"):
                what = [f"lab {lab['lab_hash'][:8]}" for lab in busy["labs"]] + [
                    f"{j['kind']} job" for j in busy["jobs"]
                ]
                raise RuntimeError(
                    "The host is busy (" + ", ".join(what[:5]) + "); stop them first or set "
                    "allow_busy_host"
                )
            runner.progress(
                job_id, "preflight", "host is quiet" if not busy["labs"] else "host busy (allowed)"
            )

        async with runner.step(job_id, "images"):
            assert runner.images is not None
            if spec.get("generated"):
                p = _gen_params(spec, max(scales) if scales else first_adaptive)
                needed = images_in(generate(p)) + [
                    catalog.resolve_image(t, img) for t, img in kinds_used(p)
                ]
            else:
                needed = images_in(_topo(runner, spec["topology_id"]).data)
            needed = list(dict.fromkeys(i for i in needed if i))
            await runner.images.ensure_images(runner, job_id, needed)
            tools = list(
                dict.fromkeys([catalog.tool_image("collector"), catalog.tool_image("driver")])
            )
            await runner.images.ensure_images(
                runner, job_id, tools, stale_event="benchmark.images_stale", rebuild_stale=True
            )
            env = await environment.system_environment(runner.engine, settings)
            env["busy"] = busy
            persist()

        async with runner.step(job_id, "baseline", message=f"monitor every {b.interval:g}s"):
            b.session = monitor_service.MonitorSession(
                runner.engine,
                directory=directory,
                interval=b.interval,
                job_id=job_id,
                owner=settings.ensure_instance_id(),
                image=catalog.tool_image("collector"),
                cgroup_root=settings.collector_cgroup_root,
                scope=m.Scope(step="baseline"),
                topology_id=spec["topology_id"],
            )
            b.session.on_sweep.append(b.on_sweep)
            monitor_service.register_session(job_id, b.session)
            await b.session.start()
            b.mark("benchmark started")
            rest_s = float(spec.get("rest_s") or 0)
            if rest_s:
                runner.progress(job_id, "baseline", f"the host at rest ({rest_s:g}s)")
                t0 = b.now()
                await asyncio.sleep(rest_s)
                b.rest = bm.rest_metrics(b.session.host_rows, (t0, b.now()))
                persist()

        async def step(
            scale: int, rep: int, name: str, ends: Callable[[dict[str, Any]], bool] | None = None
        ) -> dict[str, Any]:
            async with runner.step(job_id, name):
                row = await run_step(b, name, scale, rep, ends)
                b.rows.append(row)
                persist()
                runner.progress(
                    job_id,
                    name,
                    row["outcome"] + (f": {row['detail']}" if row.get("detail") else ""),
                )
            return row

        if adaptive:
            stopped_by = await _climb(b, adaptive, step, persist)
        else:
            plan = [(s, r) for s in scales for r in range(1, reps + 1)]
            for i, (scale, rep) in enumerate(plan):
                b.is_last = i == len(plan) - 1
                name = f"{scale} hosts" + (f" #{rep}" if reps > 1 else "")
                row = await step(scale, rep, name)
                if _halts(b, row):
                    stopped_by = f"criterion:{row['reason']}"
                    break
                if runner.stop_requested(job_id):
                    stopped_by = runner.stop_code(job_id) or "user"
                    break
            else:
                stopped_by = "completed"
    finally:
        b.armed = False
        with contextlib.suppress(Exception):
            await _stop_traffic(runner, spec["topology_id"])
        if not spec.get("keep_last"):
            with contextlib.suppress(Exception):
                await asyncio.wait_for(_destroy(runner, spec["topology_id"]), timeout=600)
        monitor_service.unregister_session(job_id)
        if b.session is not None:
            with contextlib.suppress(Exception):
                await b.session.stop()
        persist(final=True)
        channel.close({"type": "end", "result": result})
        hub.prune()


def register(runner: JobRunner) -> None:
    runner.register(KIND, run_benchmark, cancellable=True, stoppable=True)
