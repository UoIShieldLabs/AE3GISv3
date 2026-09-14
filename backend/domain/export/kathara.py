"""Render a LabPlan as a Kathara lab folder (lab.conf + <machine>.startup).

The output runs with plain ``kathara lstart`` from the extracted folder. It is
intentionally independent of the Kathara Python API so it can be produced
anywhere (tests included).
"""

from __future__ import annotations

import io
import zipfile

from domain.plan import LabPlan, NodePlan


def render_lab_conf(plan: LabPlan, *, description: str | None = None) -> str:
    lines = [
        f'LAB_DESCRIPTION="{(description or plan.name).replace(chr(34), "")}"',
        'LAB_VERSION="1"',
        "",
    ]
    for node in plan.nodes:
        m = node.machine_name
        for iface in sorted(node.interfaces, key=lambda i: i.index):
            lines.append(f'{m}[{iface.index}]="{iface.collision_domain}"')
        lines.append(f'{m}[image]="{node.image}"')
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_startup(node: NodePlan) -> str:
    return "\n".join(node.startup) + ("\n" if node.startup else "")


README = """AE3GIS Kathara lab export
=========================

Run from this folder with Kathara installed:

    kathara lstart

lab.conf declares every machine, its image, and which collision domain each
interface attaches to; <machine>.startup holds the boot commands (IP addresses,
routes, bridges). Stop with `kathara lclean`.
"""


def build_zip(plan: LabPlan, *, description: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lab.conf", render_lab_conf(plan, description=description))
        for node in plan.nodes:
            if node.startup:
                zf.writestr(f"{node.machine_name}.startup", render_startup(node))
        zf.writestr("README.txt", README)
    return buf.getvalue()
