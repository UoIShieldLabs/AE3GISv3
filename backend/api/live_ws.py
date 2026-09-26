"""Serving a job's live channel over a WebSocket.

A handler must notice when the client goes away even while nothing is being
sent (an idle capture, a run still preparing): otherwise it lingers until the
job ends, and on shutdown uvicorn waits for it while the job waits for
shutdown. Every wait here is raced against the client's disconnect (uvicorn
closes open WebSockets with 1012 when it shuts down).
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import WebSocket

from services.live import Subscriber


class ClientGone(Exception):
    """The WebSocket closed while we were waiting."""


async def _until_disconnect(websocket: WebSocket) -> None:
    while True:
        msg = await websocket.receive()
        if msg["type"] == "websocket.disconnect":
            return


async def unless_disconnected[T](websocket: WebSocket, awaitable: Awaitable[T]) -> T:
    """Await ``awaitable``, or raise ``ClientGone`` if the client leaves first."""
    work = asyncio.ensure_future(awaitable)
    gone = asyncio.ensure_future(_until_disconnect(websocket))
    try:
        done, _ = await asyncio.wait({work, gone}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in (work, gone):
            if not task.done():
                task.cancel()
                with contextlib.suppress(BaseException):
                    await task
    if work in done:
        return work.result()
    raise ClientGone


async def forward(
    websocket: WebSocket,
    sub: Subscriber,
    transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> None:
    """Send the subscriber's messages until the channel closes or the client leaves."""

    async def pump() -> None:
        while True:
            msg = await sub.get()
            if msg is None:
                return
            await websocket.send_json(transform(msg) if transform else msg)

    with contextlib.suppress(ClientGone):
        await unless_disconnected(websocket, pump())
