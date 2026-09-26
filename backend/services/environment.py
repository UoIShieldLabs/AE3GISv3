"""Snapshot the environment of a capture or traffic run (see domain/environment)."""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import API_VERSION, BASE_DIR, Settings
from db.models import Topology
from domain.environment import build_environment, plan_sha256
from domain.images import LABEL_FINGERPRINT
from engine.base import DeploymentEngine, EngineState


def _host(settings: Settings) -> dict[str, Any]:
    """What the backend can see of its host (on Docker Desktop: the Linux VM)."""
    out: dict[str, Any] = {"label": settings.host_label or None}
    try:
        out["loadavg"] = [round(x, 2) for x in os.getloadavg()]
    except OSError:  # pragma: no cover - platform dependent
        out["loadavg"] = None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                out["mem_available"] = int(line.split()[1]) * 1024
    except OSError:
        pass
    return out


@lru_cache(maxsize=1)
def _local_git() -> tuple[str | None, bool]:
    """The checkout's commit when running from a git clone (not in Docker)."""
    root = BASE_DIR.parent
    if not (root / ".git").exists():
        return None, False
    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None, False
    return commit or None, bool(dirty)


def ae3gis_info(settings: Settings) -> dict[str, Any]:
    commit, dirty = (settings.git_commit, settings.git_dirty)
    if not commit:
        commit, dirty = _local_git()
    return {
        "api_version": API_VERSION,
        "git_commit": commit or None,
        "git_dirty": dirty,
        "mode": settings.mode or None,
        "instance_id": settings.instance_id or None,
    }


async def system_environment(engine: DeploymentEngine, settings: Settings) -> dict[str, Any]:
    """The host and engine alone (no topology)."""
    return build_environment(
        engine=await engine.environment(), ae3gis=ae3gis_info(settings), host=_host(settings)
    )


async def snapshot(
    engine: DeploymentEngine,
    settings: Settings,
    topo: Topology,
    state: EngineState,
    *,
    tool_ref: str | None = None,
    tool_versions: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Everything about where a run on ``topo`` happens, fingerprinted."""
    nodes = [n.to_dict() for n in await engine.node_runtime_info(state)]
    tool: dict[str, Any] = {}
    if tool_ref:
        info = (await engine.inspect_images([tool_ref])).get(tool_ref)
        tool = {
            "ref": tool_ref,
            "image_id": info.id if info else None,
            "fingerprint": (info.labels or {}).get(LABEL_FINGERPRINT) if info else None,
            "versions": tool_versions or {},
        }
    topology = {
        "id": topo.id,
        "name": topo.name,
        "version": topo.version,
        "deployed_version": state.deployed_version,
        "lab_hash": state.lab_hash,
        "plan_sha256": plan_sha256(state.links, {n["node_id"]: n["image_ref"] for n in nodes}),
    }
    return build_environment(
        engine=await engine.environment(),
        ae3gis=ae3gis_info(settings),
        host=_host(settings),
        topology=topology,
        nodes=nodes,
        tool=tool,
        extra=extra,
    )
