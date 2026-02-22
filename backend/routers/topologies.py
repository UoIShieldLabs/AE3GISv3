from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import (
    AuthIdentity,
    StudentIdentity,
    require_any_auth,
    require_instructor,
    validate_student_topology,
)
from database import get_db
from models import Topology
from schemas import TopologyCreate, TopologyRecord, TopologySummary, TopologyUpdate
from services import clab_manager

router = APIRouter(prefix="/api/topologies", tags=["topologies"])


@router.get("", response_model=list[TopologySummary])
def list_topologies(
    db: Session = Depends(get_db),
    identity: AuthIdentity = Depends(require_any_auth),
):
    if isinstance(identity, StudentIdentity):
        topo = db.get(Topology, identity.topology_id)
        return [topo] if topo else []
    return db.query(Topology).order_by(Topology.updated_at.desc()).all()


@router.post("", response_model=TopologyRecord, status_code=201)
def create_topology(
    body: TopologyCreate,
    db: Session = Depends(get_db),
    _=Depends(require_instructor),
):
    topo = Topology(
        name=body.name,
        data=body.data.model_dump(by_alias=True),
    )
    db.add(topo)
    db.commit()
    db.refresh(topo)
    return topo


@router.get("/{topology_id}", response_model=TopologyRecord)
def get_topology(
    topology_id: str,
    db: Session = Depends(get_db),
    identity: AuthIdentity = Depends(require_any_auth),
):
    validate_student_topology(identity, topology_id)
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
        topo.data = body.data.model_dump(by_alias=True)
    db.commit()
    db.refresh(topo)
    return topo


@router.delete("/{topology_id}", status_code=204)
def delete_topology(
    topology_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_instructor),
):
    topo = db.get(Topology, topology_id)
    if not topo:
        raise HTTPException(404, "Topology not found")
    topo_name = clab_manager.deployment_name(topology_id, topo.data)
    db.delete(topo)
    db.commit()
    # Remove YAML file and clab working directory
    clab_manager.cleanup(topology_id, topo_name)
