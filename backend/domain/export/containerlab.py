"""Render a LabPlan as a ContainerLab topology (topo.clab.yml).

Build the plan with ``iface_base=1``: ContainerLab reserves eth0 for its
management network, so data interfaces start at eth1 and the startup commands
must already refer to the shifted names.
"""

from __future__ import annotations

import io
import zipfile
from typing import Any

import yaml

from domain.plan import LabPlan


def render_clab_yaml(plan: LabPlan, *, name: str | None = None) -> str:
    nodes: dict[str, Any] = {}
    for node in plan.nodes:
        entry: dict[str, Any] = {"kind": "linux", "image": node.image}
        if node.startup:
            entry["exec"] = list(node.startup)
        nodes[node.machine_name] = entry

    links: list[dict[str, Any]] = []
    for link in plan.links():
        eps = link["endpoints"]
        if len(eps) != 2:
            # The plan only emits point-to-point collision domains; anything
            # else would need a bridge node in clab, so it is reported, not silently dropped.
            links.append(
                {
                    "endpoints": [f"{e['machine_name']}:{e['interface']}" for e in eps],
                    "comment": "multi-endpoint domain; clab needs a bridge here",
                }
            )
            continue
        links.append(
            {
                "endpoints": [
                    f"{eps[0]['machine_name']}:{eps[0]['interface']}",
                    f"{eps[1]['machine_name']}:{eps[1]['interface']}",
                ]
            }
        )

    doc = {"name": name or plan.name, "topology": {"nodes": nodes, "links": links}}
    return yaml.safe_dump(doc, sort_keys=False, default_flow_style=False)


README = """AE3GIS ContainerLab export
==========================

Deploy with ContainerLab installed:

    containerlab deploy -t topo.clab.yml

Every node is a plain `linux` kind running the same image AE3GIS would use;
`exec` lists the boot commands. Interfaces start at eth1 because ContainerLab
keeps eth0 for its management network. Tear down with `containerlab destroy`.
"""


def build_zip(plan: LabPlan, *, name: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("topo.clab.yml", render_clab_yaml(plan, name=name))
        zf.writestr("README.txt", README)
    return buf.getvalue()
