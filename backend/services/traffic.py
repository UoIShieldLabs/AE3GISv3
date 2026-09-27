"""Traffic between deployed nodes (iperf3 for now), as a job.

A run's flows come from an explicit list and/or patterns (clients → servers,
mesh; see ``domain/traffic/patterns``). One netns driver helper
(``services/netns_driver``) starts every flow's iperf3 server and client inside
the nodes' network namespaces, so traffic leaves from each client's addresses
and follows the lab's real routes (through routers, firewalls…) whatever images
the nodes run, and a thousand flows cost one container rather than two
thousand. Resource use is the Monitor's job (``services/monitor``); a run
notes its start and end on any monitor of the topology.

Everything lands in the job's artifacts:

- ``flows.ndjson``: one line per iperf3 interval sample (see domain/traffic)
- ``totals.ndjson``: once per interval, what arrived over all flows
  (receiver-measured) vs. what the flows were asked to carry
- ``raw.ndjson``: the driver's events, iperf3's own output inside, verbatim
- ``run.json``: the request, the environment (host, versions, images; see
  domain/environment) and, once done, the result with every flow's summary

Jobs: kind ``traffic``, subject ``traffic:<topology>`` (one run at a time per
topology), stoppable. Steps: ``images`` → ``prepare`` (servers listening,
environment recorded) → ``run``.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import threading
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

import catalog
from api.errors import Conflict, Invalid
from db.models import Job, Topology
from domain import selectors
from domain.topology import find_container
from domain.traffic.iperf3 import Iperf3StreamParser, is_interrupt
from domain.traffic.patterns import PatternError, assign_ports, expand, offered_bps
from domain.traffic.summary import FlowSummary
from engine.base import EngineState
from services import environment, events, jobs, monitor
from services.jobs import JobRunner
from services.live import Channel
from services.netns_driver import NetnsDriver, ready_timeout
from services.traffic_generators import GENERATORS

log = logging.getLogger(__name__)

KIND = "traffic"
RUN_NAME = "run.json"
FLOWS_NAME = "flows.ndjson"
TOTALS_NAME = "totals.ndjson"
RAW_NAME = "raw.ndjson"
END_GRACE_S = 15.0
DRIVER_STOP_S = 30.0
LIVE_FLOW_LIMIT = 16  # per-flow samples go to live views up to this many flows
STATUS_FLOW_LIMIT = 200  # every flow's latest rate in status messages up to this many
RESULT_FLOW_LIMIT = 64  # the job row keeps per-flow summaries up to this many (run.json: all)

# Recorders of running runs, by job id (live views start from their backlog).
_ACTIVE: dict[str, RunRecorder] = {}


def subject(topology_id: str) -> str:
    return f"traffic:{topology_id}"


def active_recorder(job_id: str) -> RunRecorder | None:
    return _ACTIVE.get(job_id)


def client_proc(flow_id: str) -> str:
    return f"{flow_id}.c"


def server_proc(flow_id: str) -> str:
    return f"{flow_id}.s"


def split_proc(proc: str) -> tuple[str, str]:
    """``<flow>.c`` → (flow, "client"); ``<flow>.s`` → (flow, "server")."""
    flow_id, _, end = proc.rpartition(".")
    return flow_id, "client" if end == "c" else "server"


class RunRecorder:
    """A run's samples: appended to its files and summarised as they arrive
    (from the driver's output thread), without keeping them all in memory."""

    def __init__(self, directory: Path, flows: list[dict[str, Any]], interval: float) -> None:
        self.dir = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.flows = {f["id"]: f for f in flows}
        self.interval = interval
        self.t0 = time.time()
        self.live_samples = len(flows) <= LIVE_FLOW_LIMIT
        self.channel: Channel | None = None
        self._lock = threading.Lock()
        self._flows_fh = (directory / FLOWS_NAME).open("a")
        self._totals_fh = (directory / TOTALS_NAME).open("a")
        self._raw_fh = (directory / RAW_NAME).open("a")
        self._parsers: dict[str, Iperf3StreamParser] = {}
        for fid in self.flows:
            self._parsers[client_proc(fid)] = Iperf3StreamParser(fid, "client")
            self._parsers[server_proc(fid)] = Iperf3StreamParser(fid, "server")
        self.summaries: dict[str, FlowSummary] = {fid: FlowSummary() for fid in self.flows}
        self.last: dict[str, dict[str, tuple[float, float]]] = {}  # flow -> dir -> (t, bps)
        self.samples: deque[dict[str, Any]] = deque(maxlen=20_000)  # recent, for live views
        self.totals: deque[dict[str, Any]] = deque(maxlen=3600)
        self.started: set[str] = set()  # procs that started
        self.exited: dict[str, int] = {}
        self.proc_errors: dict[str, list[str]] = {}  # stderr / start failures, per proc
        self.processes = 0

    # ── driver events (any thread) ──
    def on_event(self, evt: dict[str, Any]) -> None:
        rows: list[dict[str, Any]] = []
        with self._lock:
            self._raw_fh.write(json.dumps(evt, separators=(",", ":")) + "\n")
            k, proc = evt.get("k"), evt.get("p")
            if k == "out" and proc in self._parsers:
                event = self._parsers[proc].parse_line(evt.get("line", ""))
                if event is not None and event.samples:
                    rows = [s.to_dict() for s in event.samples]
                    self._record(rows)
            elif k == "started" and proc in self._parsers:
                if proc not in self.started:
                    self.started.add(proc)
                    self.processes += 1
                flow_id, role = split_proc(proc)
                if role == "client":
                    # iperf3 times intervals from its test start: the client's start.
                    offset = float(evt.get("t", time.time())) - self.t0
                    self._parsers[proc].offset = offset
                    self._parsers[server_proc(flow_id)].offset = offset
            elif k == "retry" and proc in self._parsers:
                flow_id, role = split_proc(proc)
                old = self._parsers[proc]
                self._parsers[proc] = Iperf3StreamParser(flow_id, role, old.offset)
            elif k == "exit" and proc is not None:
                self.exited[proc] = int(evt.get("code", -1))
            elif k == "err" and proc is not None and evt.get("line"):
                errs = self.proc_errors.setdefault(proc, [])
                if len(errs) < 5:
                    errs.append(str(evt["line"])[:300])
            self._flows_fh.flush()
            self._raw_fh.flush()
        if rows and self.live_samples and self.channel is not None:
            self.channel.publish_threadsafe({"type": "flow", "samples": rows}, replay=False)

    def _record(self, rows: list[dict[str, Any]]) -> None:
        for s in rows:
            self._flows_fh.write(json.dumps(s) + "\n")
            self.summaries[s["flow_id"]].add(s)
            if self.live_samples:
                self.samples.append(s)
            # The receiver's view wins over the sender's for the live number.
            last = self.last.setdefault(s["flow_id"], {})
            if s["side"] == "receiver" or s["direction"] not in last:
                last[s["direction"]] = (s["t"], s["bps"])

    # ── the loop's view ──
    def running_clients(self) -> list[str]:
        return [
            fid
            for fid in self.flows
            if client_proc(fid) in self.started and client_proc(fid) not in self.exited
        ]

    def tick(self) -> dict[str, Any]:
        """Totals now; appended to totals.ndjson."""
        now = round(time.time() - self.t0, 3)
        horizon = max(2.5 * self.interval, 2.0)
        with self._lock:
            delivered = sum(
                bps for dirs in self.last.values() for t, bps in dirs.values() if now - t <= horizon
            )
            running = self.running_clients()
            rates = [offered_bps(self.flows[fid]) for fid in running]
            row = {
                "t": now,
                "delivered_bps": round(delivered, 1),
                "offered_bps": None if any(r is None for r in rates) else round(sum(rates), 1),
                "active": len(running),
            }
            self._totals_fh.write(json.dumps(row) + "\n")
            self._totals_fh.flush()
            self.totals.append(row)
        return row

    def latest_rates(self, limit: int = STATUS_FLOW_LIMIT) -> dict[str, dict[str, float]]:
        with self._lock:
            rates = {
                fid: {d: bps for d, (_, bps) in dirs.items()} for fid, dirs in self.last.items()
            }
        if len(rates) <= limit:
            return rates
        ranked = sorted(rates.items(), key=lambda kv: sum(kv[1].values()), reverse=True)
        return dict(ranked[:limit])

    def backlog(self) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            return {"flows": list(self.samples), "totals": list(self.totals)}

    def errors(self, flow_id: str) -> list[str]:
        out = []
        for proc in (client_proc(flow_id), server_proc(flow_id)):
            parser = self._parsers[proc]
            out += [e for e in parser.errors if not is_interrupt(e)]
            out += self.proc_errors.get(proc, []) if self.exited.get(proc, 0) not in (0,) else []
        return list(dict.fromkeys(out))

    def close(self) -> None:
        with self._lock:
            for fh in (self._flows_fh, self._totals_fh, self._raw_fh):
                with contextlib.suppress(OSError):
                    fh.close()


def read_backlog(
    directory: Path, *, flows: set[str] | None = None, samples: bool = True
) -> dict[str, list[dict[str, Any]]]:
    """A finished run's samples, from its files."""
    out: dict[str, list[dict[str, Any]]] = {"flows": [], "totals": []}
    for key, name in (("flows", FLOWS_NAME), ("totals", TOTALS_NAME)):
        if key == "flows" and not samples:
            continue
        path = directory / name
        if not path.exists():
            continue
        with path.open() as fh:
            for line in fh:
                with contextlib.suppress(ValueError):
                    row = json.loads(line)
                    if key == "flows" and flows is not None and row.get("flow_id") not in flows:
                        continue
                    out[key].append(row)
    return out


# ── starting (request side) ──────────────────────────────────────────


def _node_ip(data: dict[str, Any], node_id: str) -> str | None:
    c = find_container(data or {}, node_id)
    ip = (c or {}).get("ip")
    return str(ip).strip() if ip else None


def plan_flows(
    topo: Topology, state: EngineState, req: dict[str, Any], max_flows: int
) -> list[dict[str, Any]]:
    """The request's flows (explicit + expanded patterns), checked, with the
    server address and port each client connects to."""
    flows: list[dict[str, Any]] = []
    ids: set[str] = set()
    for f in req.get("flows") or []:
        if f["id"] in ids:
            raise Invalid(f"Flow id {f['id']!r} is used twice", code="duplicate_flow")
        ids.add(f["id"])
        flows.append(dict(f))

    def pick(selector: Any) -> list[str]:
        return selectors.resolve(topo.data, state.nodes, selector if selector else "all")

    try:
        flows += expand(req.get("patterns") or [], pick)
    except PatternError as exc:
        raise Invalid(str(exc), code=exc.code) from exc
    except ValueError as exc:
        raise Invalid(str(exc), code="bad_selector") from exc
    if not flows:
        raise Invalid("The run has no flows", code="no_flows")
    if len(flows) > max_flows:
        raise Invalid(
            f"The run makes {len(flows)} flows; the limit is {max_flows}",
            code="too_many_flows",
            flows=len(flows),
            limit=max_flows,
        )
    for f in flows:
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
        # The node's own address: its server binds to it (see iperf3.server_argv).
        f["bind_server"] = not f.get("server_address")
        f["server_address"] = str(server_ip)
        f.setdefault("generator", "iperf3")
    assign_ports(flows)
    return flows


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
        flows = plan_flows(topo, state, req, settings.traffic_max_flows)
        node_ids = list(dict.fromkeys(n for f in flows for n in (f["client"], f["server"])))
        duration = req.get("duration_s")
        params = {
            "label": req.get("label") or "",
            "notes": req.get("notes") or "",
            "flows": flows,
            "patterns": req.get("patterns") or [],
            "duration_s": min(duration, settings.traffic_max_seconds) if duration else None,
            "interval_s": req.get("interval_s") or 1.0,
            "ramp_s": req.get("ramp_s") or 0.0,
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


def driver_spec(
    flows: list[dict[str, Any]],
    pids: dict[str, int],
    *,
    duration: int | None,
    interval: float,
    ramp: float,
) -> dict[str, Any]:
    procs: list[dict[str, Any]] = []
    for f in flows:
        gen = GENERATORS[f.get("generator") or "iperf3"]
        procs.append(
            {
                "id": server_proc(f["id"]),
                "pid": pids[f["server"]],
                "role": "server",
                "port": f["port"],
                "argv": gen.server_argv(f, f["port"], interval),
            }
        )
    for f in flows:
        gen = GENERATORS[f.get("generator") or "iperf3"]
        procs.append(
            {
                "id": client_proc(f["id"]),
                "pid": pids[f["client"]],
                "role": "client",
                "retries": 3,
                "argv": gen.client_argv(
                    {**f, "duration_s": duration or 0}, f["server_address"], f["port"], interval
                ),
            }
        )
    return {
        "mode": "run",
        "ramp_s": ramp,
        "ready_timeout_s": ready_timeout(len(flows)),
        "grace_s": 10,
        "procs": procs,
    }


async def run_traffic(runner: JobRunner, job_id: str) -> None:
    settings, store, hub = runner.settings, runner.artifacts, runner.live
    assert settings is not None and store is not None and hub is not None
    engine = runner.engine
    channel = hub.open(job_id, replay=0)
    params, topo, state = _load(runner, job_id)
    flows: list[dict[str, Any]] = params["flows"]
    interval = float(params.get("interval_s") or 1.0)
    duration = params.get("duration_s")
    run_dir = store.dir(job_id, create=True)
    recorder = RunRecorder(run_dir, flows, interval)
    recorder.channel = channel
    _ACTIVE[job_id] = recorder
    image = catalog.tool_image("driver")
    started = datetime.now(UTC)
    env: dict[str, Any] = {}
    stopped_by: str | None = None
    driver: NetnsDriver | None = None
    failed_servers: list[str] = []
    marked = False
    try:
        async with runner.step(job_id, "images"):
            assert runner.images is not None
            await runner.images.ensure_images(
                runner, job_id, [image], stale_event="traffic.images_stale", rebuild_stale=True
            )

        async with runner.step(job_id, "prepare", message=f"{len(flows)} flow(s)"):
            if topo.status != "deployed" or state is None:
                raise RuntimeError("The topology is not deployed")
            pids = await engine.node_pids(state)
            missing = sorted(
                {n for f in flows for n in (f["client"], f["server"]) if n not in pids}
            )
            if missing:
                raise RuntimeError("Not running: " + ", ".join(missing[:10]))
            spec = driver_spec(
                flows,
                pids,
                duration=duration,
                interval=interval,
                ramp=float(params.get("ramp_s") or 0.0),
            )
            driver = NetnsDriver(
                engine,
                settings,
                image=image,
                job_id=job_id,
                owner=settings.ensure_instance_id(),
                lab_hash=state.lab_hash,
            )
            recorder.t0 = time.time()
            await driver.start(spec, recorder.on_event)
            ready = await driver.wait_ready(spec["ready_timeout_s"] + 30)
            failed_servers = [split_proc(p)[0] for p in ready.get("failed") or []]
            if failed_servers:
                first = recorder.flows[failed_servers[0]]
                message = (
                    f"The traffic server for flow {first['id']!r} on {first['server']} "
                    "did not start listening"
                )
                if len(failed_servers) == len(flows):
                    raise RuntimeError(message)
                runner.event(
                    job_id,
                    "traffic.servers_failed",
                    f"{message} ({len(failed_servers)} of {len(flows)} flows)",
                    level="warning",
                    data={"flows": failed_servers[:100]},
                )
            runner.progress(
                job_id, "prepare", f"{len(flows) - len(failed_servers)} server(s) listening"
            )
            versions = {}
            with contextlib.suppress(Exception):
                _, text = await driver.helper.exec(["iperf3", "--version"])
                versions["iperf3"] = text.splitlines()[0].strip() if text else ""
            with runner.session_factory() as db:
                concurrent = [
                    {"job_id": j.id, "kind": j.kind, "label": (j.params or {}).get("label")}
                    for j in jobs.active_jobs(db, topo.id, kinds=("capture", "monitor"))
                ]
            env = await environment.snapshot(
                engine,
                settings,
                topo,
                state,
                tool_ref=image,
                tool_versions=versions,
                extra={
                    "traffic": {
                        "flows": len(flows),
                        "interval_s": interval,
                        "ramp_s": params.get("ramp_s") or 0.0,
                    },
                    "concurrent_jobs": concurrent,
                },
            )
            _write_json(
                run_dir / RUN_NAME,
                {"kind": KIND, "params": params, "environment": env, "started_at": started},
            )
            monitor.mark(topo.id, "traffic", f"Traffic started: {len(flows)} flow(s)")
            marked = True

        label = f"{len(flows)} flow(s)" + (f", {duration}s" if duration else ", until stopped")
        async with runner.step(job_id, "run", message=label):
            stopped_by = await _wait_run(
                runner, job_id, driver, recorder, channel, duration, settings
            )
            await driver.stop(DRIVER_STOP_S)
            ok = [fid for fid in recorder.flows if not recorder.errors(fid)]
            if not ok:
                errors = [e for fid in recorder.flows for e in recorder.errors(fid)]
                raise RuntimeError(errors[0] if errors else "Every flow failed")
    finally:
        if driver is not None:
            await driver.remove()
        with contextlib.suppress(Exception):
            await engine.remove_sidecars(job_id=job_id)
        if marked:
            monitor.mark(topo.id, "traffic", f"Traffic ended ({stopped_by or 'failed'})")
        full, lean = _result(params, recorder, started, stopped_by, env)
        _ACTIVE.pop(job_id, None)
        recorder.close()
        with contextlib.suppress(Exception):
            runner.set_result(job_id, lean)
        with contextlib.suppress(Exception):
            _write_json(
                run_dir / RUN_NAME,
                {
                    "kind": KIND,
                    "params": params,
                    "environment": env,
                    "started_at": started,
                    "result": full,
                },
            )
        channel.close({"type": "end", "result": lean})
        hub.prune()


async def _wait_run(runner, job_id, driver, recorder, channel, duration, settings) -> str:
    """Until the clients finish, a stop, or the deadline; returns why it ended."""
    limit = (duration + END_GRACE_S) if duration else settings.traffic_max_seconds
    stop = asyncio.ensure_future(runner.stop_event(job_id).wait())
    done = asyncio.ensure_future(driver.done_event().wait())
    t0 = time.monotonic()
    tick = max(min(recorder.interval, 5.0), 0.5)
    try:
        while True:
            finished, _ = await asyncio.wait(
                {stop, done}, timeout=tick, return_when=asyncio.FIRST_COMPLETED
            )
            totals = recorder.tick()
            channel.publish(
                {
                    "type": "status",
                    "elapsed": round(time.monotonic() - t0, 1),
                    "total": totals,
                    "flows": recorder.latest_rates(),
                },
                replay=False,
            )
            parts = [f"{totals['active']} running", f"{totals['delivered_bps'] / 1e6:.1f} Mb/s"]
            if totals["offered_bps"]:
                parts.append(f"of {totals['offered_bps'] / 1e6:.1f} Mb/s asked")
            runner.progress(job_id, "run", " · ".join(parts), min_interval=2.0)
            if stop in finished:
                return runner.stop_code(job_id) or "user"
            if done in finished:
                if driver.error:
                    raise RuntimeError(f"The traffic driver failed: {driver.why()}")
                return "completed"
            if time.monotonic() - t0 >= limit:
                return "limit:time"
    finally:
        for f in (stop, done):
            f.cancel()


def _flow_result(f: dict[str, Any], recorder: RunRecorder) -> dict[str, Any]:
    return {
        "id": f["id"],
        "generator": f.get("generator") or "iperf3",
        "pattern": f.get("pattern"),
        "client": f["client"],
        "server": f["server"],
        "server_address": f.get("server_address"),
        "protocol": f.get("protocol") or "tcp",
        "direction": f.get("direction") or "forward",
        "bitrate": f.get("bitrate"),
        "port": f.get("port"),
        "summary": recorder.summaries[f["id"]].result(),
        "errors": recorder.errors(f["id"]),
    }


def totals(flows: list[dict[str, Any]], per_flow: list[dict[str, Any]], processes: int) -> dict:
    """Run-wide numbers from the flows' summaries."""
    delivered = 0.0
    retrans = lost = packets = 0
    no_data = 0
    for r in per_flow:
        flow_bps = sum((d.get("bps") or {}).get("mean") or 0.0 for d in r["summary"].values())
        if not flow_bps:  # nothing measured, or nothing arrived (a stalled flow)
            no_data += 1
        for d in r["summary"].values():
            delivered += (d.get("bps") or {}).get("mean") or 0.0
            retrans += d.get("retransmits") or 0
            lost += d.get("lost_packets") or 0
            packets += d.get("packets") or 0
    rates = [offered_bps(f) for f in flows]
    offered = None if any(r is None for r in rates) else sum(rates)
    return {
        "flows": len(flows),
        "processes": processes,
        "delivered_bps": round(delivered, 1),
        "offered_bps": offered,
        "delivered_ratio": round(delivered / offered, 4) if offered else None,
        "retransmits": retrans,
        "lost_packets": lost if packets else None,
        "lost_percent": round(100 * lost / packets, 4) if packets else None,
        "flows_with_errors": sum(1 for r in per_flow if r["errors"]),
        "flows_without_data": no_data,
    }


def _result(params, recorder, started, stopped_by, env) -> tuple[dict, dict]:
    """(full result for run.json, lean result for the job row)."""
    ended = datetime.now(UTC)
    flows = params.get("flows") or []
    per_flow = [_flow_result(f, recorder) for f in flows]
    base = {
        "label": params.get("label") or "",
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_s": round((ended - started).total_seconds(), 3),
        "stopped_by": stopped_by,
        "totals": totals(flows, per_flow, recorder.processes),
        "environment_fingerprint": env.get("fingerprint"),
    }
    full = {**base, "flows": per_flow}
    if len(per_flow) <= RESULT_FLOW_LIMIT:
        return full, full

    def mean_bps(r: dict[str, Any]) -> float:
        return sum((d.get("bps") or {}).get("mean") or 0.0 for d in r["summary"].values())

    ranked = sorted(per_flow, key=mean_bps)
    keep = {r["id"] for r in ranked[:10] + ranked[-10:]} | {
        r["id"] for r in per_flow if r["errors"]
    }
    lean = {
        **base,
        "flows": [r for r in per_flow if r["id"] in keep][:RESULT_FLOW_LIMIT],
        "flows_truncated": True,
    }
    return full, lean


def register(runner: JobRunner) -> None:
    runner.register(KIND, run_traffic, cancellable=True, stoppable=True)
