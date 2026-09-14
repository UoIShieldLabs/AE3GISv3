"""Compare what the engine is running with what the DB believes.

- tracked: a lab whose hash matches a topology's engine_state
- orphan:  a lab on the engine that no topology references
- stale:   a topology marked deployed whose lab has no machines any more
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Topology
from engine.base import DeploymentEngine, EngineState
from engine.kathara.naming import lab_hash as hash_for_name
from services import events


def _state_hash(topo: Topology) -> str | None:
    state = EngineState.from_dict(topo.engine_state)
    if not state:
        return None
    return state.lab_hash or hash_for_name(state.lab_name)


async def report(db: Session, engine: DeploymentEngine) -> dict[str, Any]:
    labs = await engine.list_labs()
    topos = list(db.scalars(select(Topology)))
    by_hash: dict[str, Topology] = {}
    for t in topos:
        h = _state_hash(t)
        if h:
            by_hash[h] = t

    lab_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for lab in labs:
        seen.add(lab.lab_hash)
        t = by_hash.get(lab.lab_hash)
        lab_rows.append(
            {
                **lab.to_dict(),
                "classification": "tracked" if t else "orphan",
                "topology_id": t.id if t else None,
                "topology_name": t.name if t else None,
            }
        )

    stale = [
        {"topology_id": t.id, "topology_name": t.name, "lab_hash": h}
        for h, t in by_hash.items()
        if h not in seen and t.status in ("deployed", "error")
    ]
    return {"labs": lab_rows, "stale": stale}


async def apply(db: Session, engine: DeploymentEngine) -> dict[str, Any]:
    """Mark stale topologies idle. Orphans are only reported (purge is explicit)."""
    rep = await report(db, engine)
    for item in rep["stale"]:
        topo = db.get(Topology, item["topology_id"])
        if not topo:
            continue
        topo.status = "idle"
        topo.engine_state = None
        events.record(
            db,
            type="reconcile.stale",
            level="warning",
            message="No lab found on the engine for this deployment; status reset to idle",
            topology_id=topo.id,
            data={"lab_hash": item["lab_hash"]},
        )
    db.commit()
    return {
        "reset": len(rep["stale"]),
        "orphans": sum(1 for lab in rep["labs"] if lab["classification"] == "orphan"),
    }


async def purge(db: Session, engine: DeploymentEngine, lab_hash: str) -> dict[str, Any]:
    await engine.purge(lab_hash)
    affected = None
    for topo in db.scalars(select(Topology)):
        if _state_hash(topo) == lab_hash:
            affected = topo
            topo.status = "idle"
            topo.engine_state = None
            events.record(
                db,
                type="reconcile.purged",
                level="warning",
                message="Lab purged from the engine",
                topology_id=topo.id,
                data={"lab_hash": lab_hash},
            )
    db.commit()
    return {"lab_hash": lab_hash, "topology_id": affected.id if affected else None}
