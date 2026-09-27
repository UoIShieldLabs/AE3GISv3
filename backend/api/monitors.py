"""Monitors: start/list monitors of a deployed topology, their recorded
samples, an export bundle, and a WebSocket of live sweeps. Stop via
``POST /jobs/{id}/stop``."""

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
from api.schemas import MonitorOut, MonitorRequest, MonitorSamplesOut
from auth import require_any_auth, require_instructor, valid_ws_token
from db.models import Job
from services import jobs, live, topologies
from services import monitor as monitor_service
from services.artifacts import ArtifactStore
from services.jobs import JobRunner
from services.live import LiveHub

router = APIRouter(prefix="/api/v1", tags=["monitors"])

V1 = "/api/v1"


def _get_monitor(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if not job or job.kind != monitor_service.KIND:
        raise NotFound("Monitor")
    return job


def monitor_out(job: Job) -> dict[str, Any]:
    params = job.params or {}
    return {
        "id": job.id,
        "topology_id": job.topology_id,
        "label": params.get("label") or "",
        "status": job.status,
        "live": job.is_active,
        "interval_s": params.get("interval_s") or 1.0,
        "duration_s": params.get("duration_s"),
        "selector": params.get("selector") or "all",
        "monitored": params.get("monitored") or [],
        "result": job.result,
        "job": jobs.job_to_dict(job),
        "ws_path": f"{V1}/topologies/ws/{job.topology_id}/monitors/{job.id}",
    }


def _samples(
    store: ArtifactStore,
    job_id: str,
    since: float,
    nodes: set[str] | None,
    every: int,
    host_only: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    directory = store.dir(job_id)
    host = [
        r for r in monitor_service.read_csv(directory, monitor_service.HOST_NAME) if r["t"] > since
    ]
    keep_t = {r["t"] for r in host[::every]} if every > 1 else None

    def rows(name: str) -> list[dict[str, Any]]:
        if host_only:
            return []
        out = []
        for r in monitor_service.read_csv(directory, name):
            if r["t"] <= since or (keep_t is not None and r["t"] not in keep_t):
                continue
            if nodes is not None and r.get("kind") != "tool" and r.get("target") not in nodes:
                continue
            out.append(r)
        return out

    return {
        "host": host[::every] if every > 1 else host,
        "nodes": rows(monitor_service.NODES_NAME),
        "ifaces": rows(monitor_service.IFACES_NAME),
        "markers": [
            r
            for r in monitor_service.read_csv(directory, monitor_service.MARKERS_NAME)
            if r["t"] > since
        ],
    }


@router.post("/topologies/{topology_id}/monitors", response_model=MonitorOut, status_code=202)
def start_monitor(
    topology_id: str,
    body: MonitorRequest,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_instructor),
):
    """Start recording CPU, memory and network of the selected nodes and of the
    host every ``interval_s``. One monitor at a time per topology (409
    ``monitor_active``)."""
    topo = topologies.get_or_404(db, topology_id)
    req = body.model_dump()
    if isinstance(body.nodes, list) or body.nodes == "all":
        req["nodes"] = body.nodes
    else:
        req["nodes"] = body.nodes.model_dump(exclude_none=True)
    return monitor_out(monitor_service.start_monitor(db, runner, topo, req))


@router.get("/topologies/{topology_id}/monitors", response_model=list[MonitorOut])
def list_monitors(
    topology_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_any_auth),
):
    topologies.get_or_404(db, topology_id)
    return [
        monitor_out(j)
        for j in jobs.list_jobs(db, topology_id, limit, kinds=(monitor_service.KIND,))
    ]


@router.get("/monitors/{job_id}", response_model=MonitorOut)
def get_monitor(job_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    return monitor_out(_get_monitor(db, job_id))


@router.get("/monitors/{job_id}/samples", response_model=MonitorSamplesOut)
async def get_samples(
    job_id: str,
    since: float = Query(default=-1.0, description="Only sweeps after this time (s)"),
    nodes: str | None = Query(default=None, description="Comma-separated node ids"),
    every: int = Query(default=1, ge=1, le=3600, description="Keep every n-th sweep"),
    host_only: bool = Query(default=False, description="Leave out node and interface rows"),
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifacts),
    _=Depends(require_any_auth),
):
    """Recorded sweeps of a monitor (live or finished)."""
    _get_monitor(db, job_id)
    wanted = {n for n in nodes.split(",") if n} if nodes else None
    return await asyncio.to_thread(_samples, store, job_id, since, wanted, every, host_only)


@router.get(
    "/monitors/{job_id}/export",
    response_class=Response,
    responses={200: {"content": {"application/zip": {}}}},
)
def export_monitor(
    job_id: str,
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifacts),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_any_auth),
):
    """The monitor as a zip: monitor.json (request, environment, summary), the
    CSV files and the job log."""
    job = _get_monitor(db, job_id)
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
    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="monitor-{job.id[:8]}-{stamp}.zip"'},
    )


@router.websocket("/topologies/ws/{topology_id}/monitors/{job_id}")
async def monitor_live(
    websocket: WebSocket,
    topology_id: str,
    job_id: str,
    token: str | None = Query(default=None),
):
    """Live sweeps. Messages (JSON): ``hello`` {monitor, backlog: [sweep…]},
    ``sweep`` {t, host, groups, selection, nodes (≤ 50 nodes, else null), tools,
    oom, missing}, ``marker`` {t, source, text}, ``end`` {result}."""
    if not valid_ws_token(websocket, token):
        await websocket.close(code=4003, reason="Forbidden")
        return
    hub: LiveHub = websocket.app.state.live
    session_factory = websocket.app.state.session_factory

    def info() -> dict[str, Any] | None:
        with session_factory() as db:
            job = db.get(Job, job_id)
            if not job or job.kind != monitor_service.KIND or job.topology_id != topology_id:
                return None
            return MonitorOut.model_validate(monitor_out(job)).model_dump(mode="json")

    def is_active() -> bool:
        with session_factory() as db:
            job = db.get(Job, job_id)
            return bool(job and job.is_active)

    if await asyncio.to_thread(info) is None:
        await websocket.close(code=4004, reason="Monitor not found")
        return
    await websocket.accept()
    try:
        try:
            channel = await unless_disconnected(
                websocket, live.wait_for_channel(hub, job_id, is_active)
            )
        except ClientGone:
            return
        sub = channel.subscribe(maxsize=256)[0] if channel is not None else None
        session = monitor_service.active_session(job_id)
        backlog = list(session.ring) if session is not None else []
        hello = await asyncio.to_thread(info)
        await websocket.send_json({"type": "hello", "monitor": hello, "backlog": backlog})
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
