"""In-memory DeploymentEngine for tests and for running the UI without Docker.

Select with ``AE3GIS_ENGINE=fake``. Deploys succeed instantly and every node
reports running; ``fail_deploy``/``fail_destroy`` let tests exercise error
paths.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from domain.plan import LabPlan
from engine.base import EngineState, LabRef, NodeStatus, Progress


@dataclass
class _Lab:
    state: EngineState
    running: set[str] = field(default_factory=set)


class FakeEngine:
    name = "fake"

    def __init__(self) -> None:
        self.labs: dict[str, _Lab] = {}
        self.fail_deploy: Exception | None = None
        self.fail_destroy: Exception | None = None
        self.present_images: set[str] | None = None  # None = everything present
        self.pulled: list[str] = []

    async def is_available(self) -> tuple[bool, str]:
        return True, "fake engine"

    async def deploy(self, plan: LabPlan, on_progress: Progress) -> EngineState:
        if self.fail_deploy:
            raise self.fail_deploy
        lab_hash = hashlib.md5(plan.name.encode()).hexdigest()[:22]  # noqa: S324
        state = EngineState(
            engine=self.name,
            lab_name=plan.name,
            lab_hash=lab_hash,
            user_prefix="fake",
            nodes={n.id: n.machine_name for n in plan.nodes},
        )
        self.labs[lab_hash] = _Lab(state=state, running=set(state.nodes))
        on_progress(f"Started {len(plan.nodes)} machines")
        return state

    async def destroy(self, state: EngineState) -> None:
        if self.fail_destroy:
            raise self.fail_destroy
        self.labs.pop(state.lab_hash, None)

    async def status(self, state: EngineState) -> list[NodeStatus]:
        lab = self.labs.get(state.lab_hash)
        return [
            NodeStatus(
                node_id=nid, name=m, state="running" if lab and nid in lab.running else "stopped"
            )
            for nid, m in state.nodes.items()
        ]

    async def resolve_container(self, state: EngineState, node_id: str) -> str:
        lab = self.labs.get(state.lab_hash)
        if not lab or node_id not in lab.running:
            raise LookupError(f"Device '{node_id}' is not running")
        return f"fake_{state.nodes.get(node_id, node_id)}"

    async def list_labs(self) -> list[LabRef]:
        return [
            LabRef(
                lab_hash=h,
                user_prefix=lab.state.user_prefix,
                machines=sorted(lab.state.nodes.values()),
                running=len(lab.running),
                total=len(lab.state.nodes),
            )
            for h, lab in self.labs.items()
        ]

    async def purge(self, lab_hash: str) -> None:
        self.labs.pop(lab_hash, None)

    async def images_present(self, images: list[str]) -> dict[str, bool]:
        return {i: (self.present_images is None or i in self.present_images) for i in images}

    async def pull_image(self, image: str, on_progress: Progress) -> None:
        self.pulled.append(image)
        on_progress(f"{image}: Pull complete")
        if self.present_images is not None:
            self.present_images.add(image)


def make_engine(name: str):
    """Engine factory used by the app (``Settings.engine``)."""
    if name == "fake":
        return FakeEngine()
    from engine.kathara.engine import KatharaEngine

    return KatharaEngine()
