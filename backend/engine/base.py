"""The deployment-engine seam.

Routers depend only on this interface and speak `TopologyData` + node ids.
Concrete engines (currently only Kathara) live below it. Adding a new engine —
or re-homing a deferred feature — means implementing/extending this, not
touching the routers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class NodeStatus:
    node_id: str
    name: str
    state: str  # "running" | "stopped" | "paused"


@runtime_checkable
class DeploymentEngine(Protocol):
    """Contract every deployment backend implements."""

    name: str

    async def is_available(self) -> tuple[bool, str]:
        """Return (ok, detail). Called on startup to verify the engine works."""
        ...

    async def deploy(self, topology_id: str, topology_data: dict) -> dict:
        """Instantiate the topology. Return engine_state to persist."""
        ...

    async def destroy(self, topology_id: str, topology_data: dict) -> None:
        """Tear down the topology."""
        ...

    async def status(self, topology_id: str, topology_data: dict) -> list[NodeStatus]:
        """Return the runtime status of every node."""
        ...

    async def resolve_container(self, topology_id: str, topology_data: dict, node_id: str) -> str:
        """Return the concrete container name for `node_id` (for exec/terminal)."""
        ...
