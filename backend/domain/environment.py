"""The environment a capture or traffic run happened in (pure).

Every run records where and on what it ran — host, Docker, kernel, Kathara and
its network plugin, the AE3GIS commit, each node's image, the tool image — so
results from different machines, code versions or optimisations can be
compared like for like. ``fingerprint`` hashes the parts that change results;
two runs with the same fingerprint ran on the same stack.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

SCHEMA = 1


def plan_sha256(links: list[dict[str, Any]], images: dict[str, str]) -> str:
    """Identity of the deployed lab: its links and each node's image."""
    body = json.dumps({"links": links, "images": images}, sort_keys=True, default=str)
    return hashlib.sha256(body.encode()).hexdigest()


def build_environment(
    *,
    engine: dict[str, Any],
    ae3gis: dict[str, Any],
    host: dict[str, Any],
    topology: dict[str, Any] | None = None,
    nodes: list[dict[str, Any]] | None = None,
    tool: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    env: dict[str, Any] = {
        "schema": SCHEMA,
        "captured_at": datetime.now(UTC).isoformat(),
        "host": host,
        "engine": engine,
        "ae3gis": ae3gis,
        "topology": topology or {},
        "nodes": sorted(nodes or [], key=lambda n: str(n.get("node_id"))),
        "tool": tool or {},
        **(extra or {}),
    }
    env["fingerprint"] = fingerprint(env)
    return env


def fingerprint(env: dict[str, Any]) -> str:
    """sha256 over what changes results (not timestamps, load or labels)."""
    docker = (env.get("engine") or {}).get("docker") or {}
    kathara = (env.get("engine") or {}).get("kathara") or {}
    plugin = kathara.get("network_plugin") or {}
    stable = {
        "docker": {
            k: docker.get(k)
            for k in (
                "server_version",
                "kernel",
                "os",
                "arch",
                "ncpu",
                "mem_total",
                "cgroup_version",
            )
        },
        "kathara": {
            "version": kathara.get("version"),
            "plugin": plugin.get("name"),
            "plugin_id": plugin.get("id"),
        },
        "commit": (env.get("ae3gis") or {}).get("git_commit"),
        "nodes": [
            [
                n.get("node_id"),
                n.get("image_id"),
                n.get("nano_cpus"),
                n.get("mem_limit"),
                n.get("cpuset"),
            ]
            for n in env.get("nodes") or []
        ],
        "tool": (env.get("tool") or {}).get("image_id"),
        "plan": (env.get("topology") or {}).get("plan_sha256"),
    }
    return hashlib.sha256(json.dumps(stable, sort_keys=True, default=str).encode()).hexdigest()
