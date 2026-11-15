"""The live lab view over a WebSocket: links carrying traffic, processes per node."""

from __future__ import annotations

import contextlib

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from api.access import ws_guard
from api.live_ws import forward
from services.pulse import PulseService

router = APIRouter(prefix="/api/v1", tags=["pulse"])


@router.websocket("/topologies/ws/{topology_id}/pulse")
async def pulse_live(
    websocket: WebSocket,
    topology_id: str,
    token: str | None = Query(default=None),
):
    """What is happening in the deployed lab, while this socket is open.

    Messages (JSON): ``hello``, then ``pulse`` {links: {connection id:
    "fwd" | "rev" | "both"}, nodes: {node id: [{name, args}]}} whenever the
    picture changes (only links carrying traffic and nodes running something
    are listed; the direction is relative to the connection's from → to), and
    ``unavailable`` {reason} if the collector cannot run (the socket then
    closes; reconnect to try again). Nothing is listed while not deployed."""
    if not await ws_guard(websocket, token, topology_id):
        return
    service: PulseService = websocket.app.state.pulse
    await websocket.accept()
    try:
        channel = await service.acquire(topology_id)
    except Exception as exc:
        with contextlib.suppress(Exception):
            await websocket.send_json({"type": "unavailable", "reason": str(exc)})
            await websocket.close()
        return
    sub, history = channel.subscribe(maxsize=8)
    try:
        await websocket.send_json({"type": "hello"})
        for message in history:
            await websocket.send_json(message)
        await forward(websocket, sub)
        with contextlib.suppress(Exception):
            await websocket.close()
    except WebSocketDisconnect:
        pass
    finally:
        channel.unsubscribe(sub)
        service.release(topology_id, channel)
