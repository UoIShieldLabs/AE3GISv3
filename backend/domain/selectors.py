"""Choosing deployed nodes by id, type, subnet or role (pure).

A selector is ``"all"``, a list of node ids, or a dict::

    {"ids": [...], "types": ["workstation"], "subnets": ["sub-a"],
     "roles": ["host"], "exclude": [...]}

A dict starts from ``ids`` (or every deployed node) and keeps the nodes that
match every filter given; ``exclude`` removes nodes last. Only deployed nodes
are ever returned, in topology order.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import catalog


def node_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Node id → {name, type, role, ip, subnets} (a multi-homed node lists
    every subnet it is in)."""
    out: dict[str, dict[str, Any]] = {}
    for site in (data or {}).get("sites", []) or []:
        for subnet in site.get("subnets", []) or []:
            for c in subnet.get("containers", []) or []:
                cid = c.get("id")
                if not cid:
                    continue
                entry = out.setdefault(
                    cid,
                    {
                        "name": c.get("name") or cid,
                        "type": c.get("type", ""),
                        "role": catalog.role_for(c.get("type", "")),
                        "ip": (c.get("ip") or "").strip() or None,
                        "subnets": [],
                    },
                )
                entry["subnets"].append(subnet.get("id"))
    return out


def resolve(data: dict[str, Any], deployed: Iterable[str], selector: Any) -> list[str]:
    """The deployed node ids ``selector`` picks."""
    deployed_set = set(deployed)
    index = node_index(data)
    order = [nid for nid in index if nid in deployed_set]
    order += sorted(deployed_set - set(order))  # deployed but no longer in the data
    if selector in (None, "all"):
        return order
    if isinstance(selector, list):
        wanted = set(selector)
        return [n for n in order if n in wanted]
    if not isinstance(selector, dict):
        raise ValueError(f"Unknown node selector: {selector!r}")
    pool = order
    if selector.get("ids") is not None:
        wanted = set(selector["ids"])
        pool = [n for n in pool if n in wanted]
    for key, field in (("types", "type"), ("roles", "role")):
        if selector.get(key):
            allowed = set(selector[key])
            pool = [n for n in pool if (index.get(n) or {}).get(field) in allowed]
    if selector.get("subnets"):
        allowed = set(selector["subnets"])
        pool = [n for n in pool if allowed & set((index.get(n) or {}).get("subnets") or [])]
    if selector.get("exclude"):
        excluded = set(selector["exclude"])
        pool = [n for n in pool if n not in excluded]
    return pool
