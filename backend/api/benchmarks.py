"""Benchmarks: start a scale sweep, follow it, fetch its results (JSON, CSV,
Markdown report, zip). Stop (finish the current step) via ``POST
/jobs/{id}/stop``; cancel (clean up now) via ``POST /jobs/{id}/cancel``."""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from api.deps import get_artifacts, get_db, get_runner
from api.errors import NotFound
from api.schemas import BenchmarkOut, BenchmarkRequest
from auth import require_any_auth, require_instructor
from db.models import Job
from domain import benchmark as bm
from services import benchmark, jobs
from services.artifacts import ArtifactStore
from services.jobs import JobRunner

router = APIRouter(prefix="/api/v1/benchmarks", tags=["benchmarks"])


def _get(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if not job or job.kind != benchmark.KIND:
        raise NotFound("Benchmark")
    return job


def benchmark_out(job: Job) -> dict[str, Any]:
    params = job.params or {}
    running = next((s for s in reversed(job.steps or []) if s.get("status") == "running"), None)
    return {
        "id": job.id,
        "label": params.get("label") or "",
        "kind": bm.kind_of(params),
        "status": job.status,
        "live": job.is_active,
        "topology_id": params.get("topology_id"),
        "spec": params,
        "result": job.result,
        "current": f"{running['name']}: {running.get('message') or ''}".rstrip(": ")
        if running
        else None,
        "job": jobs.job_to_dict(job),
    }


@router.post("", response_model=BenchmarkOut, status_code=202)
def start_benchmark(
    body: BenchmarkRequest,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_instructor),
):
    """Start a sweep. One benchmark at a time (409 ``benchmark_active``); it
    fails at its first step if other labs or jobs load the host, unless
    ``allow_busy_host``."""
    return benchmark_out(benchmark.start_benchmark(db, runner, body.model_dump()))


@router.get("", response_model=list[BenchmarkOut])
def list_benchmarks(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_any_auth),
):
    return [benchmark_out(j) for j in benchmark.list_benchmarks(db, limit)]


@router.get("/{job_id}", response_model=BenchmarkOut)
def get_benchmark(job_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    return benchmark_out(_get(db, job_id))


@router.get("/{job_id}/report.md", response_class=PlainTextResponse)
def get_report(
    job_id: str,
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifacts),
    _=Depends(require_any_auth),
):
    """The results as Markdown (so far, while it runs)."""
    job = _get(db, job_id)
    path = store.dir(job.id) / benchmark.REPORT_NAME
    if path.exists() and not job.is_active:
        text = path.read_text()
    else:
        info_path = store.dir(job.id) / benchmark.INFO_NAME
        env = (
            json.loads(info_path.read_text()).get("environment") or {} if info_path.exists() else {}
        )
        text = bm.markdown_report(job.result or {}, job.params or {}, env)
    return PlainTextResponse(text, media_type="text/markdown")


@router.get(
    "/{job_id}/export",
    response_class=Response,
    responses={200: {"content": {"application/zip": {}}}},
)
def export_benchmark(
    job_id: str,
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifacts),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_any_auth),
):
    """Everything: benchmark.json, results.csv, report.md, the monitor's CSVs,
    each step's topology, and the job log."""
    job = _get(db, job_id)
    directory = store.dir(job.id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if directory.is_dir():
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(directory).as_posix())
        log_path = runner.logs.path(job.id)
        if log_path.exists():
            zf.write(log_path, "job.log")
    stamp = (job.created_at or job.started_at).strftime("%Y%m%d-%H%M%S")
    label = "".join(c if c.isalnum() else "-" for c in (job.params or {}).get("label") or "")[:40]
    name = f"benchmark-{label + '-' if label else ''}{stamp}.zip"
    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
