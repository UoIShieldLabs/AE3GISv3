"""Helpers shared by the tool modules: resolving a topology or job the caller may
touch (through ``api.access``), and the topology argument most tools take."""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api import access
from api.errors import Invalid
from db.models import Job, Topology
from services.agent.tools.base import ToolContext


class TopologyArg(BaseModel):
    topology_id: str | None = Field(
        default=None,
        description="The topology's id. Omit to use the one the user has open.",
        max_length=64,
    )


def topology_id(ctx: ToolContext, given: str | None) -> str:
    tid = (given or ctx.topology_id or "").strip()
    if not tid:
        raise Invalid(
            "Which topology? Give topology_id (list_topologies shows them)", code="no_topology"
        )
    return tid


def view_topology(db: Session, ctx: ToolContext, given: str | None) -> Topology:
    return access.check_view(db, ctx.identity, db.get(Topology, topology_id(ctx, given)))


def own_topology(db: Session, ctx: ToolContext, given: str | None) -> Topology:
    return access.check_own(db, ctx.identity, db.get(Topology, topology_id(ctx, given)))


def job_for(db: Session, ctx: ToolContext, job_id: str, *, write: bool = False) -> Job:
    return access.check_job(db, ctx.identity, db.get(Job, job_id), write=write)


def ui_topology_changed(topo: Topology) -> dict:
    return {"type": "topology_changed", "topology_id": topo.id, "version": topo.version}


def ui_runtime_changed(topology_id: str) -> dict:
    return {"type": "runtime_changed", "topology_id": topology_id}
