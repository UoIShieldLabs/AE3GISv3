"""Saved lab state: what "save & destroy" keeps and how a deploy resumes it.

Saving commits each node's container (its whole filesystem: edited configs,
files, installed packages) to a local image under ``ae3gis.local/snapshot/``;
the next deploy runs that image in place of the catalog one. Live state is not
saved — processes, shells, and the kernel's network state. Addressing and
routes come back from the plan's startup commands as usual; ``iptables`` rules
are dumped to a file before the commit (``PREPARE_SCRIPT``) and restored at
boot (``RESTORE_COMMAND``).

The record stored in ``Topology.saved_state``::

    {"created_at": iso, "deployed_version": int | None,
     "nodes": {node_id: {"ref": image ref, "base_image": catalog image}}}

A node resumes only while it still exists and still resolves to the same base
image; otherwise it starts fresh from its catalog image.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from domain.plan import LabPlan

REPO_PREFIX = "ae3gis.local/snapshot/"
RULES_PATH = "/etc/ae3gis/iptables.rules"

# Run in each node (``sh -c``) right before its commit. Best effort throughout:
# images without iptables just skip it. Pid files go so daemons that refuse to
# start over a stale one (Apache, FRR, rsyslog) come back up on resume; the
# running daemons are about to be destroyed anyway.
PREPARE_SCRIPT = (
    f"mkdir -p {RULES_PATH.rsplit('/', 1)[0]} 2>/dev/null; "
    "if command -v iptables-save >/dev/null 2>&1; then "
    f"iptables-save > {RULES_PATH} 2>/dev/null || rm -f {RULES_PATH}; fi; "
    "find /run /var/run /usr/local/apache2/logs -maxdepth 2 -name '*.pid' -type f "
    "-exec rm -f {} + 2>/dev/null; "
    "sync 2>/dev/null; true"
)

# Appended to a resumed node's startup, after its addressing.
RESTORE_COMMAND = (
    f"if [ -s {RULES_PATH} ] && command -v iptables-restore >/dev/null 2>&1; then "
    f"iptables-restore < {RULES_PATH} || true; fi"
)


def repository(topology_id: str) -> str:
    """The image repository a topology's snapshots are committed to."""
    return f"{REPO_PREFIX}{topology_id[:12].lower()}"


def tag_suffix(now: datetime) -> str:
    """Per-save tag suffix (a tag is ``<machine>-<suffix>``)."""
    return now.strftime("%Y%m%dt%H%M%S")


def make(
    refs: dict[str, str],
    base_images: dict[str, str],
    *,
    deployed_version: int | None,
    now: datetime,
) -> dict[str, Any]:
    return {
        "created_at": now.isoformat(),
        "deployed_version": deployed_version,
        "nodes": {
            nid: {"ref": ref, "base_image": base_images.get(nid)} for nid, ref in refs.items()
        },
    }


def _nodes(saved: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(saved, dict):
        return {}
    nodes = saved.get("nodes")
    if not isinstance(nodes, dict):
        return {}
    return {k: v for k, v in nodes.items() if isinstance(v, dict) and v.get("ref")}


def refs(saved: dict[str, Any] | None) -> list[str]:
    """Every image a saved state holds."""
    return sorted({str(n["ref"]) for n in _nodes(saved).values()})


def summary(saved: dict[str, Any] | None) -> dict[str, Any] | None:
    """What the API shows: when it was saved and how many nodes it holds."""
    nodes = _nodes(saved)
    if not nodes:
        return None
    return {"created_at": str(saved.get("created_at") or ""), "nodes": len(nodes)}


@dataclass
class Restore:
    """Which plan nodes resume from a snapshot, and why the others don't."""

    applied: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)  # node id -> reason


def apply(plan: LabPlan, saved: dict[str, Any] | None, present: dict[str, bool]) -> Restore:
    """Point the plan's nodes at their snapshot images (in place).

    ``present``: whether each snapshot ref exists locally. Catalog-derived
    settings (env, shell, own bridge) stay those of the base image, which the
    snapshot was committed from.
    """
    out = Restore()
    nodes = _nodes(saved)
    for node in plan.nodes:
        entry = nodes.get(node.id)
        if entry is None:
            continue
        ref = str(entry["ref"])
        base = entry.get("base_image")
        if base and base != node.image:
            out.skipped[node.id] = f"image changed ({base} → {node.image})"
            continue
        if not present.get(ref, False):
            out.skipped[node.id] = f"saved image {ref} is missing"
            continue
        node.image = ref
        node.startup.append(RESTORE_COMMAND)
        out.applied.append(node.id)
    return out
