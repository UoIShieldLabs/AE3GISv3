"""Topology CRUD, versioning, diagnostics, plan access; copies and publishing.

Accounts: a topology's ``owner_id`` is the user who owns it (None only with
accounts off). Staff publish their topologies to their students; a student
works on a copy (``copy_for``), one per published topology, which remembers the
source and the source version it was taken from so ``reset_from_source`` can
bring it up to date. Who may call what is ``api.access``.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy import update as sql_update
from sqlalchemy.orm import Session

from api.errors import Conflict, Invalid, NotFound
from db.models import STAFF_ROLES, Topology, User, utcnow
from domain import saved_state, validation
from domain.plan import LabPlan, build_lab_plan
from domain.validation import Diagnostic
from engine.kathara.naming import lab_name
from services import events, jobs
from services.accounts import Identity, holds_lab, owner_out, owners, student_ids_of


def get_or_404(db: Session, topology_id: str) -> Topology:
    topo = db.get(Topology, topology_id)
    if not topo:
        raise NotFound("Topology")
    return topo


def list_all(db: Session) -> list[Topology]:
    return list(db.scalars(select(Topology).order_by(Topology.updated_at.desc())))


def list_visible(db: Session, identity: Identity) -> list[Topology]:
    """Everything for an admin; an instructor's own and their students'; a
    student's own plus what their instructor published. Retired lesson copies
    (on their way out) are nobody's."""
    stmt = (
        select(Topology).where(Topology.retired_at.is_(None)).order_by(Topology.updated_at.desc())
    )
    if identity.is_admin:
        pass
    elif identity.is_staff:
        stmt = stmt.where(
            or_(
                Topology.owner_id == identity.user_id,
                Topology.owner_id.in_(student_ids_of(identity.user_id)),
            )
        )
    elif identity.instructor_id:
        lessons = Topology.published.is_(True) & (Topology.owner_id == identity.instructor_id)
        stmt = stmt.where(or_(Topology.owner_id == identity.user_id, lessons))
    else:
        stmt = stmt.where(Topology.owner_id == identity.user_id)
    return list(db.scalars(stmt))


def summary_meta(db: Session, topos: list[Topology]) -> dict[str, dict[str, Any]]:
    """The account fields of each topology's summary (owner, published, source,
    update_available), in two queries for any number of topologies."""
    known = owners(db, {t.owner_id for t in topos if t.owner_id})
    source_ids = {t.source_id for t in topos if t.source_id}
    versions: dict[str, int] = {}
    if source_ids:
        rows = db.execute(select(Topology.id, Topology.version).where(Topology.id.in_(source_ids)))
        versions = dict(rows.all())
    meta: dict[str, dict[str, Any]] = {}
    for t in topos:
        owner = owner_out(known, t.owner_id)
        source_version = versions.get(t.source_id) if t.source_id else None
        meta[t.id] = {
            "owner": owner,
            "published": bool(t.published),
            "source_id": t.source_id,
            "update_available": source_version is not None
            and source_version > (t.source_version or 0),
            "holds_lab": holds_lab(t),
        }
    return meta


def diagnostics_for(data: Any) -> list[Diagnostic]:
    return validation.validate(data)


def data_with_name(topo: Topology) -> dict[str, Any]:
    """The stored JSON plus the record's display name (the frontend keeps both)."""
    return {**(topo.data or {}), "name": topo.name}


def plan_for(topo: Topology, *, iface_base: int = 0) -> LabPlan:
    return build_lab_plan(data_with_name(topo), lab_name(topo.id), iface_base=iface_base)


def create(
    db: Session,
    *,
    name: str,
    data: dict[str, Any],
    owner_id: str | None = None,
    source: Topology | None = None,
) -> tuple[Topology, list[Diagnostic]]:
    topo = Topology(
        name=name.strip() or "Untitled topology",
        data=data,
        version=1,
        owner_id=owner_id,
        source_id=source.id if source else None,
        source_version=source.version if source else None,
    )
    db.add(topo)
    events.record(db, type="topology.created", message=f"Created '{topo.name}'", topology_id=None)
    db.commit()
    db.refresh(topo)
    # Attach the id now that we have one (the record above had none yet).
    return topo, diagnostics_for(data)


def update(
    db: Session,
    topo: Topology,
    *,
    name: str | None = None,
    data: dict[str, Any] | None = None,
    expected_version: int | None = None,
) -> tuple[Topology, list[Diagnostic]]:
    if expected_version is not None and expected_version != topo.version:
        raise Conflict(
            "This topology was changed elsewhere; reload before saving",
            code="version_conflict",
            current_version=topo.version,
        )
    changed = False
    if name is not None and name.strip() and name.strip() != topo.name:
        topo.name = name.strip()
        changed = True
    if data is not None and data != topo.data:
        topo.data = data
        changed = True
    if changed:
        topo.version += 1
        if topo.status == "deployed":
            events.record(
                db,
                type="topology.edited_while_deployed",
                level="warning",
                message="Topology edited while deployed; the running lab no longer matches the saved design",
                topology_id=topo.id,
            )
        db.commit()
        db.refresh(topo)
    return topo, diagnostics_for(topo.data)


def delete(db: Session, topo: Topology) -> list[str]:
    """Delete a topology; returns the students' lesson copies it retired."""
    if jobs.active_job(db, topo.id):
        raise Conflict(
            "A job is running for this topology; wait for it to finish", code="job_active"
        )
    if topo.status in ("deployed", "deploying", "destroying"):
        raise Conflict("Destroy the deployment before deleting the topology", code="deployed")
    # Students' lesson copies go with it (the caller settles them: services.lessons).
    retired = retire_copies(db, topo)
    db.delete(topo)
    db.commit()
    return retired


def import_json(
    db: Session, raw: bytes, filename: str | None, *, owner_id: str | None = None
) -> tuple[Topology, list[Diagnostic]]:
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise Invalid(f"Invalid JSON: {exc}", code="invalid_json") from exc
    if not isinstance(parsed, dict):
        raise Invalid("Invalid JSON: expected an object", code="invalid_json")
    data = parsed.get("topology") if isinstance(parsed.get("topology"), dict) else parsed
    name = (
        parsed.get("name")
        or data.get("name")
        or (filename or "").removesuffix(".json")
        or "Imported topology"
    )
    return create(db, name=str(name), data=data, owner_id=owner_id)


# ── copies and publishing (classroom mode) ──────────────────────────


def copy_for(
    db: Session, identity: Identity, source: Topology, *, duplicate: bool = False
) -> tuple[Topology, bool]:
    """A copy of ``source`` for the caller; returns (topology, created).

    A student opening a published topology (a lesson) that is not theirs gets
    their lesson copy: the one they started, else a new one linked to the
    lesson. It lives as long as the lesson stays published (``retire_copies``).
    ``duplicate``, or anyone else copying (staff, a student their own), makes a
    plain, unlinked duplicate that the caller owns.
    """
    personal = not duplicate and identity.is_student and source.owner_id != identity.user_id
    if personal:
        existing = db.scalar(
            select(Topology)
            .where(
                Topology.owner_id == identity.user_id,
                Topology.source_id == source.id,
                Topology.retired_at.is_(None),
            )
            .order_by(Topology.created_at)
        )
        if existing is not None:
            return existing, False
        topo, _ = create(
            db,
            name=source.name,
            data=copy.deepcopy(source.data or {}),
            owner_id=identity.user_id,
            source=source,
        )
        events.record(
            db,
            type="topology.copied",
            message=f"Copied from '{source.name}' (v{source.version})",
            topology_id=topo.id,
            data={"source_id": source.id, "source_version": source.version},
        )
        db.commit()
        return topo, True
    topo, _ = create(
        db,
        name=f"{source.name} (copy)",
        data=copy.deepcopy(source.data or {}),
        owner_id=identity.owner_id,
    )
    return topo, True


def reset_from_source(db: Session, topo: Topology, source: Topology) -> list[str]:
    """Replace a copy's design with its source's current one. Its lab must be
    down; its saved state goes (returned: the snapshot images to remove)."""
    if jobs.active_job(db, topo.id):
        raise Conflict("A job is already running for this topology", code="job_active")
    if holds_lab(topo):
        raise Conflict("Destroy the lab before resetting it", code="bad_state", status=topo.status)
    refs = saved_state.refs(topo.saved_state)
    topo.saved_state = None
    topo.data = copy.deepcopy(source.data or {})
    topo.name = source.name
    topo.source_version = source.version
    topo.version += 1
    if topo.status == "error":
        topo.status = "idle"
    events.record(
        db,
        type="topology.reset",
        message=f"Reset to '{source.name}' v{source.version}",
        topology_id=topo.id,
        data={"source_id": source.id, "source_version": source.version},
    )
    db.commit()
    db.refresh(topo)
    return refs


def retire_copies(db: Session, source: Topology) -> list[str]:
    """Hide every student's lesson copy of ``source`` (unpublished or deleted):
    returns their ids for ``services.lessons.schedule``, which destroys their
    labs and deletes them. A republished lesson starts students afresh."""
    ids = list(
        db.scalars(
            select(Topology.id).where(
                Topology.source_id == source.id,
                Topology.retired_at.is_(None),
            )
        )
    )
    if ids:
        db.execute(sql_update(Topology).where(Topology.id.in_(ids)).values(retired_at=utcnow()))
        events.record(
            db,
            type="lesson.copies_retired",
            message=f"Removed {len(ids)} student cop{'y' if len(ids) == 1 else 'ies'}",
            topology_id=source.id,
            data={"copies": ids},
        )
    return ids


def retired_ids(db: Session) -> list[str]:
    return list(db.scalars(select(Topology.id).where(Topology.retired_at.is_not(None))))


def check_publishable(db: Session, topo: Topology) -> None:
    """Only a staff member's topology is a lesson (a student's is not)."""
    if topo.owner_id is None:
        return
    owner = db.get(User, topo.owner_id)
    if owner is None or owner.role not in STAFF_ROLES:
        raise Conflict(
            "Only an instructor's own topology can be published; duplicate it first",
            code="not_publishable",
        )


def set_published(db: Session, topo: Topology, published: bool) -> list[str]:
    """Publish or unpublish; returns the lesson copies retired by unpublishing."""
    retired: list[str] = []
    if bool(topo.published) != published:
        topo.published = published
        if not published:
            retired = retire_copies(db, topo)
        events.record(
            db,
            type="topology.published" if published else "topology.unpublished",
            message="Published to students" if published else "No longer published",
            topology_id=topo.id,
        )
        db.commit()
        db.refresh(topo)
    return retired
