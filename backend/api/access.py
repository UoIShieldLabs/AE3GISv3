"""What a caller may do with a topology or a job (accounts on).

Two levels on a topology:

- **own** (edit, delete, deploy, destroy, runtime, events, jobs, captures,
  traffic, monitors, scenarios, web UIs, terminals): its owner; the staff
  member whose class its owner (a student) is in; any admin.
- **view** (the record, its export, copying it): whoever owns it, and the
  students of its owner when it is published (a lesson).

``Topology.owner_id`` is the user who owns it (None only with accounts off:
an admin's). Staff topologies are private to their owner and the admins. A
caller gets 404 for a topology they cannot see, so its existence is not
leaked, and 403 ``not_owner`` for an own-level call on a lesson (a student
works on a copy).

A job follows its topology (own level). Jobs without one: image builds and
source / registry syncs are readable by anyone signed in; cancelling or
stopping a build or source sync is for staff, everything else (registry
syncs, benchmarks, purges) for admins.

With accounts off every caller is an admin, so all of this allows.
"""

from __future__ import annotations

import asyncio

from fastapi import Depends, WebSocket
from sqlalchemy.orm import Session

from api.deps import get_db
from api.errors import Forbidden, NotFound
from auth import current_identity, ws_identity
from db.models import Job, Topology
from services.accounts import Identity, teacher_of

# Topology-less job kinds any signed-in caller may read (a deploy's images step
# joins builds; the UI follows their logs).
SHARED_JOB_KINDS = ("build", "sync_source", "sync_registry")
# Of those, the ones staff (not only admins) may cancel or stop.
STAFF_JOB_KINDS = ("build", "sync_source")


def can_own(db: Session, identity: Identity, topo: Topology) -> bool:
    if identity.is_admin:
        return True
    if topo.owner_id is None:
        return False
    if topo.owner_id == identity.user_id:
        # A retired lesson copy (its lesson was unpublished) is gone for its student.
        return topo.retired_at is None
    return identity.is_staff and teacher_of(db, topo.owner_id) == identity.user_id


def can_view(db: Session, identity: Identity, topo: Topology) -> bool:
    if can_own(db, identity, topo):
        return True
    return (
        bool(topo.published)
        and topo.retired_at is None
        and identity.instructor_id is not None
        and topo.owner_id == identity.instructor_id
    )


def check_view(db: Session, identity: Identity, topo: Topology | None) -> Topology:
    if topo is None or not can_view(db, identity, topo):
        raise NotFound("Topology")
    return topo


def check_own(db: Session, identity: Identity, topo: Topology | None) -> Topology:
    if topo is not None and can_own(db, identity, topo):
        return topo
    if topo is not None and can_view(db, identity, topo):
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
    return check_view(db, identity, db.get(Topology, topology_id))


def owned_topology(
    topology_id: str,
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
) -> Topology:
    return check_own(db, identity, db.get(Topology, topology_id))


def check_job(db: Session, identity: Identity, job: Job | None, *, write: bool) -> Job:
    if job is None:
        raise NotFound("Job")
    if identity.is_admin:
        return job
    if job.topology_id:
        topo = db.get(Topology, job.topology_id)
        if topo is None or not can_own(db, identity, topo):
            raise NotFound("Job")
        return job
    if job.kind not in SHARED_JOB_KINDS:
        raise NotFound("Job")
    if write and not (identity.is_staff and job.kind in STAFF_JOB_KINDS):
        if identity.is_staff:
            raise Forbidden("Only an admin can do this", code="admin_only")
        raise Forbidden("Only an instructor can do this", code="staff_only")
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
            if topo is not None and not can_own(db, identity, topo):
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
