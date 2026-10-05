"""KatharaEngine — realises LabPlans via the Kathara Python API.

Deploy/undeploy go through Kathara. Everything that *observes* a lab (status,
container lookup, listing, purge) goes to the Docker daemon directly by the
labels Kathara stamps on its containers (``app=kathara``, ``lab_hash``,
``name``, ``user``). That makes lookups independent of Kathara's per-user
prefix, which is derived from the backend's hostname and therefore changes
whenever the backend container is recreated — the cause of "device not found"
and orphaned labs before this design.

Lookups use Docker's container *summaries* (one API call for any number of
containers); ``containers.list()`` would inspect each container, which at a
few hundred nodes makes every status poll slow and loads the daemon being
measured. Full inspects happen only where needed, in parallel.

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
    ContainerRef,
    EngineState,
    HelperSpec,
    ImageInfo,
    LabRef,
    NodeInterface,
    NodeLog,
    NodeRuntimeInfo,
    NodeStatus,
    Progress,
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


def _labels(summary: dict[str, Any]) -> dict[str, str]:
    return summary.get("Labels") or {}


def _name(summary: dict[str, Any]) -> str:
    return ((summary.get("Names") or [""])[0] or "").lstrip("/")


def _map_state(raw: str) -> str:
    raw = (raw or "").lower()
    if raw == "running":
        return "running"
    if raw == "paused":
        return "paused"
    return "stopped"


def _local_image_checks(manager: Any) -> None:
    """Make Kathara check a lab's images locally only.

    Before a deploy Kathara asks each image's registry for a newer version.
    AE3GIS has already made sure every image is present (the deploy's
    ``images`` step), and a locally built ``ae3gis.local/…`` ref has no
    registry: on Docker's containerd image store, where such images carry a
    digest, each lookup fails only after ~15 s, per image, per deploy.
    ``_check_and_pull(ref, pull=False)`` keeps Kathara's presence and
    architecture checks without the lookup. Kathara's ``DockerImage`` has
    ``__slots__``, so the instance moves to a subclass instead of taking an
    attribute. Left alone if Kathara's internals change shape.
    """
    images = getattr(getattr(manager, "manager", None), "docker_image", None)
    if images is None or not hasattr(images, "_check_and_pull"):
        return
    base = type(images)
    if getattr(base, "_ae3gis_local_checks", False):
        return

    class LocalChecks(base):  # type: ignore[misc, valid-type]
        __slots__ = ()
        _ae3gis_local_checks = True

        def check_from_list(self, refs: Any) -> None:
            for ref in refs:
                self._check_and_pull(ref, pull=False)

    with contextlib.suppress(TypeError):
        images.__class__ = LocalChecks


class KatharaEngine:
    name = "kathara"

    # ── clients ──
    def _manager(self):
        from Kathara.manager.Kathara import Kathara  # lazy import

        manager = Kathara.get_instance()
        _local_image_checks(manager)
        return manager

    def _docker(self):
        import docker  # lazy import

        return docker.from_env()

    @staticmethod
    def _hash(state: EngineState) -> str:
        return state.lab_hash or hash_for_name(state.lab_name)

    def _summaries(self, labels: list[str] | None = None) -> list[dict[str, Any]]:
        """Container summaries (Id, Names, State, Labels…) in one API call."""
        filters = {"label": labels} if labels else None
        return self._docker().api.containers(all=True, filters=filters)

    def _lab_summaries(self, lab_hash: str) -> list[dict[str, Any]]:
        return self._summaries([_KATHARA_LABEL, f"lab_hash={lab_hash}"])

    def _containers(self, lab_hash: str) -> list[Any]:
        """Full container objects of a lab, inspected in parallel."""
        client = self._docker()
        ids = [c["Id"] for c in self._lab_summaries(lab_hash)]
        if not ids:
            return []

        def get(cid: str) -> Any:
            with contextlib.suppress(Exception):
                return client.containers.get(cid)
            return None

        with ThreadPoolExecutor(max_workers=min(16, len(ids))) as pool:
            return [c for c in pool.map(get, ids) if c is not None]

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
            by_machine = {_labels(c).get("name", ""): c for c in self._lab_summaries(lab_hash)}
            out: list[NodeStatus] = []
            for node_id, mname in state.nodes.items():
                c = by_machine.get(mname)
                out.append(
                    NodeStatus(
                        node_id=node_id,
                        name=mname,
                        state=_map_state(c.get("State", "")) if c else "stopped",
                    )
                )
            return out

        return await asyncio.to_thread(_status)

    async def resolve_container(self, state: EngineState, node_id: str) -> str:
        lab_hash = self._hash(state)
        mname = state.nodes.get(node_id) or machine_name(node_id)

        def _resolve() -> str:
            for c in self._lab_summaries(lab_hash):
                if _labels(c).get("name") == mname:
                    return _name(c)
            raise LookupError(f"Device '{mname}' is not running in this lab")

        return await asyncio.to_thread(_resolve)

    async def node_logs(self, state: EngineState, tail: int = 30) -> list[NodeLog]:
        lab_hash = self._hash(state)
        node_for = {m: nid for nid, m in state.nodes.items()}

        def _logs() -> list[NodeLog]:
            out: list[NodeLog] = []
            client = self._docker()
            for summary in self._lab_summaries(lab_hash):
                # "created" containers never ran (a deploy that stopped early);
                # only exited ones have something to say.
                if summary.get("State") not in ("exited", "dead"):
                    continue
                try:
                    c = client.containers.get(summary["Id"])
                except Exception:  # pragma: no cover - removed meanwhile
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
            for c in self._summaries([_KATHARA_LABEL]):
                labels = _labels(c)
                h = labels.get("lab_hash", "")
                g = groups.setdefault(
                    h, {"user": labels.get("user", ""), "machines": [], "running": 0}
                )
                g["machines"].append(labels.get("name", _name(c)))
                if c.get("State") == "running":
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
        for c in self._lab_summaries(lab_hash):
            with contextlib.suppress(Exception):
                client.api.remove_container(c["Id"], force=True)
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
        for c in self._lab_summaries(self._hash(state)):
            if _labels(c).get("name") == mname:
                return self._docker().containers.get(c["Id"])
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
                    name=_name(c),
                    node_id=_labels(c).get(LABEL_NODE, ""),
                    job_id=_labels(c).get(LABEL_JOB, ""),
                    purpose=_labels(c).get(LABEL_PURPOSE, ""),
                    lab_hash=_labels(c).get(LABEL_LAB, ""),
                    owner=_labels(c).get(LABEL_OWNER, ""),
                    status=c.get("State", ""),
                )
                for c in self._summaries(flt)
            ]

        return await asyncio.to_thread(_list)

    def _remove_sidecars_sync(self, labels: list[str]) -> int:
        removed = 0
        client = self._docker()
        for c in self._summaries(labels):
            with contextlib.suppress(Exception):
                client.api.remove_container(c["Id"], force=True)
                removed += 1
        return removed

    async def remove_sidecars(
        self, *, lab_hash: str | None = None, job_id: str | None = None, owner: str | None = None
    ) -> int:
        if not (lab_hash or job_id or owner):
            raise ValueError("remove_sidecars needs a filter")
        flt = sidecar_filters(lab_hash=lab_hash, job_id=job_id, owner=owner)
        return await asyncio.to_thread(self._remove_sidecars_sync, flt)

    # ── helpers ──
    async def start_helper(self, spec: HelperSpec) -> DockerSidecar:
        return await asyncio.to_thread(DockerSidecar.start_helper, self._docker(), spec)

    async def node_pids(self, state: EngineState) -> dict[str, int]:
        lab_hash = self._hash(state)
        node_for = {m: nid for nid, m in state.nodes.items()}

        def _pids() -> dict[str, int]:
            api = self._docker().api
            running = [
                (node_for[_labels(c).get("name", "")], c["Id"])
                for c in self._lab_summaries(lab_hash)
                if c.get("State") == "running" and _labels(c).get("name", "") in node_for
            ]
            if not running:
                return {}

            def pid(item: tuple[str, str]) -> tuple[str, int]:
                try:
                    return item[0], int(api.inspect_container(item[1])["State"]["Pid"] or 0)
                except Exception:
                    return item[0], 0

            with ThreadPoolExecutor(max_workers=min(16, len(running))) as pool:
                return {nid: p for nid, p in pool.map(pid, running) if p > 0}

        return await asyncio.to_thread(_pids)

    async def list_containers(self) -> list[ContainerRef]:
        def _list() -> list[ContainerRef]:
            return [
                ContainerRef(
                    id=c["Id"], name=_name(c), status=c.get("State", ""), labels=_labels(c)
                )
                for c in self._summaries()
            ]

        return await asyncio.to_thread(_list)

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
