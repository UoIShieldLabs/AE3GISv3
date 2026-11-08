"""Deploy / destroy (as jobs) and the exec-terminal WebSocket."""

from __future__ import annotations

import contextlib
import logging

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from api.access import WS_NOT_FOUND, WS_UNAUTHORIZED, owned_topology, ws_access
from api.deps import get_db, get_runner, get_settings
from api.schemas import DeployedInterfacesOut, JobOut
from auth import current_identity
from config import Settings
from db.models import Topology
from domain.links import interfaces_by_node
from domain.topology import find_container
from engine.base import DeploymentEngine, EngineState
from engine.terminal import bridge_terminal
from services import accounts, deployment, jobs
from services.accounts import Identity
from services.jobs import JobRunner

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/topologies", tags=["deployment"])


@router.post("/{topology_id}/deploy", response_model=JobOut, status_code=202)
def deploy(
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    settings: Settings = Depends(get_settings),
    identity: Identity = Depends(current_identity),
    topo: Topology = Depends(owned_topology),
):
    """Start a deploy job. Poll ``/runtime`` (or ``/jobs/{id}``) for progress.
    A student over ``AE3GIS_STUDENT_MAX_LABS`` gets 409 ``lab_limit``."""

    def admit() -> None:
        accounts.check_lab_cap(db, identity, topo, settings)

    return jobs.job_to_dict(deployment.start_deploy(db, runner, topo, admit=admit))


@router.post("/{topology_id}/destroy", response_model=JobOut, status_code=202)
def destroy(
    save: bool = Query(
        False,
        description="Save every node's filesystem first; the next deploy resumes from it.",
    ),
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    topo: Topology = Depends(owned_topology),
):
    return jobs.job_to_dict(deployment.start_destroy(db, runner, topo, save=save))


@router.get("/{topology_id}/interfaces", response_model=DeployedInterfacesOut)
def get_interfaces(topo: Topology = Depends(owned_topology)):
    """Every deployed interface by node, and the links between them: what a
    capture can target. Reads the saved deploy state; no engine call."""
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
    access = await ws_access(websocket, token, topology_id)
    if access == WS_UNAUTHORIZED:
        await websocket.close(code=WS_UNAUTHORIZED, reason="Forbidden")
        return
    engine: DeploymentEngine = websocket.app.state.engine
    db: Session = websocket.app.state.session_factory()
    try:
        # Someone else's topology reads as missing (as on the REST routes).
        topo = db.get(Topology, topology_id) if access != WS_NOT_FOUND else None
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
