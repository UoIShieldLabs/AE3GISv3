"""Job lookup."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db
from api.errors import NotFound
from api.schemas import JobOut
from auth import require_any_auth
from db.models import Job
from services import jobs, topologies

router = APIRouter(prefix="/api/v1", tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    job = db.get(Job, job_id)
    if not job:
        raise NotFound("Job")
    return jobs.job_to_dict(job)


@router.get("/topologies/{topology_id}/jobs", response_model=list[JobOut])
def list_topology_jobs(
    topology_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)
):
    topologies.get_or_404(db, topology_id)
    return [jobs.job_to_dict(j) for j in jobs.list_jobs(db, topology_id)]
