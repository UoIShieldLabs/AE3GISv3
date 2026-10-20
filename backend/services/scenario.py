"""Scenario runner: step through ordered commands on deployed nodes, as a job.

A scenario (stored frontend-side in ``topology.data.scenarios``) is phases of
steps; each step is an ordinary admin/client command run in one lab container.
The runner executes a step — or a whole phase, in order — streaming each
command's output live, so a class can follow the walkthrough and reproduce it.

It composes existing pieces: the engine's ``exec_stream`` (``docker exec`` in
the node, no sidecar and no extra mounts, so any writes stay in the container),
the job machinery (one run at a time per topology, stoppable), and the live
WebSocket fan-out. There is no backend model of the scenario: phases are read
from the opaque topology data and a single step can be run ad hoc.

Jobs: kind ``scenario``, subject ``scenario:<topology>``, stoppable. Steps run
in order; a stop takes effect between steps (a long command in flight is left
to finish or abandoned — the lab is the containment boundary). Each step runs
at most ``scenario_step_max_seconds`` before it is stopped and marked timed out.

Artifacts: ``run.json`` (the request, and once done the per-step results).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import shlex
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from api.errors import Conflict, Invalid
from db.models import Job, Topology
from domain.topology import find_container
from engine.base import EngineState
from services import events, jobs, monitor
from services.jobs import JobRunner
from services.live import Channel

log = logging.getLogger(__name__)

KIND = "scenario"
RUN_NAME = "run.json"
OUTPUT_CAP = 64_000  # bytes of stdout/stderr kept per step in the result (live is uncapped)

# Running runs' completed-step results, by job id (live views start from here).
_ACTIVE: dict[str, list[dict[str, Any]]] = {}


def subject(topology_id: str) -> str:
    return f"scenario:{topology_id}"


def active_steps(job_id: str) -> list[dict[str, Any]] | None:
    return _ACTIVE.get(job_id)


# ── reading scenarios from the opaque topology data ─────────────────────


def _phases(data: dict[str, Any]) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    for sc in data.get("scenarios") or []:
        if not isinstance(sc, dict):
            continue
        for ph in sc.get("phases") or []:
            if isinstance(ph, dict):
                yield sc, ph


def find_phase(data: dict[str, Any], phase_id: str) -> dict[str, Any] | None:
    return next((ph for _, ph in _phases(data) if ph.get("id") == phase_id), None)


def build_command(script: str, args: list[str] | None) -> str:
    """One shell command line from a step's ``script`` (a command, possibly with
    pipes/redirects) and optional ``args`` (appended, each shell-quoted)."""
    line = (script or "").strip()
    if args:
        line = (line + " " + " ".join(shlex.quote(str(a)) for a in args)).strip()
    return line


def argv_for(command: str) -> list[str]:
    """Run the command line through the node's shell (``sh`` is universal; it
    handles pipes and redirects). Steps needing bash can say ``bash -c '…'``."""
    return ["sh", "-lc", command]


def _normalize(index: int, execution: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": index,
        "container_id": str(execution.get("containerId") or ""),
        "command": build_command(
            str(execution.get("script") or ""),
            [str(a) for a in (execution.get("args") or [])],
        ),
    }


def _validate(topo: Topology, steps: list[dict[str, Any]], max_steps: int) -> None:
    if not steps:
        raise Invalid("There is nothing to run (no steps)", code="empty_scenario")
    if len(steps) > max_steps:
        raise Invalid(
            f"That is {len(steps)} steps; the limit is {max_steps}",
            code="too_many_steps",
            steps=len(steps),
            limit=max_steps,
        )
    data = topo.data or {}
    for s in steps:
        if not s["container_id"]:
            raise Invalid("A step names no node", code="unknown_node")
        if find_container(data, s["container_id"]) is None:
            raise Invalid(
                f"No node {s['container_id']!r} in this topology",
                code="unknown_node",
                node=s["container_id"],
            )
        if not s["command"]:
            raise Invalid(f"The step on {s['container_id']!r} has no command", code="empty_command")


# ── starting a run ──────────────────────────────────────────────────────


def start_step(
    db: Session, runner: JobRunner, topo: Topology, step: dict[str, Any], label: str = ""
) -> Job:
    """Run a single ad-hoc step (``{containerId, script, args?}``) as a run."""
    steps = [_normalize(0, step)]
    return _start(db, runner, topo, steps, label or "Step")


def start_phase(
    db: Session, runner: JobRunner, topo: Topology, phase_id: str, label: str = ""
) -> Job:
    """Run every step of a stored phase, in order."""
    phase = find_phase(topo.data or {}, phase_id)
    if phase is None:
        raise Invalid("No such phase in this topology", code="unknown_phase", phase=phase_id)
    executions = [e for e in (phase.get("executions") or []) if isinstance(e, dict)]
    steps = [_normalize(i, e) for i, e in enumerate(executions)]
    return _start(db, runner, topo, steps, label or str(phase.get("name") or "Phase"))


def _start(
    db: Session, runner: JobRunner, topo: Topology, steps: list[dict[str, Any]], label: str
) -> Job:
    settings = runner.settings
    assert settings is not None
    _validate(topo, steps, settings.scenario_max_steps)
    with runner.admission:
        db.refresh(topo)
        if topo.status != "deployed" or not topo.engine_state:
            raise Conflict(
                "Deploy the topology before running a scenario",
                code="bad_state",
                status=topo.status,
            )
        existing = jobs.active_for_subject(db, subject(topo.id))
        if existing is not None:
            raise Conflict(
                "A scenario is already running on this topology; stop it first",
                code="scenario_active",
                job_id=existing.id,
            )
        node_ids = list(dict.fromkeys(s["container_id"] for s in steps))
        params = {
            "label": label,
            "steps": steps,
            "step_count": len(steps),
            "node_ids": node_ids,
            "connection_ids": [],
        }
        job = jobs.create_job(
            db, KIND, subject=subject(topo.id), topology_id=topo.id, params=params
        )
        events.record(
            db,
            type="scenario.requested",
            message=f"Scenario requested ({len(steps)} step(s))",
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


async def _run_step(
    runner: JobRunner,
    job_id: str,
    engine: Any,
    state: EngineState,
    step: dict[str, Any],
    channel: Channel,
    step_timeout: float,
) -> dict[str, Any]:
    idx = step["index"]
    cid = step["container_id"]
    command = step["command"]
    name = f"step {idx + 1}"
    stdout = bytearray()
    stderr = bytearray()

    def on_out(data: bytes) -> None:
        stdout.extend(data)
        channel.publish_threadsafe(
            {
                "type": "output",
                "index": idx,
                "stream": "stdout",
                "text": data.decode("utf-8", "replace"),
            },
            replay=False,
        )

    def on_err(data: bytes) -> None:
        stderr.extend(data)
        channel.publish_threadsafe(
            {
                "type": "output",
                "index": idx,
                "stream": "stderr",
                "text": data.decode("utf-8", "replace"),
            },
            replay=False,
        )

    started = datetime.now(UTC)
    status = "ok"
    exit_code: int | None = None
    channel.publish(
        {
            "type": "step",
            "index": idx,
            "status": "running",
            "container_id": cid,
            "command": command,
        },
        replay=False,
    )
    async with runner.step(job_id, name, message=f"{cid}: {command}"):
        try:
            stream = await engine.exec_stream(state, cid, argv_for(command))
        except LookupError as exc:
            status = "error"
            on_err(f"{exc}\n".encode())
        else:
            pump = asyncio.ensure_future(stream.pump(on_out, on_err))
            stop = asyncio.ensure_future(runner.stop_event(job_id).wait())
            deadline = time.monotonic() + step_timeout
            try:
                while True:
                    done, _ = await asyncio.wait(
                        {pump, stop}, timeout=1.0, return_when=asyncio.FIRST_COMPLETED
                    )
                    runner.progress(job_id, name, f"{cid}: {command}", min_interval=5.0)
                    if pump in done:
                        exit_code = pump.result()
                        status = "ok" if exit_code == 0 else "failed"
                        break
                    if stop in done:
                        status = "stopped"
                        break
                    if time.monotonic() >= deadline:
                        status = "timeout"
                        break
            finally:
                stop.cancel()
                if not pump.done():
                    await stream.remove()
                    with contextlib.suppress(BaseException):
                        await pump
    ended = datetime.now(UTC)
    out = bytes(stdout[:OUTPUT_CAP]).decode("utf-8", "replace")
    err = bytes(stderr[:OUTPUT_CAP]).decode("utf-8", "replace")
    result = {
        "index": idx,
        "container_id": cid,
        "command": command,
        "status": status,
        "exit_code": exit_code,
        "stdout": out,
        "stderr": err,
        "truncated": len(stdout) > OUTPUT_CAP or len(stderr) > OUTPUT_CAP,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
    }
    channel.publish({"type": "step", "index": idx, "status": status, "exit_code": exit_code})
    return result


async def run_scenario(runner: JobRunner, job_id: str) -> None:
    settings, store, hub = runner.settings, runner.artifacts, runner.live
    assert settings is not None and store is not None and hub is not None
    engine = runner.engine
    channel = hub.open(job_id)
    params, topo, state = _load(runner, job_id)
    steps: list[dict[str, Any]] = params.get("steps") or []
    run_dir = store.dir(job_id, create=True)
    started = datetime.now(UTC)
    results: list[dict[str, Any]] = []
    _ACTIVE[job_id] = results
    stopped_by: str | None = None
    marked = False
    try:
        if topo.status != "deployed" or state is None:
            raise RuntimeError("The topology is not deployed")
        _write_json(run_dir / RUN_NAME, {"kind": KIND, "params": params, "started_at": started})
        monitor.mark(topo.id, "scenario", f"Scenario started: {len(steps)} step(s)")
        marked = True
        for step in steps:
            if runner.stop_requested(job_id):
                stopped_by = runner.stop_code(job_id) or "user"
                break
            result = await _run_step(
                runner, job_id, engine, state, step, channel, settings.scenario_step_max_seconds
            )
            results.append(result)
            with contextlib.suppress(Exception):
                runner.set_result(job_id, _result(params, results, started, None))
            if result["status"] == "stopped":
                stopped_by = runner.stop_code(job_id) or "user"
                break
        else:
            stopped_by = "completed"
    finally:
        if marked:
            monitor.mark(topo.id, "scenario", f"Scenario ended ({stopped_by or 'failed'})")
        result_obj = _result(params, results, started, stopped_by)
        _ACTIVE.pop(job_id, None)
        with contextlib.suppress(Exception):
            runner.set_result(job_id, result_obj)
        with contextlib.suppress(Exception):
            _write_json(
                run_dir / RUN_NAME,
                {"kind": KIND, "params": params, "started_at": started, "result": result_obj},
            )
        channel.close({"type": "end", "result": result_obj})
        hub.prune()


def _result(
    params: dict[str, Any],
    results: list[dict[str, Any]],
    started: datetime,
    stopped_by: str | None,
) -> dict[str, Any]:
    done = stopped_by is not None
    failed = sum(1 for r in results if r["status"] in ("failed", "timeout", "error"))
    return {
        "label": params.get("label") or "",
        "step_count": params.get("step_count") or len(params.get("steps") or []),
        "ran": len(results),
        "failed": failed,
        "steps": list(results),
        "started_at": started.isoformat(),
        "finished_at": datetime.now(UTC).isoformat() if done else None,
        "stopped_by": stopped_by,
    }


def register(runner: JobRunner) -> None:
    runner.register(KIND, run_scenario, cancellable=True, stoppable=True)
