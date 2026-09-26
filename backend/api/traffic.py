"""Traffic runs: start/list runs, their samples, an export bundle, and a
WebSocket of live samples. Stop via ``POST /jobs/{id}/stop``."""

from __future__ import annotations

import asyncio
import contextlib
import io
import zipfile
from typing import Any

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy.orm import Session

from api.deps import get_artifacts, get_db, get_runner
from api.errors import NotFound
from api.live_ws import ClientGone, forward, unless_disconnected
from api.schemas import TrafficRunOut, TrafficRunRequest, TrafficSamplesOut
from auth import require_any_auth, require_instructor, valid_ws_token
from db.models import Job
from services import jobs, live, topologies, traffic
from services.artifacts import ArtifactStore
from services.jobs import JobRunner
from services.live import LiveHub

router = APIRouter(prefix="/api/v1", tags=["traffic"])

V1 = "/api/v1"


def _get_run(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if not job or job.kind != traffic.KIND:
        raise NotFound("Traffic run")
    return job


def run_out(job: Job) -> dict[str, Any]:
    params = job.params or {}
    recorder = traffic.active_recorder(job.id)
    sidecars = recorder.sidecars if recorder else (job.result or {}).get("sidecars") or {}
    return {
        "id": job.id,
        "topology_id": job.topology_id,
        "label": params.get("label") or "",
        "status": job.status,
        "live": job.is_active,
        "flows": params.get("flows") or [],
        "duration_s": params.get("duration_s"),
        "interval_s": params.get("interval_s") or 1.0,
        "monitored": params.get("monitored") or [],
        "sidecars": sidecars,
        "result": job.result,
        "job": jobs.job_to_dict(job),
        "ws_path": f"{V1}/topologies/ws/{job.topology_id}/traffic/{job.id}",
    }


def _backlog(store: ArtifactStore, job_id: str) -> dict[str, list[dict[str, Any]]]:
    recorder = traffic.active_recorder(job_id)
    if recorder is not None:
        return recorder.backlog()
    return traffic.read_backlog(store.dir(job_id))


@router.post(
    "/topologies/{topology_id}/traffic/runs", response_model=TrafficRunOut, status_code=202
)
def start_run(
    topology_id: str,
    body: TrafficRunRequest,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_instructor),
):
    """Start generating traffic between deployed nodes. One run at a time per
    topology (409 ``traffic_active``). Results and samples are kept."""
    topo = topologies.get_or_404(db, topology_id)
    return run_out(traffic.start_run(db, runner, topo, body.model_dump()))


@router.get("/topologies/{topology_id}/traffic/runs", response_model=list[TrafficRunOut])
def list_runs(
    topology_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_any_auth),
):
    topologies.get_or_404(db, topology_id)
    return [run_out(j) for j in jobs.list_jobs(db, topology_id, limit, kinds=(traffic.KIND,))]


@router.get("/traffic/runs/{job_id}", response_model=TrafficRunOut)
def get_run(job_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    return run_out(_get_run(db, job_id))


@router.get("/traffic/runs/{job_id}/samples", response_model=TrafficSamplesOut)
async def get_samples(
    job_id: str,
    since: float = Query(default=-1.0, description="Only samples after this run time (s)"),
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifacts),
    _=Depends(require_any_auth),
):
    """Every flow and node sample of a run (live or finished)."""
    _get_run(db, job_id)
    backlog = await asyncio.to_thread(_backlog, store, job_id)
    return {k: [s for s in rows if s.get("t", 0) > since] for k, rows in backlog.items()}


@router.get(
    "/traffic/runs/{job_id}/export",
    response_class=Response,
    responses={200: {"content": {"application/zip": {}}}},
)
def export_run(
    job_id: str,
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifacts),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_any_auth),
):
    """The run as a zip: run.json (request, environment, summary), the samples,
    iperf3's raw output and the job log."""
    job = _get_run(db, job_id)
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
    name = (
        f"traffic-{job.id[:8]}-{(job.created_at or job.started_at).strftime('%Y%m%d-%H%M%S')}.zip"
    )
    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.websocket("/topologies/ws/{topology_id}/traffic/{job_id}")
async def traffic_live(
    websocket: WebSocket,
    topology_id: str,
    job_id: str,
    token: str | None = Query(default=None),
):
    """Live samples. Messages (JSON): ``hello`` {run, backlog: {flows, nodes}},
    ``flow`` {samples}, ``nodes`` {samples}, ``sidecars`` {items}, ``status``
    {elapsed, flows: {id: {fwd, rev}}}, ``end`` {result}."""
    if not valid_ws_token(websocket, token):
        await websocket.close(code=4003, reason="Forbidden")
        return
    hub: LiveHub = websocket.app.state.live
    store: ArtifactStore = websocket.app.state.artifacts
    session_factory = websocket.app.state.session_factory

    def info() -> dict[str, Any] | None:
        with session_factory() as db:
            job = db.get(Job, job_id)
            if not job or job.kind != traffic.KIND or job.topology_id != topology_id:
                return None
            return TrafficRunOut.model_validate(run_out(job)).model_dump(mode="json")

    def is_active() -> bool:
        with session_factory() as db:
            job = db.get(Job, job_id)
            return bool(job and job.is_active)

    if await asyncio.to_thread(info) is None:
        await websocket.close(code=4004, reason="Traffic run not found")
        return
    await websocket.accept()
    try:
        try:
            channel = await unless_disconnected(
                websocket, live.wait_for_channel(hub, job_id, is_active)
            )
        except ClientGone:
            return
        # Subscribe before reading the backlog so nothing falls in between
        # (clients dedupe on t + flow/target).
        sub = channel.subscribe(maxsize=512)[0] if channel is not None else None
        backlog = await asyncio.to_thread(_backlog, store, job_id)
        hello = await asyncio.to_thread(info)
        await websocket.send_json({"type": "hello", "run": hello, "backlog": backlog})
        if sub is None:
            await websocket.send_json({"type": "end", "result": (hello or {}).get("result")})
            await websocket.close()
            return
        try:
            await forward(websocket, sub)
        finally:
            channel.unsubscribe(sub)
        with contextlib.suppress(Exception):
            await websocket.close()
    except WebSocketDisconnect:
        pass
