"""The deployment-engine seam.

Services speak ``LabPlan`` in and ``EngineState`` out. Concrete engines
(Kathara today, a fake for tests/dev) implement this protocol and are injected
into the app, never imported by routers.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

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
