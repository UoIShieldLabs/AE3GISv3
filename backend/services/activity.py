"""Open-ended jobs running against a deployed topology (captures, traffic).

They serialise on their own subjects, so they never block deploy or destroy
and never show up as the topology's ``active_job``. The runtime view lists
them as ``activity`` (the canvas badges links and nodes from it), and destroy
stops them first so each keeps what it recorded before the lab goes away.

Handlers record ``node_ids`` and ``connection_ids`` in their job's params.
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.orm import Session

from db.models import Job
from services import jobs
from services.jobs import JobRunner

LIVE_KINDS: tuple[str, ...] = ("capture", "traffic")


def activity_dict(job: Job) -> dict[str, Any]:
    params = job.params or {}
    running = next((s for s in reversed(job.steps or []) if s.get("status") == "running"), None)
    return {
        "job_id": job.id,
        "kind": job.kind,
        "status": job.status,
        "label": params.get("label") or "",
        "node_ids": list(params.get("node_ids") or []),
        "connection_ids": list(params.get("connection_ids") or []),
        "started_at": job.started_at or job.created_at,
        "message": running.get("message") if running else None,
    }


def active_for_topology(db: Session, topology_id: str) -> list[dict[str, Any]]:
    return [activity_dict(j) for j in jobs.active_jobs(db, topology_id, kinds=LIVE_KINDS)]


async def stop_all(runner: JobRunner, topology_id: str, *, timeout: float = 15.0) -> int:
    """Stop every capture/traffic job of a topology and wait for them; returns how many.

    Jobs still running after ``timeout`` are cancelled.
    """
    with runner.session_factory() as db:
        ids = [j.id for j in jobs.active_jobs(db, topology_id, kinds=LIVE_KINDS)]
    if not ids:
        return 0
    for job_id in ids:
        if not runner.request_stop(
            job_id, "Stopping: the topology is being destroyed", code="destroy"
        ):
            runner.cancel(job_id, "Cancelled: the topology is being destroyed")
    waits = [asyncio.ensure_future(runner.wait(j)) for j in ids]
    _, pending = await asyncio.wait(waits, timeout=timeout)
    if pending:
        for w in pending:
            w.cancel()
        for job_id in ids:
            runner.cancel(job_id, "Cancelled: the topology is being destroyed")
        await asyncio.wait([asyncio.ensure_future(runner.wait(j)) for j in ids], timeout=timeout)
    return len(ids)
