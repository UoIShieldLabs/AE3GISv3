"""Turn an engine-agnostic LabPlan into a Kathara Lab object.

Kept import-light: the Kathara library is imported lazily so the backend (and
its unit tests) import without Kathara installed.

Not supported by this engine (reported by validation as warnings): per-node
``persistencePaths`` and ``config``; Kathara machines have no bind mounts here.
"""

from __future__ import annotations

from domain.plan import LabPlan

# The startup commands are written to this guest path and executed at boot;
# their output goes to _INIT_LOG (Kathara otherwise discards it).
_INIT_PATH = "/ae3gis-init.sh"
_INIT_LOG = "/var/log/ae3gis-init.log"


def build_lab(plan: LabPlan):
    """Return (kathara_lab, node_id -> machine_name map)."""
    from Kathara.model.Lab import Lab  # lazy: only needed on the deploy host

    lab = Lab(plan.name)
    name_map: dict[str, str] = {}

    for node in plan.nodes:
        mname = node.machine_name
        name_map[node.id] = mname
        machine = lab.new_machine(mname, image=node.image)

        for iface in node.interfaces:
            lab.connect_machine_to_link(
                mname, iface.collision_domain, machine_iface_number=iface.index
            )

        if node.startup:
            # One script (rather than one exec meta per command) keeps the
            # commands ordered and lets us capture their output in one place.
            script = "#!/bin/sh\n" + "\n".join(node.startup) + "\n"
            machine.create_file_from_string(script, _INIT_PATH)
            machine.add_meta("exec", f"sh {_INIT_PATH} > {_INIT_LOG} 2>&1")

    return lab, name_map
