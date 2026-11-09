"""Retired lesson copies: destroy their labs, then delete them, in the background.

When the instructor unpublishes or deletes a lesson, every student's copy of it
is retired at once (``topologies.retire_copies``: hidden from everyone, students
included). This finishes the job without holding the request: per copy, wait
for a running job, destroy a lab that is still up (without saving), then delete
the row and its saved-state images. A republished lesson starts students
afresh; what a student duplicated is theirs and stays.

A copy whose destroy keeps failing is left (still retired, its lab listed in
the Class sheet) for the next start, when ``resume`` tries again.
"""

from __future__ import annotations

import asyncio
import logging

from api.errors import Conflict
from db.models import Topology
from domain import saved_state
from engine.base import DeploymentEngine
from services import deployment, jobs, topologies
from services.accounts import holds_lab
from services.jobs import JobRunner

log = logging.getLogger(__name__)

MAX_DESTROYS = 3
MAX_ROUNDS = 40
RETRY_S = 0.5


async def settle(runner: JobRunner, engine: DeploymentEngine, topology_id: str) -> None:
    destroys = 0
    for _ in range(MAX_ROUNDS):
        wait_for: str | None = None
        removed: list[str] | None = None
        with runner.session_factory() as db:
            topo = db.get(Topology, topology_id)
            if topo is None or topo.retired_at is None:
                return
            job = jobs.active_job(db, topo.id)
            if job is not None:
                wait_for = job.id
            elif holds_lab(topo):
                if destroys >= MAX_DESTROYS:
                    log.warning("Retired copy %s: destroy keeps failing; left for restart", topo.id)
                    return
                destroys += 1
                try:
                    wait_for = deployment.start_destroy(db, runner, topo, save=False).id
                except Conflict:
                    wait_for = None  # raced with another request: look again
            else:
                refs = saved_state.refs(topo.saved_state)
                try:
                    topologies.delete(db, topo)
                    removed = refs
                except Conflict:
                    removed = None
        if removed is not None:
            await engine.remove_images(removed)
            return
        if wait_for:
            await runner.wait(wait_for)
        else:
            await asyncio.sleep(RETRY_S)
    log.warning("Retired copy %s: gave up settling; left for restart", topology_id)


async def _settle_logged(runner: JobRunner, engine: DeploymentEngine, topology_id: str) -> None:
    try:
        await settle(runner, engine, topology_id)
    except Exception:  # pragma: no cover - defensive: never kill the loop
        log.exception("Retired copy %s: settling failed", topology_id)


def schedule(runner: JobRunner, engine: DeploymentEngine, ids: list[str]) -> None:
    """Settle these retired copies in the background (call on the app loop)."""
    for topology_id in ids:
        runner.spawn(_settle_logged(runner, engine, topology_id), name=f"retire:{topology_id}")


def resume(runner: JobRunner, engine: DeploymentEngine) -> int:
    """At startup: settle copies retired before a restart."""
    with runner.session_factory() as db:
        ids = topologies.retired_ids(db)
    schedule(runner, engine, ids)
    return len(ids)
