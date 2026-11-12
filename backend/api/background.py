"""Background runs: commands kept running in lab nodes (a tutorial's background
traffic). Start one, list them, read one; stop via ``POST /jobs/{id}/stop``."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.access import owned_topology, readable_job
from api.deps import get_db, get_runner
from api.errors import NotFound
from api.schemas import BackgroundRunOut, BackgroundRunRequest
from db.models import Job, Topology
from services import background, jobs, topologies
from services.jobs import JobRunner

router = APIRouter(prefix="/api/v1", tags=["background"])


def run_out(job: Job, *, full: bool = True) -> dict[str, Any]:
    """A run; listings (``full=False``) leave out the items."""
    params = job.params or {}
    result = job.result or {}
    items: list[dict[str, Any]] = []
    if full:
        items = background.active_items(job.id) or list(result.get("items") or [])
        if not items:  # queued, or failed before it started anything
            state = "starting" if job.is_active else "stopped"
            items = [{**i, "status": state} for i in params.get("items") or []]
        if not job.is_active:
            # A run cut short (cancelled at shutdown, a restart) may not have
            # recorded its last state: nothing of a finished run still runs.
            items = [
                {**i, "status": "stopped"} if i.get("status") in ("starting", "running") else i
                for i in items
            ]
    return {
        "id": job.id,
        "topology_id": job.topology_id,
        "label": params.get("label") or "",
        "tag": params.get("tag") or "",
        "status": job.status,
        "live": job.is_active,
        "node_ids": list(params.get("node_ids") or []),
        "items": items,
        "stopped_by": result.get("stopped_by"),
        "job": jobs.job_to_dict(job),
    }


@router.post(
    "/topologies/{topology_id}/background/runs", response_model=BackgroundRunOut, status_code=202
)
def start_run(
    topology_id: str,
    body: BackgroundRunRequest,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    _: Topology = Depends(owned_topology),
):
    """Start commands that keep running in their nodes until the run is stopped
    (``POST /jobs/{id}/stop``). One run at a time per topology (409
    ``background_active``); the topology must be deployed (409 ``bad_state``)."""
    topo = topologies.get_or_404(db, topology_id)
    return run_out(background.start_run(db, runner, topo, body.model_dump()))


@router.get("/topologies/{topology_id}/background/runs", response_model=list[BackgroundRunOut])
def list_runs(
    topology_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: Topology = Depends(owned_topology),
):
    topologies.get_or_404(db, topology_id)
    return [
        run_out(j, full=False)
        for j in jobs.list_jobs(db, topology_id, limit, kinds=(background.KIND,))
    ]


@router.get("/background/runs/{job_id}", response_model=BackgroundRunOut)
def get_run(job_id: str, db: Session = Depends(get_db), _: Job = Depends(readable_job)):
    """A run with every item's state: live while it runs, final afterwards."""
    job = db.get(Job, job_id)
    if not job or job.kind != background.KIND:
        raise NotFound("Background run")
    return run_out(job)
