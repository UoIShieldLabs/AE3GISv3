"""KatharaEngine — realises LabPlans via the Kathara Python API.

Deploy/undeploy go through Kathara. Everything that *observes* a lab (status,
container lookup, listing, purge) goes to the Docker daemon directly by the
labels Kathara stamps on its containers (``app=kathara``, ``lab_hash``,
``name``, ``user``). That makes lookups independent of Kathara's per-user
prefix, which is derived from the backend's hostname and therefore changes
whenever the backend container is recreated — the cause of "device not found"
and orphaned labs before this design.

All Kathara/Docker calls are blocking and run in a worker thread.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from domain.images import LABEL_FINGERPRINT
from domain.plan import LabPlan
from engine.base import (
    BuildSpec,
    BuildSupport,
    EngineState,
    ImageInfo,
    LabRef,
    NodeInterface,
    NodeLog,
    NodeRuntimeInfo,
    NodeStatus,
    Progress,
    RawStats,
    SidecarInfo,
    SidecarSpec,
    normalize_ref,
)
from engine.docker_build import buildx_available, docker_build
from engine.docker_sidecar import (
    LABEL_JOB,
    LABEL_LAB,
    LABEL_NODE,
    LABEL_OWNER,
    LABEL_PURPOSE,
    DockerSidecar,
    parse_stats,
    sidecar_filters,
    sidecar_labels,
)
from engine.kathara.lab_builder import build_lab
from engine.kathara.naming import lab_hash as hash_for_name
from engine.kathara.naming import machine_name

log = logging.getLogger(__name__)

_KATHARA_LABEL = "app=kathara"

# Docker reports the daemon's machine; images are built for linux/<arch>.
_ARCH = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}


def _map_state(raw: str) -> str:
    raw = (raw or "").lower()
    if raw == "running":
        return "running"
    if raw == "paused":
        return "paused"
    return "stopped"


class KatharaEngine:
    name = "kathara"

    # ── clients ──
    def _manager(self):
        from Kathara.manager.Kathara import Kathara  # lazy import

        return Kathara.get_instance()

    def _docker(self):
        import docker  # lazy import

        return docker.from_env()

    @staticmethod
    def _hash(state: EngineState) -> str:
        return state.lab_hash or hash_for_name(state.lab_name)

    def _containers(self, lab_hash: str) -> list[Any]:
        return self._docker().containers.list(
            all=True, filters={"label": [_KATHARA_LABEL, f"lab_hash={lab_hash}"]}
        )

    # ── protocol ──
    async def is_available(self) -> tuple[bool, str]:
        def _check() -> tuple[bool, str]:
            try:
                self._manager()
                self._docker().ping()
                return True, "kathara ready"
            except Exception as exc:  # pragma: no cover - environment dependent
                return False, f"{type(exc).__name__}: {exc}"

        return await asyncio.to_thread(_check)

    async def deploy(self, plan: LabPlan, on_progress: Progress) -> EngineState:
        def _deploy() -> EngineState:
            from Kathara import utils  # lazy

            lab, name_map = build_lab(plan)
            on_progress(
                f"Starting {len(plan.nodes)} machines and {len(plan.collision_domains)} links"
            )
            self._manager().deploy_lab(lab)
            return EngineState(
                engine=self.name,
                lab_name=plan.name,
                lab_hash=lab.hash,
                user_prefix=utils.get_current_user_name(),
                nodes=name_map,
            )

        state = await asyncio.to_thread(_deploy)
        log.info("Deployed lab %s (%s, %d nodes)", state.lab_name, state.lab_hash, len(plan.nodes))
        return state

    async def destroy(self, state: EngineState) -> None:
        lab_hash = self._hash(state)

        def _destroy() -> None:
            # Sidecars share node network namespaces: remove them first.
            self._remove_sidecars_sync(sidecar_filters(lab_hash=lab_hash))
            # Kathara's own undeploy only sees the current user prefix; the label
            # purge below catches anything it cannot.
            with contextlib.suppress(Exception):
                self._manager().undeploy_lab(lab_hash=lab_hash)
            self._purge_sync(lab_hash)

        await asyncio.to_thread(_destroy)
        log.info("Destroyed lab %s (%s)", state.lab_name, lab_hash)

    async def status(self, state: EngineState) -> list[NodeStatus]:
        lab_hash = self._hash(state)

        def _status() -> list[NodeStatus]:
            by_machine = {c.labels.get("name", ""): c for c in self._containers(lab_hash)}
            out: list[NodeStatus] = []
            for node_id, mname in state.nodes.items():
                c = by_machine.get(mname)
                out.append(
                    NodeStatus(
                        node_id=node_id, name=mname, state=_map_state(c.status) if c else "stopped"
                    )
                )
            return out

        return await asyncio.to_thread(_status)

    async def resolve_container(self, state: EngineState, node_id: str) -> str:
        lab_hash = self._hash(state)
        mname = state.nodes.get(node_id) or machine_name(node_id)

        def _resolve() -> str:
            for c in self._containers(lab_hash):
                if c.labels.get("name") == mname:
                    return c.name
            raise LookupError(f"Device '{mname}' is not running in this lab")

        return await asyncio.to_thread(_resolve)

    async def node_logs(self, state: EngineState, tail: int = 30) -> list[NodeLog]:
        lab_hash = self._hash(state)
        node_for = {m: nid for nid, m in state.nodes.items()}

        def _logs() -> list[NodeLog]:
            out: list[NodeLog] = []
            for c in self._containers(lab_hash):
                # "created" containers never ran (a deploy that stopped early);
                # only exited ones have something to say.
                if c.status not in ("exited", "dead"):
                    continue
                mname = c.labels.get("name", c.name)
                try:
                    text = c.logs(tail=tail).decode("utf-8", errors="replace")
                except Exception as exc:  # pragma: no cover - environment dependent
                    text = f"(logs unavailable: {exc})"
                out.append(
                    NodeLog(
                        node_id=node_for.get(mname, mname),
                        name=mname,
                        exit_code=(c.attrs.get("State") or {}).get("ExitCode"),
                        log=text,
                    )
                )
            return out

        return await asyncio.to_thread(_logs)

    async def list_labs(self) -> list[LabRef]:
        def _list() -> list[LabRef]:
            groups: dict[str, dict[str, Any]] = {}
            for c in self._docker().containers.list(all=True, filters={"label": [_KATHARA_LABEL]}):
                h = c.labels.get("lab_hash", "")
                g = groups.setdefault(
                    h, {"user": c.labels.get("user", ""), "machines": [], "running": 0}
                )
                g["machines"].append(c.labels.get("name", c.name))
                if c.status == "running":
                    g["running"] += 1
            return [
                LabRef(
                    lab_hash=h,
                    user_prefix=g["user"],
                    machines=sorted(g["machines"]),
                    running=g["running"],
                    total=len(g["machines"]),
                )
                for h, g in groups.items()
            ]

        return await asyncio.to_thread(_list)

    async def purge(self, lab_hash: str) -> None:
        await asyncio.to_thread(self._purge_sync, lab_hash)

    def _purge_sync(self, lab_hash: str) -> None:
        client = self._docker()
        self._remove_sidecars_sync(sidecar_filters(lab_hash=lab_hash))
        for c in client.containers.list(
            all=True, filters={"label": [_KATHARA_LABEL, f"lab_hash={lab_hash}"]}
        ):
            with contextlib.suppress(Exception):
                c.remove(force=True)
        # Kathara names its networks kathara_<user>_<cd>_<lab_hash>; labels vary by version.
        for n in client.networks.list():
            labels = n.attrs.get("Labels") or {}
            if labels.get("lab_hash") == lab_hash or (
                n.name.startswith("kathara_") and n.name.endswith(f"_{lab_hash}")
            ):
                with contextlib.suppress(Exception):
                    n.remove()

    async def images_present(self, images: list[str]) -> dict[str, bool]:
        found = await self.inspect_images(images)
        return {i: found.get(i) is not None for i in images}

    async def inspect_images(self, refs: list[str]) -> dict[str, ImageInfo | None]:
        def _inspect() -> dict[str, ImageInfo | None]:
            by_tag: dict[str, Any] = {}
            for img in self._docker().images.list():
                for t in img.tags or []:
                    by_tag[t] = img
            out: dict[str, ImageInfo | None] = {}
            for ref in refs:
                img = by_tag.get(normalize_ref(ref))
                out[ref] = (
                    ImageInfo(
                        ref=ref,
                        id=img.id,
                        labels=dict(img.labels or {}),
                        created=img.attrs.get("Created"),
                        size=img.attrs.get("Size"),
                        arch=img.attrs.get("Architecture"),
                    )
                    if img is not None
                    else None
                )
            return out

        return await asyncio.to_thread(_inspect)

    async def build_support(self) -> BuildSupport:
        def _arch() -> str:
            raw = str(self._docker().info().get("Architecture", ""))
            return _ARCH.get(raw, raw or "unknown")

        try:
            platform = f"linux/{await asyncio.to_thread(_arch)}"
        except Exception as exc:  # pragma: no cover - environment dependent
            return BuildSupport(False, f"Docker is not reachable: {exc}", "unknown")
        ok, detail = await buildx_available()
        return BuildSupport(ok, detail, platform)

    async def build_image(self, spec: BuildSpec, on_line: Progress) -> None:
        await docker_build(spec, on_line)

    async def pull_image(self, image: str, on_progress: Progress) -> None:
        def _pull() -> None:
            repo, _, tag = image.partition(":")
            last = ""
            for line in self._docker().api.pull(
                repo, tag=tag or "latest", stream=True, decode=True
            ):
                status = line.get("status", "")
                if status and status != last and not status.startswith("Pulling fs layer"):
                    last = status
                    on_progress(f"{image}: {status}")

        await asyncio.to_thread(_pull)

    # ── sidecars ──
    def _node_container(self, state: EngineState, node_id: str) -> Any:
        mname = state.nodes.get(node_id) or machine_name(node_id)
        for c in self._containers(self._hash(state)):
            if c.labels.get("name") == mname:
                return c
        raise LookupError(f"Device '{mname}' is not running in this lab")

    async def node_interfaces(self, state: EngineState, node_id: str) -> list[NodeInterface]:
        def _ifaces() -> list[NodeInterface]:
            c = self._node_container(state, node_id)
            out = []
            for net in (c.attrs.get("NetworkSettings") or {}).get("Networks", {}).values():
                opts = net.get("DriverOpts") or {}
                if "kathara.iface" in opts:
                    out.append(
                        NodeInterface(
                            name=f"eth{opts['kathara.iface']}",
                            collision_domain=opts.get("kathara.link", ""),
                        )
                    )
            return sorted(out, key=lambda i: (len(i.name), i.name))

        return await asyncio.to_thread(_ifaces)

    async def start_sidecar(self, state: EngineState, spec: SidecarSpec) -> DockerSidecar:
        lab_hash = self._hash(state)

        def _start() -> DockerSidecar:
            node = self._node_container(state, spec.node_id)
            if node.status != "running":
                raise LookupError(f"Device '{node.labels.get('name')}' is not running")
            return DockerSidecar.start(self._docker(), node, spec, sidecar_labels(spec, lab_hash))

        return await asyncio.to_thread(_start)

    async def list_sidecars(
        self, *, lab_hash: str | None = None, owner: str | None = None
    ) -> list[SidecarInfo]:
        def _list() -> list[SidecarInfo]:
            flt = sidecar_filters(lab_hash=lab_hash, owner=owner)
            return [
                SidecarInfo(
                    name=c.name,
                    node_id=c.labels.get(LABEL_NODE, ""),
                    job_id=c.labels.get(LABEL_JOB, ""),
                    purpose=c.labels.get(LABEL_PURPOSE, ""),
                    lab_hash=c.labels.get(LABEL_LAB, ""),
                    owner=c.labels.get(LABEL_OWNER, ""),
                    status=c.status,
                )
                for c in self._docker().containers.list(all=True, filters={"label": flt})
            ]

        return await asyncio.to_thread(_list)

    def _remove_sidecars_sync(self, labels: list[str]) -> int:
        removed = 0
        for c in self._docker().containers.list(all=True, filters={"label": labels}):
            with contextlib.suppress(Exception):
                c.remove(force=True)
                removed += 1
        return removed

    async def remove_sidecars(
        self, *, lab_hash: str | None = None, job_id: str | None = None, owner: str | None = None
    ) -> int:
        if not (lab_hash or job_id or owner):
            raise ValueError("remove_sidecars needs a filter")
        flt = sidecar_filters(lab_hash=lab_hash, job_id=job_id, owner=owner)
        return await asyncio.to_thread(self._remove_sidecars_sync, flt)

    # ── telemetry ──
    async def sample_stats(
        self, state: EngineState, node_ids: list[str], sidecars: list[str] = ()
    ) -> list[RawStats]:
        lab_hash = self._hash(state)

        def _sample() -> list[RawStats]:
            client = self._docker()
            by_machine = {
                c.labels.get("name", ""): c
                for c in self._containers(lab_hash)
                if c.status == "running"
            }
            targets: list[tuple[str, str, Any]] = []
            for nid in node_ids:
                c = by_machine.get(state.nodes.get(nid) or machine_name(nid))
                if c is not None:
                    targets.append((nid, "node", c))
            for name in sidecars:
                with contextlib.suppress(Exception):
                    targets.append((name, "sidecar", client.containers.get(name)))

            def one(t: tuple[str, str, Any]) -> RawStats | None:
                try:
                    return parse_stats(t[2].stats(stream=False, one_shot=True), t[0], t[1])
                except Exception:
                    return None

            if not targets:
                return []
            with ThreadPoolExecutor(max_workers=min(8, len(targets))) as pool:
                return [r for r in pool.map(one, targets) if r is not None]

        return await asyncio.to_thread(_sample)

    async def node_runtime_info(self, state: EngineState) -> list[NodeRuntimeInfo]:
        lab_hash = self._hash(state)
        node_for = {m: nid for nid, m in state.nodes.items()}

        def _info() -> list[NodeRuntimeInfo]:
            client = self._docker()
            images: dict[str, Any] = {}
            out = []
            for c in self._containers(lab_hash):
                image_id = c.attrs.get("Image", "")
                if image_id not in images:
                    try:
                        images[image_id] = client.images.get(image_id)
                    except Exception:
                        images[image_id] = None
                img = images[image_id]
                host = c.attrs.get("HostConfig") or {}
                mname = c.labels.get("name", c.name)
                out.append(
                    NodeRuntimeInfo(
                        node_id=node_for.get(mname, mname),
                        machine=mname,
                        container=c.name,
                        image_ref=(c.attrs.get("Config") or {}).get("Image", ""),
                        image_id=image_id,
                        fingerprint=(img.labels or {}).get(LABEL_FINGERPRINT) if img else None,
                        arch=img.attrs.get("Architecture") if img else None,
                        nano_cpus=host.get("NanoCpus") or None,
                        mem_limit=host.get("Memory") or None,
                        cpuset=host.get("CpusetCpus") or None,
                    )
                )
            return sorted(out, key=lambda i: i.node_id)

        return await asyncio.to_thread(_info)

    async def environment(self) -> dict[str, Any]:
        def _env() -> dict[str, Any]:
            from Kathara.setting.Setting import Setting
            from Kathara.version import CURRENT_VERSION

            client = self._docker()
            info = client.info()
            version = client.version()
            plugin_name = Setting.get_instance().network_plugin
            arch = _ARCH.get(str(info.get("Architecture", "")), info.get("Architecture"))
            plugin: dict[str, Any] = {"name": plugin_name}
            with contextlib.suppress(Exception):
                p = client.plugins.get(f"{plugin_name}:{arch}")
                plugin.update(id=p.id, enabled=p.enabled, reference=p.attrs.get("PluginReference"))
            return {
                "engine": self.name,
                "kathara": {"version": CURRENT_VERSION, "network_plugin": plugin},
                "docker": {
                    "server_version": version.get("Version"),
                    "api_version": version.get("ApiVersion"),
                    "os": info.get("OperatingSystem"),
                    "os_type": info.get("OSType"),
                    "kernel": info.get("KernelVersion"),
                    "arch": info.get("Architecture"),
                    "ncpu": info.get("NCPU"),
                    "mem_total": info.get("MemTotal"),
                    "cgroup_version": info.get("CgroupVersion"),
                    "cgroup_driver": info.get("CgroupDriver"),
                    "storage_driver": info.get("Driver"),
                    "default_runtime": info.get("DefaultRuntime"),
                    "name": info.get("Name"),
                },
            }

        return await asyncio.to_thread(_env)
