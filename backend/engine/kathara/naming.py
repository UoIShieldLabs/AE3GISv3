"""Deterministic names for Kathara labs and machines.

Because the mapping is deterministic, status/exec/destroy can be handled
statelessly by rebuilding the lab plan from the stored topology.
"""

from __future__ import annotations

import re


def lab_name(topology_id: str, topology_data: dict | None = None) -> str:
    base = ((topology_data or {}).get("name") or "ae3gis").strip() or "ae3gis"
    base = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_").lower() or "ae3gis"
    return f"{base}_{topology_id[:8]}"


def machine_name(node_id: str) -> str:
    """Sanitize a node id into a valid Kathara machine name (alnum + underscore)."""
    name = re.sub(r"[^a-z0-9_]+", "_", (node_id or "").lower()).strip("_")
    return name or "node"
