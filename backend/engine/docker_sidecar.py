"""Docker helpers for sidecars and helper containers (engine-agnostic).

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
import io
import logging
import tarfile
import uuid
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Any

from engine.base import HelperSpec, SidecarSpec

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


def helper_labels(spec: HelperSpec) -> dict[str, str]:
    """Helpers carry the sidecar labels (no node), so the same sweeps find them."""
    return {
        LABEL_SIDECAR: "1",
        LABEL_OWNER: spec.owner,
        LABEL_LAB: spec.lab_hash,
        LABEL_NODE: "",
        LABEL_JOB: spec.job_id,
        LABEL_PURPOSE: spec.purpose,
    }


def files_tar(files: dict[str, bytes]) -> bytes:
    """An in-memory tar of absolute ``path -> content``, parents included, for
    ``put_archive("/", ...)``."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        dirs: set[str] = set()
        for path, content in files.items():
            rel = PurePosixPath(path.lstrip("/"))
            for parent in reversed(rel.parents[:-1]):
                if str(parent) not in dirs:
                    dirs.add(str(parent))
                    info = tarfile.TarInfo(str(parent))
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    tar.addfile(info)
            info = tarfile.TarInfo(str(rel))
            info.size = len(content)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


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
    def _launch(
        cls,
        client: Any,
        image: str,
        command: list[str],
        node_id: str,
        files: dict[str, bytes] | None = None,
        **create: Any,
    ) -> DockerSidecar:
        """Create → write files → attach → start (blocking; call from a worker thread)."""
        from docker.types import LogConfig

        container = client.containers.create(
            image,
            command,
            log_config=LogConfig(type=LogConfig.types.NONE),
            init=True,
            detach=True,
            **create,
        )
        try:
            if files:
                container.put_archive("/", files_tar(files))
            stream = client.api.attach(
                container.id, stdout=True, stderr=True, stream=True, logs=False, demux=True
            )
            container.start()
        except Exception:
            with contextlib.suppress(Exception):
                container.remove(force=True)
            raise
        return cls(client, container, stream, node_id)

    @classmethod
    def start(
        cls, client: Any, node_container: Any, spec: SidecarSpec, labels: dict[str, str]
    ) -> DockerSidecar:
        """A sidecar in ``node_container``'s network namespace."""
        machine = node_container.labels.get("name") or spec.node_id
        return cls._launch(
            client,
            spec.image,
            spec.command,
            spec.node_id,
            name=f"ae3gis-{spec.purpose}-{spec.job_id[:8]}-{machine}-{uuid.uuid4().hex[:4]}",
            network_mode=f"container:{node_container.id}",
            cap_add=list(spec.cap_add),
            labels=labels,
        )

    @classmethod
    def start_helper(cls, client: Any, spec: HelperSpec) -> DockerSidecar:
        """A helper container: no network of its own, host namespaces as asked."""
        from docker.types import Ulimit

        create: dict[str, Any] = {
            "name": f"ae3gis-{spec.purpose}-{spec.job_id[:8]}-{uuid.uuid4().hex[:4]}",
            "network_mode": "none",
            "labels": helper_labels(spec),
        }
        if spec.cap_add:
            create["cap_add"] = list(spec.cap_add)
        if spec.security_opt:
            create["security_opt"] = list(spec.security_opt)
        if spec.pid_host:
            create["pid_mode"] = "host"
        if spec.cgroupns_host:
            create["cgroupns"] = "host"
        if spec.binds:
            create["volumes"] = {
                src: {"bind": dst, "mode": "ro"} for src, dst in spec.binds.items()
            }
        if spec.nofile:
            create["ulimits"] = [Ulimit(name="nofile", soft=spec.nofile, hard=spec.nofile)]
        return cls._launch(client, spec.image, spec.command, "", spec.files, **create)

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
