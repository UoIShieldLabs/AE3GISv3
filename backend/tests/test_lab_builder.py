"""The Kathara lab object built from a plan (needs the Kathara library)."""

import pytest

from domain.plan import build_lab_plan
from tests.conftest import TWO_SUBNETS

pytest.importorskip("Kathara")

from engine.kathara.lab_builder import build_lab  # noqa: E402


def test_machines_get_image_env_shell_and_a_startup_file():
    plan = build_lab_plan(TWO_SUBNETS, "ae3gis_demo")
    plan.nodes[0].env = {"POSTGRES_PASSWORD": "pass"}
    plan.nodes[1].shell = "/bin/sh"  # an image without bash
    lab, names = build_lab(plan)
    first = lab.machines[names[plan.nodes[0].id]]
    assert first.get_image() == plan.nodes[0].image
    assert first.get_envs() == {"POSTGRES_PASSWORD": "pass"}
    assert "shell" not in first.meta  # Kathara's default, bash
    assert lab.machines[names[plan.nodes[1].id]].meta["shell"] == "/bin/sh"
    for name, machine in lab.machines.items():
        # boot runs from a .startup file: no exec meta, whose `&>>` logging
        # BusyBox ash rejects
        assert not machine.meta["exec_commands"]
        assert lab.fs.readtext(f"{name}.startup") == (
            "sh /ae3gis-init.sh > /var/log/ae3gis-init.log 2>&1\n"
        )
        assert machine.fs.readtext("ae3gis-init.sh").startswith("#!/bin/sh\n")
        assert machine.pack_data()  # both files reach the container's /hostlab


def test_kathara_checks_images_locally_only():
    from types import SimpleNamespace

    from engine.kathara.engine import _local_image_checks

    calls = []

    class Images:
        __slots__ = ("client",)  # like Kathara's DockerImage: no new attributes

        def _check_and_pull(self, ref, pull=True):
            calls.append((ref, pull))

        def check_from_list(self, refs):  # Kathara's: a registry lookup per image
            raise AssertionError("looked up the registry")

    images = Images()
    manager = SimpleNamespace(manager=SimpleNamespace(docker_image=images))
    _local_image_checks(manager)
    _local_image_checks(manager)  # idempotent
    images.check_from_list(["ae3gis.local/suricata", "kathara/base"])
    assert calls == [("ae3gis.local/suricata", False), ("kathara/base", False)]
    _local_image_checks(SimpleNamespace())  # another shape: left alone
