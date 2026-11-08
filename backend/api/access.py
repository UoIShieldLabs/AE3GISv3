"""What a caller may do with a topology or a job (classroom mode).

Two levels on a topology:

- **view** (the record, its export, copying it): its owner, the instructor,
  or any student when the topology is published.
- **own** (everything else: edit, delete, deploy, destroy, runtime, events,
  jobs, captures, traffic, monitors, scenarios, web UIs, terminals): its owner
  or the instructor.

``Topology.owner_id`` is the owning student, None for the instructor. A student
gets 404 for a topology they cannot see, so its existence is not leaked, and
403 ``not_owner`` for an own-level call on a published one (they work on a copy).

A job follows its topology (own level). Jobs without one: image builds and
source / registry syncs are readable by anyone signed in; everything else
(benchmarks, purges) and cancelling or stopping them is the instructor's.

With accounts off every caller is the instructor, so all of this allows.
"""

from __future__ import annotations

import asyncio

from fastapi import Depends, WebSocket
from sqlalchemy.orm import Session

from api.deps import get_db
from api.errors import Forbidden, NotFound
from auth import current_identity, ws_identity
from db.models import Job, Topology
from services.accounts import Identity

# Topology-less job kinds any signed-in caller may read (a deploy's images step
# joins builds; the UI follows their logs).
SHARED_JOB_KINDS = ("build", "sync_source", "sync_registry")


def can_view(identity: Identity, topo: Topology) -> bool:
    return can_own(identity, topo) or bool(topo.published)


def can_own(identity: Identity, topo: Topology) -> bool:
    if identity.is_instructor:
        return True
    return topo.owner_id is not None and topo.owner_id == identity.user_id


def check_view(identity: Identity, topo: Topology | None) -> Topology:
    if topo is None or not can_view(identity, topo):
        raise NotFound("Topology")
    return topo


def check_own(identity: Identity, topo: Topology | None) -> Topology:
    if topo is not None and can_own(identity, topo):
        return topo
    if topo is not None and can_view(identity, topo):
        raise Forbidden(
            "This topology is your instructor's; open it from the library to get your own copy",
            code="not_owner",
        )
    raise NotFound("Topology")


def visible_topology(
    topology_id: str,
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
) -> Topology:
    return check_view(identity, db.get(Topology, topology_id))


def owned_topology(
    topology_id: str,
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
) -> Topology:
    return check_own(identity, db.get(Topology, topology_id))


def check_job(db: Session, identity: Identity, job: Job | None, *, write: bool) -> Job:
    if job is None:
        raise NotFound("Job")
    if identity.is_instructor:
        return job
    if job.topology_id:
        topo = db.get(Topology, job.topology_id)
        if topo is None or not can_own(identity, topo):
            raise NotFound("Job")
        return job
    if job.kind not in SHARED_JOB_KINDS:
        raise NotFound("Job")
    if write:
        raise Forbidden("Only the instructor can do this", code="instructor_only")
    return job


def readable_job(
    job_id: str,
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
) -> Job:
    return check_job(db, identity, db.get(Job, job_id), write=False)


def writable_job(
    job_id: str,
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
) -> Job:
    return check_job(db, identity, db.get(Job, job_id), write=True)


# ── WebSockets ──────────────────────────────────────────────────────

WS_UNAUTHORIZED = 4003
WS_NOT_FOUND = 4004


async def ws_access(websocket: WebSocket, token: str | None, topology_id: str) -> int:
    """0 when the caller may use the topology's WebSockets (own level), else
    the close code: 4003 for a missing or bad token, 4004 when the topology is
    not theirs (or does not exist)."""

    def check() -> int:
        with websocket.app.state.session_factory() as db:
            identity = ws_identity(websocket, token, db)
            if identity is None:
                return WS_UNAUTHORIZED
            topo = db.get(Topology, topology_id)
            if topo is not None and not can_own(identity, topo):
                return WS_NOT_FOUND
            return 0

    return await asyncio.to_thread(check)


async def ws_guard(websocket: WebSocket, token: str | None, topology_id: str) -> bool:
    """Close the upgrade (before accepting) unless ``ws_access`` allows it."""
    code = await ws_access(websocket, token, topology_id)
    if code:
        await websocket.close(
            code=code, reason="Forbidden" if code == WS_UNAUTHORIZED else "Not found"
        )
        return False
    return True
