"""Topology CRUD + JSON import."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from auth import require_any_auth, require_instructor
from database import get_db
from models import Topology
from schemas import TopologyCreate, TopologyRecord, TopologySummary, TopologyUpdate

router = APIRouter(prefix="/api/topologies", tags=["topologies"])


@router.get("", response_model=list[TopologySummary])
def list_topologies(db: Session = Depends(get_db), _=Depends(require_any_auth)):
    return db.query(Topology).order_by(Topology.updated_at.desc()).all()


@router.post("", response_model=TopologyRecord, status_code=201)
def create_topology(
    body: TopologyCreate, db: Session = Depends(get_db), _=Depends(require_instructor)
):
    topo = Topology(name=body.name, data=body.data)
    db.add(topo)
    db.commit()
    db.refresh(topo)
    return topo


@router.post("/import-json", response_model=TopologyRecord, status_code=201)
async def import_json_topology(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(require_instructor),
):
    try:
        data = json.loads((await file.read()).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(400, f"Invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(400, "Invalid JSON: expected an object")

    topology_data = data.get("topology") if isinstance(data.get("topology"), dict) else data
    name = (
        data.get("name")
        or topology_data.get("name")
        or (file.filename or "").removesuffix(".json")
        or "Imported Topology"
    )
    topo = Topology(name=name, data=topology_data)
    db.add(topo)
    db.commit()
    db.refresh(topo)
    return topo


@router.get("/{topology_id}", response_model=TopologyRecord)
def get_topology(topology_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    topo = db.get(Topology, topology_id)
    if not topo:
        raise HTTPException(404, "Topology not found")
    return topo


@router.put("/{topology_id}", response_model=TopologyRecord)
def update_topology(
    topology_id: str,
    body: TopologyUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_instructor),
):
    topo = db.get(Topology, topology_id)
    if not topo:
        raise HTTPException(404, "Topology not found")
    if body.name is not None:
        topo.name = body.name
    if body.data is not None:
        topo.data = body.data
    db.commit()
    db.refresh(topo)
    return topo


@router.delete("/{topology_id}", status_code=204)
def delete_topology(topology_id: str, db: Session = Depends(get_db), _=Depends(require_instructor)):
    topo = db.get(Topology, topology_id)
    if not topo:
        raise HTTPException(404, "Topology not found")
    db.delete(topo)
    db.commit()
