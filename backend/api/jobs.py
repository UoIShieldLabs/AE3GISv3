"""Job lookup, logs, cancellation and stopping."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.deps import get_artifacts, get_db, get_runner
from api.errors import Conflict, NotFound
from api.schemas import ArtifactOut, JobLogOut, JobOut
from auth import require_any_auth, require_instructor
from db.models import Job
from services import jobs, topologies
from services.artifacts import ArtifactStore, content_type
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


@router.post("/jobs/{job_id}/stop", response_model=JobOut, status_code=202)
async def stop_job(
    job_id: str,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_instructor),
):
    """Stop an open-ended job (a capture or traffic run): it winds down, keeps
    what it recorded, and finishes as ``succeeded``. Use cancel to abort."""
    job = _get_job(db, job_id)
    # Async on purpose: runs on the app loop, like cancel.
    if not runner.request_stop(job.id):
        raise Conflict("This job can't be stopped", code="not_stoppable")
    db.refresh(job)
    return jobs.job_to_dict(job)


@router.get("/topologies/{topology_id}/jobs", response_model=list[JobOut])
def list_topology_jobs(
    topology_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)
):
    topologies.get_or_404(db, topology_id)
    return [jobs.job_to_dict(j) for j in jobs.list_jobs(db, topology_id)]


@router.get("/jobs/{job_id}/artifacts", response_model=list[ArtifactOut])
def list_artifacts(
    job_id: str,
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifacts),
    _=Depends(require_any_auth),
):
    """Files the job produced (a capture's pcap, a traffic run's time series)."""
    job = _get_job(db, job_id)
    return [a.__dict__ for a in store.list(job.id)]


@router.get(
    "/jobs/{job_id}/artifacts/{name}",
    response_class=FileResponse,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
def download_artifact(
    job_id: str,
    name: str,
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifacts),
    _=Depends(require_any_auth),
):
    """Download one artifact. Accepts ``?token=`` so it works as a plain link."""
    job = _get_job(db, job_id)
    try:
        path = store.path(job.id, name)
    except ValueError:
        raise NotFound("Artifact") from None
    if not path.is_file():
        raise NotFound("Artifact")
    return FileResponse(path, media_type=content_type(name), filename=name)
