"""Turn an engine-agnostic LabPlan into a Kathara Lab object.

Kept import-light: the Kathara library is imported lazily so the backend (and
its unit tests) import without Kathara installed. Only the deployment host/
container needs Kathara present.
"""
from __future__ import annotations

from engine.networking import LabPlan
from engine.kathara.naming import machine_name

# The startup commands are written to this guest path and executed at boot.
_INIT_PATH = "/ae3gis-init.sh"


def build_lab(plan: LabPlan):
    """Return (kathara_lab, node_id -> machine_name map)."""
    from Kathara.model.Lab import Lab  # lazy: only needed on the deploy host

    lab = Lab(plan.name)
    name_map: dict[str, str] = {}

    for node in plan.nodes:
        mname = machine_name(node.id)
        name_map[node.id] = mname
        machine = lab.new_machine(mname, image=node.image)

        for iface in node.interfaces:
            # eth<index> attaches to the collision domain (a Kathara link).
            lab.connect_machine_to_link(mname, iface.collision_domain, machine_iface_number=iface.index)

        if node.startup:
            # add_meta('exec', ...) overwrites, so run everything from one script
            # to guarantee ordered execution regardless of exec-meta semantics.
            script = "#!/bin/sh\n" + "\n".join(node.startup) + "\n"
            machine.create_file_from_string(script, _INIT_PATH)
            machine.add_meta("exec", f"sh {_INIT_PATH}")

    return lab, name_map
