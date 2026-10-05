"""Turn an engine-agnostic LabPlan into a Kathara Lab object.

Kept import-light: the Kathara library is imported lazily so the backend (and
its unit tests) import without Kathara installed.

Not supported by this engine (reported by validation as warnings): per-node
``persistencePaths`` and ``config``; Kathara machines have no bind mounts here.
"""

from __future__ import annotations

from domain.plan import LabPlan

# The startup commands are written to this guest path and run at boot by the
# machine's Kathara ``.startup`` file; their output goes to _INIT_LOG.
_INIT_PATH = "/ae3gis-init.sh"
_INIT_LOG = "/var/log/ae3gis-init.log"
# Kathara runs a machine's boot line through its shell: /bin/bash, or the
# image's catalog ``shell`` where it has no bash (Alpine: /bin/sh, BusyBox ash).
# The init runs from a ``.startup`` file, not an ``exec`` meta: Kathara logs
# exec metas with ``&>>``, a syntax error for ash. Its ``&>`` redirect is fine
# for bash and ash; dash (Debian's sh) would read it as "run in background",
# orphaning the init to the container's PID 1, which some daemons do not
# survive (vsftpd segfaults reaping a child it did not fork), so a
# bash-equipped image keeps bash.


def build_lab(plan: LabPlan):
    """Return (kathara_lab, node_id -> machine_name map)."""
    from Kathara.model.Lab import Lab  # lazy: only needed on the deploy host

    lab = Lab(plan.name)
    name_map: dict[str, str] = {}

    for node in plan.nodes:
        mname = node.machine_name
        name_map[node.id] = mname
        machine = lab.new_machine(mname, image=node.image)
        if node.shell:
            machine.add_meta("shell", node.shell)
        for key, value in node.env.items():
            machine.add_meta("env", f"{key}={value}")

        for iface in node.interfaces:
            lab.connect_machine_to_link(
                mname, iface.collision_domain, machine_iface_number=iface.index
            )

        if node.startup:
            # One script keeps the commands ordered and their output in one place.
            script = "#!/bin/sh\n" + "\n".join(node.startup) + "\n"
            machine.create_file_from_string(script, _INIT_PATH)
            lab.create_file_from_string(f"sh {_INIT_PATH} > {_INIT_LOG} 2>&1\n", f"{mname}.startup")

    return lab, name_map
