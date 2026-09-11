"""Engine-agnostic interactive terminal: PTY <-> WebSocket bridge.

Given an already-resolved container name, bridges a browser xterm.js WebSocket
to an interactive shell via `docker exec -it`. No `sudo` (the daemon is reached
through the mounted socket). Adapted from the original ContainerLab exec
handler, minus the clab naming.
"""

from __future__ import annotations

import asyncio
import contextlib
import fcntl
import json
import logging
import os
import pty
import signal
import struct
import termios

from fastapi import WebSocket, WebSocketDisconnect

log = logging.getLogger(__name__)


def _interactive_shell_command() -> list[str]:
    return [
        "sh",
        "-lc",
        (
            "mkdir -p /tmp; "
            "printf 'set horizontal-scroll-mode Off\\nset enable-bracketed-paste Off\\n' >/tmp/ae3gis.inputrc 2>/dev/null || true; "
            "export INPUTRC=/tmp/ae3gis.inputrc; "
            "if command -v bash >/dev/null 2>&1; then exec bash -il; "
            "elif command -v ash >/dev/null 2>&1; then exec ash -l; "
            "else exec sh -l; fi"
        ),
    ]


async def bridge_terminal(websocket: WebSocket, container_name: str) -> None:
    """Run an interactive shell in `container_name`, bridged to `websocket`.

    The websocket must already be accepted by the caller.
    """
    proc = None
    master_fd = -1

    def _resize(cols: int, rows: int) -> None:
        nonlocal proc, master_fd
        cols = max(1, int(cols))
        rows = max(1, int(rows))
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        if proc is not None and proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                proc.send_signal(signal.SIGWINCH)

    try:
        master_fd, slave_fd = pty.openpty()
        _resize(80, 24)
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "exec",
                "-e",
                "TERM=xterm-256color",
                "-e",
                "COLUMNS=80",
                "-e",
                "LINES=24",
                "-it",
                container_name,
                *_interactive_shell_command(),
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
            )
        finally:
            os.close(slave_fd)

        loop = asyncio.get_running_loop()
        read_queue: asyncio.Queue[bytes] = asyncio.Queue()

        def _on_readable() -> None:
            try:
                data = os.read(master_fd, 4096)
                read_queue.put_nowait(data if data else b"")
            except OSError:
                read_queue.put_nowait(b"")
                loop.remove_reader(master_fd)

        loop.add_reader(master_fd, _on_readable)

        async def _read_pty() -> None:
            while True:
                data = await read_queue.get()
                if not data:
                    break
                with contextlib.suppress(Exception):
                    await websocket.send_bytes(data)

        async def _write_pty() -> None:
            while True:
                try:
                    msg = await websocket.receive()
                    if msg.get("type") != "websocket.receive":
                        if msg.get("type") in ("websocket.disconnect", "websocket.close"):
                            break
                        continue
                    data = msg.get("bytes") if msg.get("bytes") is not None else msg.get("text", "")
                    if isinstance(data, str):
                        data = data.encode("utf-8")
                    try:
                        payload = json.loads(data.decode("utf-8", "ignore"))
                        if isinstance(payload, dict) and payload.get("type") == "resize":
                            _resize(payload.get("cols", 80), payload.get("rows", 24))
                            continue
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass
                    os.write(master_fd, data)
                except WebSocketDisconnect:
                    break
                except Exception:
                    break

        read_task = asyncio.create_task(_read_pty())
        write_task = asyncio.create_task(_write_pty())
        try:
            await asyncio.wait([read_task, write_task], return_when=asyncio.FIRST_COMPLETED)
        finally:
            loop.remove_reader(master_fd)
            for t in (read_task, write_task):
                t.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await t

        with contextlib.suppress(Exception):
            await websocket.send_text("\r\n[session ended]\r\n")
    except WebSocketDisconnect:
        pass
    finally:
        if master_fd >= 0:
            with contextlib.suppress(OSError):
                os.close(master_fd)
        if proc and proc.returncode is None:
            proc.terminate()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(proc.wait(), timeout=2.0)
