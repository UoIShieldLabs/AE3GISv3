"""Job lookup, logs and cancellation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db, get_runner
from api.errors import Conflict, NotFound
from api.schemas import JobLogOut, JobOut
from auth import require_any_auth, require_instructor
from db.models import Job
from services import jobs, topologies
from services.jobs import JobRunner

router = APIRouter(prefix="/api/v1", tags=["jobs"])


def _get_job(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise NotFound("Job")
    return job


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    return jobs.job_to_dict(_get_job(db, job_id))


@router.get("/jobs/{job_id}/log", response_model=JobLogOut)
def get_job_log(
    job_id: str,
    offset: int | None = Query(default=None, ge=0, description="Omit to read the tail"),
    limit: int = Query(default=65536, ge=1024, le=1_048_576),
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_any_auth),
):
    """A slice of the job's log. ``done`` turns true once the job has finished
    and the slice reaches the end of the log."""
    job = _get_job(db, job_id)
    chunk = runner.logs.read(job.id, offset, limit)
    return JobLogOut(
        offset=chunk.offset,
        next_offset=chunk.next_offset,
        size=chunk.size,
        text=chunk.text,
        done=not job.is_active and chunk.next_offset >= chunk.size,
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobOut, status_code=202)
async def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_instructor),
):
    """Cancel a queued or running job. Deploys can only be cancelled before the
    engine starts creating containers; destroys cannot be cancelled."""
    job = _get_job(db, job_id)
    # Async on purpose: runs on the app loop, so it cannot interleave with the job.
    if not runner.cancel(job.id):
        raise Conflict("This job can't be cancelled now", code="not_cancellable")
    db.refresh(job)
    return jobs.job_to_dict(job)


@router.get("/topologies/{topology_id}/jobs", response_model=list[JobOut])
def list_topology_jobs(
    topology_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)
):
    topologies.get_or_404(db, topology_id)
    return [jobs.job_to_dict(j) for j in jobs.list_jobs(db, topology_id)]
