"""Scenario runs: run a step or a phase, list/read runs, export a bundle, and a
WebSocket of live step output. Stop via ``POST /jobs/{id}/stop``."""

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
from api.schemas import (
    ScenarioPhaseRunRequest,
    ScenarioRunOut,
    ScenarioSamplesOut,
    ScenarioStepRequest,
)
from auth import require_any_auth, require_instructor, valid_ws_token
from db.models import Job
from services import jobs, live, scenario, topologies
from services.artifacts import ArtifactStore
from services.jobs import JobRunner
from services.live import LiveHub

router = APIRouter(prefix="/api/v1", tags=["scenario"])

V1 = "/api/v1"


def _get_run(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if not job or job.kind != scenario.KIND:
        raise NotFound("Scenario run")
    return job


def run_out(job: Job, *, full: bool = True) -> dict[str, Any]:
    """A run; listings (``full=False``) leave out the planned steps and results."""
    params = job.params or {}
    steps = params.get("steps") or []
    result = job.result
    if not full and result:
        result = {k: v for k, v in result.items() if k != "steps"}
    return {
        "id": job.id,
        "topology_id": job.topology_id,
        "label": params.get("label") or "",
        "status": job.status,
        "live": job.is_active,
        "step_count": params.get("step_count") or len(steps),
        "node_ids": list(params.get("node_ids") or []),
        "steps": steps if full else [],
        "result": result,
        "job": jobs.job_to_dict(job),
        "ws_path": f"{V1}/topologies/ws/{job.topology_id}/scenario/{job.id}",
    }


def _backlog(job: Job) -> dict[str, list[dict[str, Any]]]:
    """Completed-step results so a late joiner (or a poll) sees progress: the
    live buffer while running, else the stored result."""
    live_steps = scenario.active_steps(job.id)
    if live_steps is not None:
        return {"steps": list(live_steps)}
    return {"steps": list((job.result or {}).get("steps") or [])}


@router.post(
    "/topologies/{topology_id}/scenario/steps/run", response_model=ScenarioRunOut, status_code=202
)
def run_step(
    topology_id: str,
    body: ScenarioStepRequest,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_instructor),
):
    """Run one command on a node. One scenario run at a time per topology
    (409 ``scenario_active``); the topology must be deployed (409 ``bad_state``)."""
    topo = topologies.get_or_404(db, topology_id)
    step = {"containerId": body.containerId, "script": body.script, "args": body.args}
    return run_out(scenario.start_step(db, runner, topo, step, body.label))


@router.post(
    "/topologies/{topology_id}/scenario/phases/{phase_id}/run",
    response_model=ScenarioRunOut,
    status_code=202,
)
def run_phase(
    topology_id: str,
    phase_id: str,
    body: ScenarioPhaseRunRequest | None = None,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_instructor),
):
    """Run every step of a stored phase, in order."""
    topo = topologies.get_or_404(db, topology_id)
    return run_out(scenario.start_phase(db, runner, topo, phase_id, (body.label if body else "")))


@router.get("/topologies/{topology_id}/scenario/runs", response_model=list[ScenarioRunOut])
def list_runs(
    topology_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_any_auth),
):
    topologies.get_or_404(db, topology_id)
    return [
        run_out(j, full=False)
        for j in jobs.list_jobs(db, topology_id, limit, kinds=(scenario.KIND,))
    ]


@router.get("/scenario/runs/{job_id}", response_model=ScenarioRunOut)
def get_run(job_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    return run_out(_get_run(db, job_id))


@router.get("/scenario/runs/{job_id}/samples", response_model=ScenarioSamplesOut)
def get_samples(job_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    """The run's completed-step results so far (live or finished)."""
    return _backlog(_get_run(db, job_id))


@router.get(
    "/scenario/runs/{job_id}/export",
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
    """The run as a zip: run.json (request, per-step results) and the job log."""
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
        f"scenario-{job.id[:8]}-{(job.created_at or job.started_at).strftime('%Y%m%d-%H%M%S')}.zip"
    )
    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.websocket("/topologies/ws/{topology_id}/scenario/{job_id}")
async def scenario_live(
    websocket: WebSocket,
    topology_id: str,
    job_id: str,
    token: str | None = Query(default=None),
):
    """Live step output. Messages (JSON): ``hello`` {run, backlog: {steps}},
    ``step`` {index, status, container_id?, command?, exit_code?}, ``output``
    {index, stream, text}, ``end`` {result}."""
    if not valid_ws_token(websocket, token):
        await websocket.close(code=4003, reason="Forbidden")
        return
    hub: LiveHub = websocket.app.state.live
    session_factory = websocket.app.state.session_factory

    def info() -> dict[str, Any] | None:
        with session_factory() as db:
            job = db.get(Job, job_id)
            if not job or job.kind != scenario.KIND or job.topology_id != topology_id:
                return None
            return ScenarioRunOut.model_validate(run_out(job)).model_dump(mode="json")

    def hello_payload() -> tuple[dict[str, Any] | None, dict[str, Any]]:
        with session_factory() as db:
            job = db.get(Job, job_id)
            run = (
                ScenarioRunOut.model_validate(run_out(job)).model_dump(mode="json") if job else None
            )
            return run, (_backlog(job) if job else {"steps": []})

    def is_active() -> bool:
        with session_factory() as db:
            job = db.get(Job, job_id)
            return bool(job and job.is_active)

    if await asyncio.to_thread(info) is None:
        await websocket.close(code=4004, reason="Scenario run not found")
        return
    await websocket.accept()
    try:
        try:
            channel = await unless_disconnected(
                websocket, live.wait_for_channel(hub, job_id, is_active)
            )
        except ClientGone:
            return
        sub = channel.subscribe(maxsize=512)[0] if channel is not None else None
        run, backlog = await asyncio.to_thread(hello_payload)
        await websocket.send_json({"type": "hello", "run": run, "backlog": backlog})
        if sub is None:
            await websocket.send_json({"type": "end", "result": (run or {}).get("result")})
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
