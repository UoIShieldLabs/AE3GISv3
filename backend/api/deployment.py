"""Deploy / destroy (as jobs) and the exec-terminal WebSocket."""

from __future__ import annotations

import contextlib
import logging

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from api.deps import get_db, get_runner
from api.schemas import DeployedInterfacesOut, JobOut
from auth import require_any_auth, require_instructor, valid_ws_token
from db.models import Topology
from domain.links import interfaces_by_node
from domain.topology import find_container
from engine.base import DeploymentEngine, EngineState
from engine.terminal import bridge_terminal
from services import deployment, jobs, topologies
from services.jobs import JobRunner

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/topologies", tags=["deployment"])


@router.post("/{topology_id}/deploy", response_model=JobOut, status_code=202)
def deploy(
    topology_id: str,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_instructor),
):
    """Start a deploy job. Poll ``/runtime`` (or ``/jobs/{id}``) for progress."""
    topo = topologies.get_or_404(db, topology_id)
    return jobs.job_to_dict(deployment.start_deploy(db, runner, topo))


@router.post("/{topology_id}/destroy", response_model=JobOut, status_code=202)
def destroy(
    topology_id: str,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_instructor),
):
    topo = topologies.get_or_404(db, topology_id)
    return jobs.job_to_dict(deployment.start_destroy(db, runner, topo))


@router.get("/{topology_id}/interfaces", response_model=DeployedInterfacesOut)
def get_interfaces(topology_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    """Every deployed interface by node, and the links between them: what a
    capture can target. Reads the saved deploy state; no engine call."""
    topo = topologies.get_or_404(db, topology_id)
    links, mapping = deployment.deployed_links(topo)
    nodes = {
        node_id: [
            {
                "name": ep.interface,
                "collision_domain": ep.collision_domain,
                "connection_id": ep.connection_id,
                "peer_node_id": ep.peer_node_id,
                "ip": ep.ip,
            }
            for ep in eps
        ]
        for node_id, eps in interfaces_by_node(links).items()
    }
    return {"deployed": mapping != "none", "mapping": mapping, "nodes": nodes, "links": links}


@router.websocket("/ws/{topology_id}/exec/{container_id}")
async def exec_terminal(
    websocket: WebSocket,
    topology_id: str,
    container_id: str,
    token: str | None = Query(default=None),
):
    if not valid_ws_token(websocket, token):
        await websocket.close(code=4003, reason="Forbidden")
        return
    engine: DeploymentEngine = websocket.app.state.engine
    db: Session = websocket.app.state.session_factory()
    try:
        topo = db.get(Topology, topology_id)
        await websocket.accept()
        if not topo:
            await websocket.send_text("Error: topology not found\r\n")
            await websocket.close(code=4004)
            return
        if not find_container(topo.data or {}, container_id):
            await websocket.send_text("Error: container not found\r\n")
            await websocket.close(code=4004)
            return
        state = EngineState.from_dict(topo.engine_state)
        if topo.status != "deployed" or not state:
            await websocket.send_text("Error: topology is not deployed\r\n")
            await websocket.close(code=4004)
            return
        try:
            container_name = await engine.resolve_container(state, container_id)
        except Exception as exc:
            await websocket.send_text(f"Error: {exc}\r\n")
            await websocket.close(code=4004)
            return
        await websocket.send_text(f"Connecting to {container_name}...\r\n")
        await bridge_terminal(websocket, container_name)
        with contextlib.suppress(Exception):
            await websocket.close()
    except WebSocketDisconnect:
        pass
    finally:
        db.close()
