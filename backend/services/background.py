"""Background runs: commands kept running in lab nodes until stopped, as a job.

A tutorial's background traffic is a handful of command lines (a polling loop
on a client, a ``curl`` every few seconds) that should run from "Start" to
"Stop" without a terminal. A background run starts each one in its node with
the engine's ``exec_stream`` (``docker exec``, the node's own tools and
filesystem), holds them, and reports per item whether it still runs, how it
ended and the last of what it printed.

Jobs: kind ``background``, subject ``background:<topology>`` (one at a time
per topology), stoppable, listed in ``/runtime``'s activity and stopped by
destroy. The run ends when it is stopped, when every item has ended on its
own, or after ``background_max_seconds``.

Stopping kills each command's process tree (``ExecStream.remove``). Every
command also starts with ``AE3GIS_BG=<job>`` in its environment (``env`` runs
the shell, so the shell itself carries it, not only what it spawns: an
``export`` would only reach the children, and a loop would outlive its
``sleep``), so whatever detached itself from that tree, or outlived a backend
restart, is found by the marker and killed too: at the end of a run and
before the next one starts.
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import logging
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from api.errors import Conflict, Invalid
from db.models import Job, Topology
from domain.topology import find_container
from engine.base import EngineState, ExecStream
from services import events, jobs, monitor
from services.jobs import JobRunner
from services.scenario import argv_for

log = logging.getLogger(__name__)

KIND = "background"
MARKER = "AE3GIS_BG"
OUTPUT_TAIL = 4000  # bytes of each item's latest output kept
# Kills every process in the node whose environment carries the marker (this
# shell's own does not). Plain sh + tr + grep: present in every node image.
KILL_MARKED = (
    'for p in /proc/[0-9]*; do [ "$p" = "/proc/$$" ] && continue; '
    f"tr '\\0' '\\n' <\"$p/environ\" 2>/dev/null | grep -q '^{MARKER}=' "
    '&& kill "${p#/proc/}" 2>/dev/null; done; true'
)

# Running runs' item views, by job id (reads while the run is live start here).
_ACTIVE: dict[str, list[dict[str, Any]]] = {}


def subject(topology_id: str) -> str:
    return f"background:{topology_id}"


def active_items(job_id: str) -> list[dict[str, Any]] | None:
    """A running run's items as they are now, or None once it has finished."""
    items = _ACTIVE.get(job_id)
    return copy.deepcopy(items) if items is not None else None


def marked_argv(job_id: str, command: str) -> list[str]:
    """Run ``command`` through the node's shell, the run's marker in that
    shell's own environment (and so in everything it starts)."""
    return ["env", f"{MARKER}={job_id}", *argv_for(command)]


# ── starting a run ──────────────────────────────────────────────────────


def start_run(db: Session, runner: JobRunner, topo: Topology, req: dict[str, Any]) -> Job:
    items = [
        {
            "id": str(i["id"]),
            "container_id": str(i["containerId"]),
            "command": str(i["command"]).strip(),
        }
        for i in req.get("items") or []
    ]
    data = topo.data or {}
    for item in items:
        if find_container(data, item["container_id"]) is None:
            raise Invalid(
                f"No node {item['container_id']!r} in this topology",
                code="unknown_node",
                node=item["container_id"],
            )
        if not item["command"]:
            raise Invalid(
                f"The item on {item['container_id']!r} has no command", code="empty_command"
            )
    with runner.admission:
        db.refresh(topo)
        if topo.status != "deployed" or not topo.engine_state:
            raise Conflict(
                "Deploy the topology before starting background commands",
                code="bad_state",
                status=topo.status,
            )
        existing = jobs.active_for_subject(db, subject(topo.id))
        if existing is not None:
            raise Conflict(
                "Background commands are already running on this topology; stop them first",
                code="background_active",
                job_id=existing.id,
            )
        params = {
            "label": req.get("label") or "",
            "tag": req.get("tag") or "",
            "items": items,
            "node_ids": list(dict.fromkeys(i["container_id"] for i in items)),
            "connection_ids": [],
        }
        job = jobs.create_job(
            db, KIND, subject=subject(topo.id), topology_id=topo.id, params=params
        )
        events.record(
            db,
            type="background.requested",
            message=f"Background run requested ({len(items)} command(s))",
            topology_id=topo.id,
            job_id=job.id,
        )
        db.commit()
    db.refresh(job)
    runner.submit(job.id)
    return job


# ── the job ───────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def _kill_marked(engine: Any, state: EngineState, node_ids: list[str]) -> None:
    """Best effort: a node that is down, or has no ``tr``/``grep``, is skipped."""

    async def one(node_id: str) -> None:
        with contextlib.suppress(Exception):
            await engine.exec_output(state, node_id, ["sh", "-c", KILL_MARKED], timeout=5.0)

    await asyncio.gather(*(one(n) for n in node_ids))


async def run_background(runner: JobRunner, job_id: str) -> None:
    settings = runner.settings
    assert settings is not None
    engine = runner.engine
    with runner.session_factory() as db:
        job = db.get(Job, job_id)
        assert job is not None and job.topology_id
        params = dict(job.params or {})
        topo = db.get(Topology, job.topology_id)
        assert topo is not None
        db.expunge(topo)
    state = EngineState.from_dict(topo.engine_state)
    items: list[dict[str, Any]] = [
        {
            **i,
            "status": "starting",
            "exit_code": None,
            "output": "",
            "started_at": None,
            "ended_at": None,
        }
        for i in params.get("items") or []
    ]
    nodes: list[str] = list(params.get("node_ids") or [])
    _ACTIVE[job_id] = items
    streams: list[ExecStream] = []
    pumps: dict[asyncio.Future, dict[str, Any]] = {}
    tails: dict[str, bytearray] = {}
    stopped_by: str | None = None
    marked_monitor = False

    def publish(final: bool = False) -> None:
        with contextlib.suppress(Exception):
            runner.set_result(
                job_id,
                {
                    "items": copy.deepcopy(items),
                    "stopped_by": stopped_by,
                    "finished_at": _now() if final else None,
                },
            )

    def tail(item: dict[str, Any]):
        buf = tails.setdefault(item["id"], bytearray())

        def on_data(data: bytes) -> None:  # called from the pump's thread
            buf.extend(data)
            del buf[:-OUTPUT_TAIL]
            item["output"] = bytes(buf).decode("utf-8", "replace")

        return on_data

    try:
        if topo.status != "deployed" or state is None:
            raise RuntimeError("The topology is not deployed")
        async with runner.step(job_id, "prepare", message=f"{len(items)} command(s)"):
            await _kill_marked(engine, state, nodes)
        async with runner.step(job_id, "run", message=f"{len(items)} running"):
            monitor.mark(topo.id, "background", f"Background run started: {len(items)} command(s)")
            marked_monitor = True
            for item in items:
                item["started_at"] = _now()
                try:
                    stream = await engine.exec_stream(
                        state, item["container_id"], marked_argv(job_id, item["command"])
                    )
                except LookupError as exc:
                    item.update(status="error", output=str(exc), ended_at=_now())
                    continue
                streams.append(stream)
                item["status"] = "running"
                on_data = tail(item)
                pumps[asyncio.ensure_future(stream.pump(on_data, on_data))] = item
            publish()
            stop = asyncio.ensure_future(runner.stop_event(job_id).wait())
            deadline = time.monotonic() + settings.background_max_seconds
            pending = set(pumps)
            try:
                while pending:
                    done, pending = await asyncio.wait(
                        pending | {stop}, timeout=1.0, return_when=asyncio.FIRST_COMPLETED
                    )
                    pending.discard(stop)
                    ended = [f for f in done if f is not stop]
                    for fut in ended:
                        item = pumps[fut]
                        code = fut.result() if fut.exception() is None else -1
                        item.update(status="exited", exit_code=code, ended_at=_now())
                    if ended:
                        publish()
                    running = sum(1 for i in items if i["status"] == "running")
                    runner.progress(job_id, "run", f"{running} running", min_interval=5.0)
                    if stop in done or runner.stop_requested(job_id):
                        stopped_by = runner.stop_code(job_id) or "user"
                        break
                    if time.monotonic() >= deadline:
                        stopped_by = "limit:time"
                        break
                else:
                    stopped_by = "completed"
            finally:
                stop.cancel()
    finally:
        # All at once: each removal is a ``docker exec`` into its node, and one
        # after another 50 of them outlast a shutdown's grace period.
        await asyncio.gather(*(stream.remove() for stream in streams), return_exceptions=True)
        await asyncio.gather(*pumps, return_exceptions=True)
        if state is not None:
            with contextlib.suppress(Exception):
                await _kill_marked(engine, state, nodes)
        for item in items:
            if item["status"] in ("starting", "running"):
                item.update(status="stopped", ended_at=_now())
        if marked_monitor:
            monitor.mark(topo.id, "background", f"Background run ended ({stopped_by or 'failed'})")
        _ACTIVE.pop(job_id, None)
        publish(final=True)


def register(runner: JobRunner) -> None:
    runner.register(KIND, run_background, cancellable=True, stoppable=True)
