"""Docker helpers for sidecars and container stats (engine-agnostic).

A sidecar is a short-lived container started with
``network_mode=container:<node>``: it shares the node's network namespace, so
``tcpdump`` sees the node's interfaces and ``iperf3`` sends from its addresses
and routes, whatever image the node itself runs.

Details that matter (verified against Docker Desktop + Kathara's VDE plugin):

- Output is read by *attaching*, and the attach happens **before** the
  container starts, or the first bytes (a pcap's global header) are lost.
- The log driver is ``none``: stdout can be binary (pcap) and potentially
  hundreds of MB, which the default json-file driver would store, mangled, on
  the host.
- ``demux=True`` keeps stderr (tcpdump's diagnostics) out of stdout.
- No ``hostname``: Docker rejects it with ``network_mode=container:``.
- Undeploying a lab under a sidecar works, but leaves the sidecar ``Exited``;
  callers remove sidecars before the lab, and by label afterwards.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from engine.base import IfaceCounters, RawStats, SidecarSpec

log = logging.getLogger(__name__)

LABEL_SIDECAR = "ae3gis.sidecar"
LABEL_OWNER = "ae3gis.owner"
LABEL_LAB = "ae3gis.lab_hash"
LABEL_NODE = "ae3gis.node"
LABEL_JOB = "ae3gis.job"
LABEL_PURPOSE = "ae3gis.purpose"


def sidecar_labels(spec: SidecarSpec, lab_hash: str) -> dict[str, str]:
    # Never ``app=kathara``: Kathara-labelled containers count as lab machines.
    return {
        LABEL_SIDECAR: "1",
        LABEL_OWNER: spec.owner,
        LABEL_LAB: lab_hash,
        LABEL_NODE: spec.node_id,
        LABEL_JOB: spec.job_id,
        LABEL_PURPOSE: spec.purpose,
    }


def sidecar_filters(
    *, lab_hash: str | None = None, job_id: str | None = None, owner: str | None = None
) -> list[str]:
    labels = [f"{LABEL_SIDECAR}=1"]
    if lab_hash:
        labels.append(f"{LABEL_LAB}={lab_hash}")
    if job_id:
        labels.append(f"{LABEL_JOB}={job_id}")
    if owner:
        labels.append(f"{LABEL_OWNER}={owner}")
    return labels


class DockerSidecar:
    """A running sidecar whose output stream was attached before it started."""

    def __init__(self, client: Any, container: Any, stream: Any, node_id: str) -> None:
        self._client = client
        self._container = container
        self._stream = stream
        self.name: str = container.name
        self.node_id = node_id
        self._removed = False

    @classmethod
    def start(
        cls, client: Any, node_container: Any, spec: SidecarSpec, labels: dict[str, str]
    ) -> DockerSidecar:
        """Create → attach → start (blocking; call from a worker thread)."""
        from docker.types import LogConfig

        machine = node_container.labels.get("name") or spec.node_id
        container = client.containers.create(
            spec.image,
            spec.command,
            name=f"ae3gis-{spec.purpose}-{spec.job_id[:8]}-{machine}-{uuid.uuid4().hex[:4]}",
            network_mode=f"container:{node_container.id}",
            cap_add=list(spec.cap_add),
            log_config=LogConfig(type=LogConfig.types.NONE),
            init=True,
            labels=labels,
            detach=True,
        )
        try:
            stream = client.api.attach(
                container.id, stdout=True, stderr=True, stream=True, logs=False, demux=True
            )
            container.start()
        except Exception:
            with contextlib.suppress(Exception):
                container.remove(force=True)
            raise
        return cls(client, container, stream, spec.node_id)

    def _pump_sync(
        self, on_stdout: Callable[[bytes], None], on_stderr: Callable[[bytes], None]
    ) -> int:
        try:
            for out, err in self._stream:
                if out:
                    on_stdout(out)
                if err:
                    on_stderr(err)
        except Exception as exc:  # the container was removed under us
            if not self._removed:
                log.debug("Sidecar %s stream ended: %s", self.name, exc)
        finally:
            with contextlib.suppress(Exception):
                self._stream.close()
        if self._removed:
            return -1
        try:
            return int(self._container.wait(timeout=10).get("StatusCode", -1))
        except Exception:
            return -1

    async def pump(
        self, on_stdout: Callable[[bytes], None], on_stderr: Callable[[bytes], None]
    ) -> int:
        try:
            return await asyncio.to_thread(self._pump_sync, on_stdout, on_stderr)
        except asyncio.CancelledError:
            await self.remove()
            raise

    async def signal(self, sig: str = "SIGINT") -> None:
        def _kill() -> None:
            with contextlib.suppress(Exception):
                self._container.kill(signal=sig)

        await asyncio.to_thread(_kill)

    async def exec(self, cmd: list[str], timeout: float = 5.0) -> tuple[int, str]:
        def _exec() -> tuple[int, str]:
            res = self._container.exec_run(cmd)
            return int(res.exit_code or 0), (res.output or b"").decode("utf-8", "replace")

        return await asyncio.wait_for(asyncio.to_thread(_exec), timeout)

    async def remove(self) -> None:
        if self._removed:
            return
        self._removed = True

        def _remove() -> None:
            with contextlib.suppress(Exception):
                self._container.remove(force=True)
            with contextlib.suppress(Exception):
                self._stream.close()

        await asyncio.to_thread(_remove)


def parse_stats(raw: dict[str, Any], target: str, kind: str) -> RawStats:
    """Docker's ``stats(one_shot=True)`` payload → cumulative counters."""
    cpu = raw.get("cpu_stats") or {}
    mem = raw.get("memory_stats") or {}
    mstats = mem.get("stats") or {}
    inactive = mstats.get("inactive_file", mstats.get("total_inactive_file"))
    ifaces = {
        name: IfaceCounters(
            **{k: int(v.get(k, 0) or 0) for k in IfaceCounters.__dataclass_fields__}
        )
        for name, v in (raw.get("networks") or {}).items()
    }
    return RawStats(
        target=target,
        kind=kind,  # type: ignore[arg-type]
        ts=time.time(),
        cpu_total_ns=int((cpu.get("cpu_usage") or {}).get("total_usage", 0) or 0),
        system_cpu_ns=cpu.get("system_cpu_usage"),
        online_cpus=cpu.get("online_cpus"),
        mem_usage=int(mem.get("usage", 0) or 0),
        mem_inactive_file=inactive,
        mem_limit=mem.get("limit"),
        pids=(raw.get("pids_stats") or {}).get("current"),
        ifaces=ifaces,
    )
