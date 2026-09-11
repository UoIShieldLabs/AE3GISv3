"""Deploy / destroy / status / exec-terminal, backed by the deployment engine."""

from __future__ import annotations

import contextlib
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from auth import require_any_auth, require_instructor, valid_ws_token
from database import get_db
from engine.base import NodeStatus
from engine.kathara.engine import engine
from engine.terminal import bridge_terminal
from models import Topology

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/topologies", tags=["deployment"])


def _get_topo(topology_id: str, db: Session) -> Topology:
    topo = db.get(Topology, topology_id)
    if not topo:
        raise HTTPException(404, "Topology not found")
    return topo


def _find_container(topo: Topology, container_id: str) -> dict | None:
    for site in (topo.data or {}).get("sites", []):
        for subnet in site.get("subnets", []):
            for c in subnet.get("containers", []):
                if c.get("id") == container_id:
                    return c
    return None


@router.post("/{topology_id}/deploy")
async def deploy(topology_id: str, db: Session = Depends(get_db), _=Depends(require_instructor)):
    topo = _get_topo(topology_id, db)
    try:
        data = {**topo.data, "name": topo.name}
        state = await engine.deploy(topology_id, data)
        topo.engine_state = state
        topo.status = "deployed"
        db.commit()
        return {"status": "deployed", "engine_state": state}
    except Exception as exc:
        log.exception("Deploy failed for %s", topology_id)
        topo.status = "error"
        db.commit()
        raise HTTPException(500, f"{type(exc).__name__}: {exc}") from exc


@router.post("/{topology_id}/destroy")
async def destroy(topology_id: str, db: Session = Depends(get_db), _=Depends(require_instructor)):
    topo = _get_topo(topology_id, db)
    try:
        data = {**topo.data, "name": topo.name}
        await engine.destroy(topology_id, data)
        topo.status = "idle"
        topo.engine_state = None
        db.commit()
        return {"status": "destroyed"}
    except Exception as exc:
        log.exception("Destroy failed for %s", topology_id)
        topo.status = "error"
        db.commit()
        raise HTTPException(500, f"{type(exc).__name__}: {exc}") from exc


@router.get("/{topology_id}/status")
async def status(topology_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    topo = _get_topo(topology_id, db)
    if topo.status != "deployed":
        return {"status": topo.status, "containers": []}
    data = {**topo.data, "name": topo.name}
    try:
        statuses: list[NodeStatus] = await engine.status(topology_id, data)
    except Exception as exc:
        log.warning("Status failed for %s: %s", topology_id, exc)
        return {"status": topo.status, "containers": []}
    return {
        "status": topo.status,
        "containers": [{"id": s.node_id, "name": s.name, "state": s.state} for s in statuses],
    }


@router.websocket("/ws/{topology_id}/exec/{container_id}")
async def exec_terminal(
    websocket: WebSocket,
    topology_id: str,
    container_id: str,
    token: str | None = Query(default=None),
):
    db = next(get_db())
    try:
        if not valid_ws_token(token):
            await websocket.close(code=4003, reason="Forbidden")
            return
        topo = db.get(Topology, topology_id)
        await websocket.accept()
        if not topo:
            await websocket.send_text("Error: topology not found\r\n")
            await websocket.close(code=4004)
            return
        if not _find_container(topo, container_id):
            await websocket.send_text("Error: container not found\r\n")
            await websocket.close(code=4004)
            return
        data = {**topo.data, "name": topo.name}
        try:
            container_name = await engine.resolve_container(topology_id, data, container_id)
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
