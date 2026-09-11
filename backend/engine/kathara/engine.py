"""KatharaEngine — realises topologies via the Kathara Python API.

No `sudo`, no host network namespace: Kathara talks to the Docker daemon via
the Docker SDK and creates collision domains as Docker bridge networks, so this
runs unprivileged on Linux and Apple silicon alike.

All Kathara calls are blocking, so they run in a worker thread to keep the
FastAPI event loop responsive.
"""

from __future__ import annotations

import asyncio
import logging

from engine.base import NodeStatus
from engine.kathara.lab_builder import build_lab
from engine.kathara.naming import lab_name, machine_name
from engine.networking import build_lab_plan

log = logging.getLogger(__name__)

_RUNNING_STATES = {"running"}


def _map_state(raw: str) -> str:
    raw = (raw or "").lower()
    if raw in _RUNNING_STATES:
        return "running"
    if raw == "paused":
        return "paused"
    return "stopped"


class KatharaEngine:
    name = "kathara"

    def _manager(self):
        from Kathara.manager.Kathara import Kathara  # lazy import

        return Kathara.get_instance()

    async def is_available(self) -> tuple[bool, str]:
        def _check() -> tuple[bool, str]:
            try:
                self._manager()
                return True, "kathara ready"
            except Exception as exc:  # pragma: no cover - environment dependent
                return False, f"{type(exc).__name__}: {exc}"

        return await asyncio.to_thread(_check)

    async def deploy(self, topology_id: str, topology_data: dict) -> dict:
        name = lab_name(topology_id, topology_data)
        plan = build_lab_plan(topology_data, name)

        def _deploy() -> dict:
            lab, name_map = build_lab(plan)
            self._manager().deploy_lab(lab)
            return {"engine": self.name, "lab_name": name, "nodes": name_map}

        state = await asyncio.to_thread(_deploy)
        log.info("Deployed lab %s (%d nodes)", name, len(plan.nodes))
        return state

    async def destroy(self, topology_id: str, topology_data: dict) -> None:
        name = lab_name(topology_id, topology_data)
        plan = build_lab_plan(topology_data, name)

        def _destroy() -> None:
            lab, _ = build_lab(plan)
            self._manager().undeploy_lab(lab=lab)

        await asyncio.to_thread(_destroy)
        log.info("Destroyed lab %s", name)

    async def status(self, topology_id: str, topology_data: dict) -> list[NodeStatus]:
        name = lab_name(topology_id, topology_data)
        plan = build_lab_plan(topology_data, name)

        def _status() -> list[NodeStatus]:
            lab, name_map = build_lab(plan)
            mgr = self._manager()
            out: list[NodeStatus] = []
            for node in plan.nodes:
                mname = name_map[node.id]
                state = "stopped"
                try:
                    obj = mgr.get_machine_api_object(mname, lab=lab)
                    state = _map_state(getattr(obj, "status", ""))
                except Exception:
                    state = "stopped"
                out.append(NodeStatus(node_id=node.id, name=node.name, state=state))
            return out

        return await asyncio.to_thread(_status)

    async def resolve_container(self, topology_id: str, topology_data: dict, node_id: str) -> str:
        name = lab_name(topology_id, topology_data)
        plan = build_lab_plan(topology_data, name)
        mname = machine_name(node_id)

        def _resolve() -> str:
            lab, _ = build_lab(plan)
            obj = self._manager().get_machine_api_object(mname, lab=lab)
            return obj.name

        return await asyncio.to_thread(_resolve)


# Singleton used by routers.
engine: KatharaEngine = KatharaEngine()
