"""The netns driver: processes inside node network namespaces, from one helper.

``ae3gis-netns`` (tools image, ``tools/nettools/ae3gis_netns.py``) runs in a
helper container with the host's PID namespace, ``CAP_SYS_ADMIN`` (``setns``)
and ``CAP_SYS_PTRACE`` (opening ``/proc/<pid>/ns/net`` of a node that holds
capabilities the driver lacks, as Kathara's do), and starts each process with
``setns`` into a node's network namespace: iperf3
ends for traffic runs, pings for the benchmark's "network ready" check. This
module builds its spec, starts it through the engine and turns its output into
events.

Events arrive on the output pump's thread (Docker) or on the loop (fake
engine), so ``on_event`` must be thread-safe; the control events a caller
waits on (``servers_ready``, ``done``, ``error``) are also recorded here and
signalled on the loop.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections import deque
from collections.abc import Callable
from typing import Any

from config import Settings
from engine.base import DeploymentEngine, HelperSpec, Sidecar

log = logging.getLogger(__name__)

SPEC_PATH = "/ae3gis/spec.json"
NOFILE = 65536  # two pipes per process; thousands of flows

Event = dict[str, Any]


def ready_timeout(servers: int) -> float:
    """How long servers get to listen: starting a process costs a few ms."""
    return 10.0 + 0.02 * servers


class NetnsDriver:
    """One running ``ae3gis-netns`` helper."""

    def __init__(
        self,
        engine: DeploymentEngine,
        settings: Settings,
        *,
        image: str,
        job_id: str,
        owner: str,
        lab_hash: str = "",
        purpose: str = "driver",
    ) -> None:
        self.engine = engine
        self.settings = settings
        self.image = image
        self.job_id = job_id
        self.owner = owner
        self.lab_hash = lab_hash
        self.purpose = purpose
        self.helper: Sidecar | None = None
        self.error: str | None = None
        self.servers_ready: Event | None = None
        self.done: Event | None = None
        self.stderr: deque[str] = deque(maxlen=20)
        self._pump: asyncio.Future | None = None
        self._ready = asyncio.Event()
        self._done = asyncio.Event()
        self._buf = b""

    async def start(self, spec: dict[str, Any], on_event: Callable[[Event], None]) -> None:
        loop = asyncio.get_running_loop()

        def control(evt: Event) -> None:
            k = evt.get("k")
            if k == "servers_ready":
                self.servers_ready = evt
                self._ready.set()
            elif k == "done":
                self.done = evt
                self._done.set()
                self._ready.set()
            elif k == "error":
                self.error = str(evt.get("message") or evt.get("code") or "driver error")
                self._ready.set()

        def on_stdout(chunk: bytes) -> None:
            self._buf += chunk
            *lines, self._buf = self._buf.split(b"\n")
            for line in lines:
                if not line.strip():
                    continue
                try:
                    evt = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(evt, dict):
                    continue
                try:
                    on_event(evt)
                except Exception as exc:  # pragma: no cover - a caller's bug; keep pumping
                    log.warning("Driver event handler failed: %s", exc)
                if evt.get("k") in ("servers_ready", "done", "error"):
                    loop.call_soon_threadsafe(control, evt)

        def on_stderr(chunk: bytes) -> None:
            for line in chunk.decode("utf-8", "replace").splitlines():
                if line.strip():
                    self.stderr.append(line.strip())

        def ended(_f: asyncio.Future) -> None:
            loop.call_soon_threadsafe(self._ready.set)
            loop.call_soon_threadsafe(self._done.set)

        self.helper = await self.engine.start_helper(
            HelperSpec(
                image=self.image,
                command=["ae3gis-netns", "--spec", SPEC_PATH],
                purpose=self.purpose,
                job_id=self.job_id,
                owner=self.owner,
                lab_hash=self.lab_hash,
                pid_host=True,
                cap_add=tuple(self.settings.driver_cap_add),
                security_opt=tuple(self.settings.driver_security_opt),
                files={SPEC_PATH: json.dumps(spec).encode()},
                nofile=NOFILE,
            )
        )
        self._pump = asyncio.ensure_future(self.helper.pump(on_stdout, on_stderr))
        self._pump.add_done_callback(ended)

    @property
    def exited(self) -> bool:
        return self._pump is not None and self._pump.done()

    def why(self) -> str:
        return self.error or "; ".join(self.stderr) or "the driver exited"

    async def wait_ready(self, timeout: float) -> Event:
        """The ``servers_ready`` event; raises if the driver fails first."""
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._ready.wait(), timeout=timeout)
        if self.servers_ready is not None and self.error is None:
            return self.servers_ready
        if self.error or self.exited:
            raise RuntimeError(f"The traffic driver failed: {self.why()}")
        raise RuntimeError(f"The traffic servers did not start within {timeout:.0f}s")

    async def wait_done(self, timeout: float | None = None) -> bool:
        """True once the driver said ``done`` or exited."""
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._done.wait(), timeout=timeout)
        return self._done.is_set()

    def done_event(self) -> asyncio.Event:
        return self._done

    async def stop(self, timeout: float = 30.0) -> None:
        """SIGINT the driver (it winds its processes down) and wait for it."""
        if self.helper is None or self._done.is_set():
            return
        await self.helper.signal("SIGINT")
        await self.wait_done(timeout)

    async def remove(self) -> None:
        if self.helper is not None:
            with contextlib.suppress(Exception):
                await self.helper.remove()
        if self._pump is not None and not self._pump.done():
            self._pump.cancel()


async def probe(
    engine: DeploymentEngine,
    settings: Settings,
    *,
    image: str,
    job_id: str,
    owner: str,
    lab_hash: str,
    probes: list[dict[str, Any]],
    timeout_s: float,
    parallel: int = 64,
    on_result: Callable[[Event], None] | None = None,
) -> dict[str, Any]:
    """Ping each ``{node, pid, target}`` until it answers or ``timeout_s`` passes.

    Returns ``{ok, failed, elapsed, results: [probe events], error}``: per probe,
    when (seconds after the start) its target first answered."""
    results: list[Event] = []

    def on_event(evt: Event) -> None:
        if evt.get("k") == "probe":
            results.append(evt)
            if on_result is not None:
                on_result(evt)

    if not probes:
        return {"ok": 0, "failed": 0, "elapsed": 0.0, "results": [], "error": None}
    driver = NetnsDriver(
        engine,
        settings,
        image=image,
        job_id=job_id,
        owner=owner,
        lab_hash=lab_hash,
        purpose="probe",
    )
    spec = {
        "mode": "probe",
        "timeout_s": timeout_s,
        "parallel": parallel,
        "interval_s": 1,
        "probes": probes,
    }
    try:
        await driver.start(spec, on_event)
        await driver.wait_done(timeout_s + 60)
    finally:
        await driver.remove()
    done = driver.done or {}
    return {
        "ok": done.get("ok", sum(1 for r in results if r.get("ok"))),
        "failed": done.get("failed", sum(1 for r in results if not r.get("ok"))),
        "elapsed": done.get("elapsed"),
        "results": results,
        "error": driver.error or (None if driver.done is not None else driver.why()),
    }
