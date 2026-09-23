"""In-memory DeploymentEngine for tests and for running the UI without Docker.

Select with ``AE3GIS_ENGINE=fake``. Deploys succeed instantly and every node
reports running. Test hooks:

- ``fail_deploy`` / ``fail_destroy``: raise instead of deploying/destroying.
- ``fail_after_create``: create the lab, then raise (a deploy that dies part-way).
- ``crash_nodes``: node id -> container output; those nodes exit right after start.
- ``pull_gate`` / ``build_gate``: an ``asyncio.Event`` that pulls / builds wait on.
- ``fail_build``: image ref -> error message.

Images under ``ae3gis.local/`` (built by AE3GIS, never pulled) are absent until
built; other refs follow ``present_images``. ``build_delay`` paces the simulated
build output so the UI can show progress.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

from domain.plan import LabPlan
from engine.base import (
    BuildError,
    BuildSpec,
    BuildSupport,
    EngineState,
    ImageInfo,
    LabRef,
    NodeLog,
    NodeStatus,
    Progress,
    normalize_ref,
)
from engine.kathara.naming import lab_hash as hash_for_name

LOCAL_PREFIX = "ae3gis.local/"


@dataclass
class _Lab:
    state: EngineState
    running: set[str] = field(default_factory=set)


class FakeEngine:
    name = "fake"

    def __init__(self) -> None:
        self.labs: dict[str, _Lab] = {}
        self.fail_deploy: Exception | None = None
        self.fail_after_create: Exception | None = None
        self.fail_destroy: Exception | None = None
        self.crash_nodes: dict[str, str] = {}
        self.present_images: set[str] | None = None  # None = everything present
        self.pulled: list[str] = []
        self.pull_gate: asyncio.Event | None = None
        self.built: dict[str, ImageInfo] = {}  # normalized ref -> image
        self.builds: list[BuildSpec] = []
        self.build_gate: asyncio.Event | None = None
        self.fail_build: dict[str, str] = {}
        self.build_delay = 0.0
        self.platform = "linux/amd64"
        self.can_build = True

    @staticmethod
    def _hash(state: EngineState) -> str:
        # Same fallback as the Kathara engine: a provisional state has only a name.
        return state.lab_hash or hash_for_name(state.lab_name)

    async def is_available(self) -> tuple[bool, str]:
        return True, "fake engine"

    async def deploy(self, plan: LabPlan, on_progress: Progress) -> EngineState:
        if self.fail_deploy:
            raise self.fail_deploy
        state = EngineState(
            engine=self.name,
            lab_name=plan.name,
            lab_hash=hash_for_name(plan.name),
            user_prefix="fake",
            nodes={n.id: n.machine_name for n in plan.nodes},
        )
        running = {nid for nid in state.nodes if nid not in self.crash_nodes}
        self.labs[state.lab_hash] = _Lab(state=state, running=running)
        if self.fail_after_create:
            raise self.fail_after_create
        on_progress(f"Started {len(plan.nodes)} machines")
        return state

    async def destroy(self, state: EngineState) -> None:
        if self.fail_destroy:
            raise self.fail_destroy
        self.labs.pop(self._hash(state), None)

    async def status(self, state: EngineState) -> list[NodeStatus]:
        lab = self.labs.get(self._hash(state))
        return [
            NodeStatus(
                node_id=nid, name=m, state="running" if lab and nid in lab.running else "stopped"
            )
            for nid, m in state.nodes.items()
        ]

    async def resolve_container(self, state: EngineState, node_id: str) -> str:
        lab = self.labs.get(self._hash(state))
        if not lab or node_id not in lab.running:
            raise LookupError(f"Device '{node_id}' is not running")
        return f"fake_{state.nodes.get(node_id, node_id)}"

    async def node_logs(self, state: EngineState, tail: int = 30) -> list[NodeLog]:
        lab = self.labs.get(self._hash(state))
        if not lab:
            return []
        return [
            NodeLog(node_id=nid, name=m, exit_code=1, log=self.crash_nodes.get(nid, ""))
            for nid, m in lab.state.nodes.items()
            if nid not in lab.running
        ]

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

    def _local(self, ref: str) -> ImageInfo | None:
        built = self.built.get(normalize_ref(ref))
        if built is not None:
            return built
        if ref.startswith(LOCAL_PREFIX):
            return None
        if self.present_images is None or ref in self.present_images:
            return ImageInfo(ref=ref, id=f"sha256:{abs(hash(ref)):x}")
        return None

    async def images_present(self, images: list[str]) -> dict[str, bool]:
        return {i: self._local(i) is not None for i in images}

    async def inspect_images(self, refs: list[str]) -> dict[str, ImageInfo | None]:
        return {r: self._local(r) for r in refs}

    async def build_support(self) -> BuildSupport:
        detail = "fake builder" if self.can_build else "builds disabled"
        return BuildSupport(self.can_build, detail, self.platform)

    async def build_image(self, spec: BuildSpec, on_line: Progress) -> None:
        if self.build_gate is not None:
            await self.build_gate.wait()
        self.builds.append(spec)
        lines = [
            '#0 building with "default" instance using docker driver',
            f"#1 [internal] load build definition from {spec.dockerfile}",
            "#2 [1/3] FROM docker.io/library/ubuntu:24.04",
            "#3 [2/3] RUN apt-get update && apt-get install -y --no-install-recommends tools",
            "#4 [3/3] COPY . /opt/app",
            "#5 exporting to image",
        ]
        for line in lines:
            on_line(line)
            if self.build_delay:
                await asyncio.sleep(self.build_delay)
        if spec.ref in self.fail_build:
            on_line(f"ERROR: {self.fail_build[spec.ref]}")
            raise BuildError(self.fail_build[spec.ref])
        on_line(f"#5 naming to {normalize_ref(spec.ref)} done")
        self.built[normalize_ref(spec.ref)] = ImageInfo(
            ref=spec.ref,
            id=f"sha256:{len(self.builds):064x}",
            labels=dict(spec.labels),
            created=datetime.now(UTC).isoformat(),
            size=180_000_000,
            arch=self.platform.split("/")[-1],
        )

    async def pull_image(self, image: str, on_progress: Progress) -> None:
        if self.pull_gate is not None:
            await self.pull_gate.wait()
        self.pulled.append(image)
        on_progress(f"{image}: Pull complete")
        if self.present_images is not None:
            self.present_images.add(image)


def make_engine(name: str):
    """Engine factory used by the app (``Settings.engine``)."""
    if name == "fake":
        engine = FakeEngine()
        engine.build_delay = 0.5  # visible progress when driving the UI
        return engine
    from engine.kathara.engine import KatharaEngine

    return KatharaEngine()
