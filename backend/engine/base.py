"""The deployment-engine seam.

Services speak ``LabPlan`` in and ``EngineState`` out. Concrete engines
(Kathara today, a fake for tests/dev) implement this protocol and are injected
into the app, never imported by routers.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from domain.plan import LabPlan

Progress = Callable[[str], None]


@dataclass
class EngineState:
    """What an engine needs to find a deployed lab again, persisted as JSON."""

    engine: str
    lab_name: str
    lab_hash: str = ""
    user_prefix: str = ""
    nodes: dict[str, str] = field(default_factory=dict)  # node id -> machine name
    # The plan's links as deployed (``LabPlan.links()``: collision domain,
    # connection id, endpoints with interface names). Captures resolve targets
    # against this, not a plan recomputed from data edited since the deploy.
    links: list[dict[str, Any]] = field(default_factory=list)
    deployed_version: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> EngineState | None:
        if not raw or not isinstance(raw, dict):
            return None
        return cls(
            engine=str(raw.get("engine", "")),
            lab_name=str(raw.get("lab_name", "")),
            lab_hash=str(raw.get("lab_hash", "") or ""),
            user_prefix=str(raw.get("user_prefix", "") or ""),
            nodes=dict(raw.get("nodes") or {}),
            links=list(raw.get("links") or []),
            deployed_version=raw.get("deployed_version"),
        )


@dataclass
class NodeStatus:
    node_id: str
    name: str
    state: str  # "running" | "stopped" | "paused"


@dataclass
class NodeLog:
    """The tail of a node's container output after it stopped unexpectedly."""

    node_id: str
    name: str
    exit_code: int | None
    log: str

    def summary(self) -> str:
        lines = [ln.strip() for ln in self.log.splitlines() if ln.strip()]
        code = "?" if self.exit_code is None else self.exit_code
        return f"{self.name} exited ({code})" + (f": {lines[-1]}" if lines else "")


@dataclass
class ImageInfo:
    """A local image as the Docker daemon reports it."""

    ref: str
    id: str
    labels: dict[str, str] = field(default_factory=dict)
    created: str | None = None
    size: int | None = None
    arch: str | None = None


@dataclass
class BuildSpec:
    """Build ``context/dockerfile`` and tag it ``ref`` with ``labels``."""

    ref: str
    context: Path
    dockerfile: str = "Dockerfile"
    args: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    pull: bool = False  # refresh the base image
    no_cache: bool = False


@dataclass
class BuildSupport:
    ok: bool
    detail: str
    platform: str  # e.g. "linux/arm64"


class BuildError(RuntimeError):
    """An image build failed; the message is the most useful error line."""


def normalize_ref(ref: str) -> str:
    """``name`` → ``name:latest`` (registry ports and digests left alone)."""
    ref = ref.strip()
    if "@" in ref or ":" in ref.rsplit("/", 1)[-1]:
        return ref
    return f"{ref}:latest"


@dataclass
class LabRef:
    """A lab that exists on the engine's backend right now (for reconcile)."""

    lab_hash: str
    user_prefix: str
    machines: list[str]
    running: int
    total: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── sidecars: helper containers inside a node's network namespace ──────


@dataclass
class NodeInterface:
    """An interface of a running node, as the engine attached it."""

    name: str  # e.g. "eth0"
    collision_domain: str


@dataclass
class SidecarSpec:
    """Run ``command`` in ``image`` inside ``node_id``'s network namespace.

    The sidecar sees the node's interfaces and sends from its addresses and
    routes, whatever image the node runs. ``purpose`` (capture, iperf-server,
    iperf-client, probe), ``job_id`` and ``owner`` (the backend instance) are
    stamped as labels so sidecars can be found and removed later.
    """

    node_id: str
    image: str
    command: list[str]
    purpose: str
    job_id: str
    owner: str
    cap_add: tuple[str, ...] = ("NET_RAW", "NET_ADMIN")


@runtime_checkable
class Sidecar(Protocol):
    name: str
    node_id: str

    async def pump(
        self, on_stdout: Callable[[bytes], None], on_stderr: Callable[[bytes], None]
    ) -> int:
        """Feed the sidecar's output to the callbacks until it exits; return its
        exit code. Callbacks may run on a worker thread. Cancelling removes it."""
        ...

    async def signal(self, sig: str = "SIGINT") -> None: ...

    async def exec(self, cmd: list[str], timeout: float = 5.0) -> tuple[int, str]:
        """Run a command in the sidecar; (exit code, combined output)."""
        ...

    async def remove(self) -> None:
        """Force-remove the sidecar (idempotent)."""
        ...


@dataclass
class SidecarInfo:
    name: str
    node_id: str
    job_id: str
    purpose: str
    lab_hash: str
    owner: str
    status: str


# ── telemetry ─────────────────────────────────────────────────────────


@dataclass
class IfaceCounters:
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    rx_dropped: int = 0
    tx_dropped: int = 0
    rx_errors: int = 0
    tx_errors: int = 0


@dataclass
class RawStats:
    """One cgroup sample of a node or sidecar (cumulative counters)."""

    target: str  # node id, or sidecar name
    kind: Literal["node", "sidecar"]
    ts: float  # unix seconds
    cpu_total_ns: int
    system_cpu_ns: int | None
    online_cpus: int | None
    mem_usage: int
    mem_inactive_file: int | None
    mem_limit: int | None
    pids: int | None
    ifaces: dict[str, IfaceCounters] = field(default_factory=dict)


@dataclass
class NodeRuntimeInfo:
    """What a node actually runs: image, architecture and resource limits."""

    node_id: str
    machine: str
    container: str
    image_ref: str
    image_id: str
    fingerprint: str | None = None
    arch: str | None = None
    nano_cpus: int | None = None
    mem_limit: int | None = None
    cpuset: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class DeploymentEngine(Protocol):
    name: str

    async def is_available(self) -> tuple[bool, str]: ...

    async def deploy(self, plan: LabPlan, on_progress: Progress) -> EngineState: ...

    async def destroy(self, state: EngineState) -> None: ...

    async def status(self, state: EngineState) -> list[NodeStatus]: ...

    async def resolve_container(self, state: EngineState, node_id: str) -> str: ...

    async def node_logs(self, state: EngineState, tail: int = 30) -> list[NodeLog]:
        """Output of the lab's nodes whose container has exited (crashed CMD etc.)."""
        ...

    async def list_labs(self) -> list[LabRef]: ...

    async def purge(self, lab_hash: str) -> None: ...

    async def images_present(self, images: list[str]) -> dict[str, bool]: ...

    async def pull_image(self, image: str, on_progress: Progress) -> None: ...

    async def inspect_images(self, refs: list[str]) -> dict[str, ImageInfo | None]:
        """Local image details per ref (None when absent)."""
        ...

    async def build_support(self) -> BuildSupport:
        """Whether this host can build images, and for which platform."""
        ...

    async def build_image(self, spec: BuildSpec, on_line: Progress) -> None:
        """Build an image, streaming output lines; raise ``BuildError`` on failure.

        Cancelling the awaiting task must stop the build.
        """
        ...

    # ── sidecars and telemetry (captures, traffic runs) ──

    async def node_interfaces(self, state: EngineState, node_id: str) -> list[NodeInterface]:
        """The node's interfaces as attached right now (checks the saved link map)."""
        ...

    async def start_sidecar(self, state: EngineState, spec: SidecarSpec) -> Sidecar:
        """Start a sidecar in the node's network namespace, output already attached."""
        ...

    async def list_sidecars(
        self, *, lab_hash: str | None = None, owner: str | None = None
    ) -> list[SidecarInfo]: ...

    async def remove_sidecars(
        self, *, lab_hash: str | None = None, job_id: str | None = None, owner: str | None = None
    ) -> int:
        """Force-remove matching sidecars (at least one filter); return how many."""
        ...

    async def sample_stats(
        self, state: EngineState, node_ids: list[str], sidecars: list[str] = ()
    ) -> list[RawStats]:
        """One sample per running node / named sidecar (missing ones are skipped)."""
        ...

    async def node_runtime_info(self, state: EngineState) -> list[NodeRuntimeInfo]: ...

    async def environment(self) -> dict[str, Any]:
        """Facts about the host and the engine, recorded with every run."""
        ...
