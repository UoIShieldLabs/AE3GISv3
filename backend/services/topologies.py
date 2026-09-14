"""Topology CRUD, versioning, diagnostics, and plan access."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.errors import Conflict, Invalid, NotFound
from db.models import Topology
from domain import validation
from domain.plan import LabPlan, build_lab_plan
from domain.validation import Diagnostic
from engine.kathara.naming import lab_name
from services import events, jobs


def get_or_404(db: Session, topology_id: str) -> Topology:
    topo = db.get(Topology, topology_id)
    if not topo:
        raise NotFound("Topology")
    return topo


def list_all(db: Session) -> list[Topology]:
    return list(db.scalars(select(Topology).order_by(Topology.updated_at.desc())))


def diagnostics_for(data: Any) -> list[Diagnostic]:
    return validation.validate(data)


def data_with_name(topo: Topology) -> dict[str, Any]:
    """The stored JSON plus the record's display name (the frontend keeps both)."""
    return {**(topo.data or {}), "name": topo.name}


def plan_for(topo: Topology, *, iface_base: int = 0) -> LabPlan:
    return build_lab_plan(data_with_name(topo), lab_name(topo.id), iface_base=iface_base)


def create(db: Session, *, name: str, data: dict[str, Any]) -> tuple[Topology, list[Diagnostic]]:
    topo = Topology(name=name.strip() or "Untitled topology", data=data, version=1)
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


def delete(db: Session, topo: Topology) -> None:
    if jobs.active_job(db, topo.id):
        raise Conflict(
            "A job is running for this topology; wait for it to finish", code="job_active"
        )
    if topo.status in ("deployed", "deploying", "destroying"):
        raise Conflict("Destroy the deployment before deleting the topology", code="deployed")
    db.delete(topo)
    db.commit()


def import_json(db: Session, raw: bytes, filename: str | None) -> tuple[Topology, list[Diagnostic]]:
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
    return create(db, name=str(name), data=data)
