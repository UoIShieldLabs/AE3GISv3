"""The engine-agnostic "lab spec": a versioned JSON document describing exactly
what would be instantiated (nodes, images, interfaces, links, boot commands).

It is the portable representation of a topology as a deployable lab; the
Kathara and ContainerLab renderers are projections of the same LabPlan.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from domain.plan import LabPlan

LABSPEC_VERSION = 1


def to_labspec(
    plan: LabPlan, *, topology_id: str, topology_name: str, generated_at: datetime | None = None
) -> dict[str, Any]:
    ts = (generated_at or datetime.now(UTC)).isoformat()
    return {
        "labspec_version": LABSPEC_VERSION,
        "generated_at": ts,
        "generator": "ae3gis",
        "topology": {"id": topology_id, "name": topology_name},
        "lab": plan.name,
        "images": plan.images(),
        "nodes": [n.to_dict() for n in plan.nodes],
        "links": plan.links(),
    }
