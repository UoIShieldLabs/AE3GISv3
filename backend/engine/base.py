"""The deployment-engine seam.

Services speak ``LabPlan`` in and ``EngineState`` out. Concrete engines
(Kathara today, a fake for tests/dev) implement this protocol and are injected
into the app, never imported by routers.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
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

    async def list_labs(self) -> list[LabRef]: ...

    async def purge(self, lab_hash: str) -> None: ...

    async def images_present(self, images: list[str]) -> dict[str, bool]: ...

    async def pull_image(self, image: str, on_progress: Progress) -> None: ...
