"""In-memory PTY exec session manager.

When an instructor pushes a scenario phase to student topologies, each
script execution becomes a live interactive PTY session.  Students connect
to these sessions via WebSocket to see real-time output and interact.
"""
from __future__ import annotations

import asyncio
import collections
import contextlib
import fcntl
import logging
import os
import pty
import signal
import struct
import termios
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

log = logging.getLogger(__name__)

# How much output (in bytes) to buffer per session so late joiners catch up.
_OUTPUT_BUFFER_BYTES = 128 * 1024


@dataclass
class ExecSession:
    session_id: str
    topology_id: str
    container_id: str
    container_name: str   # human-readable display name for the UI tab
    script: str
    phase_name: str
    docker_name: str
    proc: Any = None          # asyncio.subprocess.Process
    master_fd: int = -1
    subscribers: list = field(default_factory=list)
    output_chunks: collections.deque = field(default_factory=collections.deque)
    output_bytes: int = 0
    done: bool = False
    _read_task: Any = None    # asyncio.Task


class ExecSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, ExecSession] = {}
        # topology_id -> list of per-subscriber notification queues
        self._notify_channels: dict[str, list[asyncio.Queue]] = {}

    # ── Session accessors ─────────────────────────────────────────

    def get(self, session_id: str) -> ExecSession | None:
        return self._sessions.get(session_id)

    def active_for_topology(self, topology_id: str) -> list[ExecSession]:
        return [
            s for s in self._sessions.values()
            if s.topology_id == topology_id and not s.done
        ]

    # ── Session lifecycle ─────────────────────────────────────────

    async def create_session(
        self,
        *,
        topology_id: str,
        container_id: str,
        container_name: str,
        docker_name: str,
        script: str,
        args: list[str],
        env: dict[str, str],
        phase_name: str,
    ) -> ExecSession:
        session_id = uuid.uuid4().hex
        session = ExecSession(
            session_id=session_id,
            topology_id=topology_id,
            container_id=container_id,
            container_name=container_name,
            script=script,
            phase_name=phase_name,
            docker_name=docker_name,
        )
        self._sessions[session_id] = session

        env_flags: list[str] = []
        for k, v in env.items():
            env_flags += ["-e", f"{k}={v}"]

        master_fd, slave_fd = pty.openpty()
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
        session.master_fd = master_fd

        # Launch an interactive shell directly as the PTY process.
        # We then inject the script command as simulated keystrokes after a short
        # delay.  This keeps the interactive shell as the permanent PTY owner —
        # tools like msfconsole that close inherited fds won't terminate the session
        # because they are just child processes of the shell.
        try:
            proc = await asyncio.create_subprocess_exec(
                "sudo", "docker", "exec",
                "-e", "TERM=xterm-256color",
                "-e", "COLUMNS=80",
                "-e", "LINES=24",
                *env_flags,
                "-it",
                docker_name,
                "sh", "-c",
                (
                    "mkdir -p /tmp; "
                    "printf 'set horizontal-scroll-mode Off\\nset enable-bracketed-paste Off\\n' "
                    ">/tmp/ae3gis.inputrc 2>/dev/null || true; "
                    "export INPUTRC=/tmp/ae3gis.inputrc; "
                    "if command -v bash >/dev/null 2>&1; then exec bash --norc --noprofile -i; "
                    "elif command -v ash >/dev/null 2>&1; then exec ash -i; "
                    "else exec sh -i; fi"
                ),
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
            )
        finally:
            os.close(slave_fd)

        session.proc = proc
        session._read_task = asyncio.create_task(self._read_loop(session))

        # Inject the script command after the shell has initialised.
        # Build the command line with single-quote escaping.
        quoted_args = " ".join(
            "'" + a.replace("'", "'\\''") + "'"
            for a in [script, *args]
        )
        asyncio.create_task(self._inject_command(session, quoted_args))

        return session

    async def _inject_command(self, session: ExecSession, command: str) -> None:
        """Wait for the shell prompt then inject the script command as keystrokes."""
        # Give the shell a moment to print its prompt before we start typing.
        await asyncio.sleep(0.5)
        cmd_bytes = (command + "\n").encode()
        with contextlib.suppress(OSError):
            os.write(session.master_fd, cmd_bytes)

    async def _read_loop(self, session: ExecSession) -> None:
        loop = asyncio.get_running_loop()
        q: asyncio.Queue[bytes] = asyncio.Queue()

        def _readable() -> None:
            try:
                data = os.read(session.master_fd, 4096)
                q.put_nowait(data if data else b"")
            except OSError:
                q.put_nowait(b"")
                loop.remove_reader(session.master_fd)

        loop.add_reader(session.master_fd, _readable)
        try:
            while True:
                data = await q.get()
                if not data:
                    break
                # Append to rolling output buffer
                session.output_chunks.append(data)
                session.output_bytes += len(data)
                while session.output_bytes > _OUTPUT_BUFFER_BYTES and session.output_chunks:
                    removed = session.output_chunks.popleft()
                    session.output_bytes -= len(removed)
                # Fan-out to all connected subscribers
                for ws in list(session.subscribers):
                    try:
                        await ws.send_bytes(data)
                    except Exception:
                        with contextlib.suppress(ValueError):
                            session.subscribers.remove(ws)
        finally:
            loop.remove_reader(session.master_fd)
            session.done = True
            end_msg = b"\r\n\x1b[90m[session ended]\x1b[0m\r\n"
            for ws in list(session.subscribers):
                with contextlib.suppress(Exception):
                    await ws.send_bytes(end_msg)
            # Keep session around briefly for late joiners, then clean up.
            await asyncio.sleep(300)
            self._sessions.pop(session.session_id, None)
            with contextlib.suppress(OSError):
                os.close(session.master_fd)

    # ── Subscriber management ─────────────────────────────────────

    async def subscribe(self, session_id: str, ws: WebSocket) -> bool:
        """Attach a WebSocket to an existing session.

        Replays buffered output first so late joiners see what they missed.
        Returns False if the session does not exist.
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        # Replay buffered output
        for chunk in list(session.output_chunks):
            try:
                await ws.send_bytes(chunk)
            except Exception:
                return False
        if session.done:
            with contextlib.suppress(Exception):
                await ws.send_bytes(b"\r\n\x1b[90m[session ended]\x1b[0m\r\n")
        else:
            session.subscribers.append(ws)
        return True

    def unsubscribe(self, session_id: str, ws: WebSocket) -> None:
        session = self._sessions.get(session_id)
        if session:
            with contextlib.suppress(ValueError):
                session.subscribers.remove(ws)

    # ── Input/resize ──────────────────────────────────────────────

    def write_input(self, session_id: str, data: bytes) -> None:
        session = self._sessions.get(session_id)
        if session and session.master_fd >= 0 and not session.done:
            with contextlib.suppress(OSError):
                os.write(session.master_fd, data)

    def resize(self, session_id: str, cols: int, rows: int) -> None:
        session = self._sessions.get(session_id)
        if not session or session.master_fd < 0 or session.done:
            return
        with contextlib.suppress(OSError):
            fcntl.ioctl(
                session.master_fd,
                termios.TIOCSWINSZ,
                struct.pack("HHHH", rows, cols, 0, 0),
            )
        if session.proc and session.proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                session.proc.send_signal(signal.SIGWINCH)

    # ── Topology notification channels ───────────────────────────

    def register_notify(self, topology_id: str) -> asyncio.Queue:
        """Create and register a notification queue for a topology subscriber."""
        q: asyncio.Queue = asyncio.Queue()
        self._notify_channels.setdefault(topology_id, []).append(q)
        return q

    def unregister_notify(self, topology_id: str, q: asyncio.Queue) -> None:
        channels = self._notify_channels.get(topology_id, [])
        with contextlib.suppress(ValueError):
            channels.remove(q)

    async def broadcast_topology(self, topology_id: str, message: dict) -> None:
        """Push a message to all notify-channel subscribers for a topology."""
        for q in list(self._notify_channels.get(topology_id, [])):
            await q.put(message)


# Singleton used by all routers.
exec_session_manager = ExecSessionManager()
