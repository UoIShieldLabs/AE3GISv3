"""domain.topology_edit: the agent's edit operations mirror the editor's store."""

from __future__ import annotations

import copy

import pytest

from domain import validation
from domain.plan import build_lab_plan
from domain.topology_edit import EditError, apply_ops
from tests.conftest import TWO_SUBNETS


def _site_with_two_subnets():
    return apply_ops(
        {},
        [
            {"op": "add_site", "name": "HQ"},
            {"op": "add_subnet", "site": "$0", "name": "IT", "cidr": "10.0.1.0/24"},
            {"op": "add_subnet", "site": "$0", "name": "OT", "cidr": "10.0.2.0/24"},
        ],
    )


def test_add_subnet_brings_its_router_and_switch_linked():
    r = _site_with_two_subnets()
    it = r.data["sites"][0]["subnets"][0]
    router, switch = it["containers"]
    assert (router["type"], router["ip"]) == ("router", "10.0.1.1")
    assert (switch["type"], switch["ip"]) == ("switch", "10.0.1.2")
    assert it["gateway"] == "10.0.1.1"
    assert it["connections"][0]["from"] == switch["id"]
    assert it["connections"][0]["to"] == router["id"]
    assert r.created[1]["router"] == router["id"] and r.created[1]["switch"] == switch["id"]


def test_add_device_takes_the_next_address_and_links_to_the_switch():
    r = _site_with_two_subnets()
    it = r.created[1]
    r2 = apply_ops(r.data, [{"op": "add_device", "subnet": it["id"], "type": "workstation"}])
    dev = r2.created[0]
    assert dev["ip"] == "10.0.1.3" and dev["name"] == "Workstation 1"
    conns = r2.data["sites"][0]["subnets"][0]["connections"]
    assert {"from": it["switch"], "to": dev["id"]} == {k: conns[-1][k] for k in ("from", "to")}
    r3 = apply_ops(
        r2.data,
        [{"op": "add_device", "subnet": it["id"], "type": "workstation", "connect_to": None}],
    )
    assert r3.created[0]["ip"] == "10.0.1.4" and r3.created[0]["name"] == "Workstation 2"
    assert len(r3.data["sites"][0]["subnets"][0]["connections"]) == len(conns)


def test_connecting_subnets_links_their_gateway_routers():
    r = _site_with_two_subnets()
    it, ot = r.created[1], r.created[2]
    r2 = apply_ops(r.data, [{"op": "connect", "a": it["id"], "b": ot["id"]}])
    link = r2.data["sites"][0]["subnetConnections"][0]
    assert (link["from"], link["to"]) == (it["id"], ot["id"])
    assert (link["fromContainer"], link["toContainer"]) == (it["router"], ot["router"])
    with pytest.raises(EditError, match="already connected"):
        apply_ops(r2.data, [{"op": "connect", "a": ot["id"], "b": it["id"]}])


def test_connecting_hosts_across_subnets_is_refused():
    r = _site_with_two_subnets()
    r2 = apply_ops(
        r.data,
        [
            {"op": "add_device", "subnet": r.created[1]["id"], "type": "workstation"},
            {"op": "add_device", "subnet": r.created[2]["id"], "type": "workstation"},
            {"op": "connect", "a": "$0", "b": "$1"},
        ][:2],
    )
    a, b = r2.created[0]["id"], r2.created[1]["id"]
    with pytest.raises(EditError, match="only routers"):
        apply_ops(r2.data, [{"op": "connect", "a": a, "b": b}])


def test_sites_connect_through_routers():
    r = apply_ops(
        {},
        [
            {"op": "add_site", "name": "A"},
            {"op": "add_subnet", "site": "$0", "cidr": "10.1.0.0/24"},
            {"op": "add_site", "name": "B"},
            {"op": "add_subnet", "site": "$2", "cidr": "10.2.0.0/24"},
            {"op": "connect", "a": "$0", "b": "$2"},
        ],
    )
    link = r.data["siteConnections"][0]
    assert link["fromContainer"] == r.created[1]["router"]
    assert link["toContainer"] == r.created[3]["router"]


def test_a_built_topology_validates_and_plans():
    r = _site_with_two_subnets()
    it, ot = r.created[1], r.created[2]
    r2 = apply_ops(
        r.data,
        [
            {"op": "add_device", "subnet": it["id"], "type": "workstation"},
            {"op": "add_device", "subnet": ot["id"], "type": "plc"},
            {"op": "connect", "a": it["id"], "b": ot["id"]},
        ],
    )
    assert [d for d in validation.validate(r2.data) if d.severity == "error"] == []
    plan = build_lab_plan(r2.data, "lab").to_dict()
    assert len(plan["nodes"]) == 6


def test_remove_cascades_like_the_editor():
    r = _site_with_two_subnets()
    it, ot = r.created[1], r.created[2]
    r2 = apply_ops(
        r.data,
        [
            {"op": "connect", "a": it["id"], "b": ot["id"]},
            {"op": "add_device", "subnet": it["id"], "type": "workstation"},
            {"op": "add_interface", "device": "$1", "subnet": ot["id"]},
            {"op": "add_scenario", "name": "S"},
            {"op": "add_phase", "scenario": "$3"},
            {"op": "add_step", "phase": "$4", "device": "$1", "script": "ping -c1 10.0.2.1"},
        ],
    )
    host = r2.created[1]["id"]
    r3 = apply_ops(r2.data, [{"op": "remove", "ids": [ot["id"]]}])
    site = r3.data["sites"][0]
    assert [s["id"] for s in site["subnets"]] == [it["id"]]
    assert site["subnetConnections"] == []
    dev = next(c for c in site["subnets"][0]["containers"] if c["id"] == host)
    assert "interfaces" not in dev  # its leg into the removed subnet went too
    r4 = apply_ops(r3.data, [{"op": "remove", "ids": [host]}])
    assert r4.data["scenarios"][0]["phases"][0]["executions"] == []


def test_all_or_nothing_and_the_input_is_never_touched():
    data = copy.deepcopy(TWO_SUBNETS)
    before = copy.deepcopy(data)
    with pytest.raises(EditError) as exc:
        apply_ops(
            data,
            [
                {"op": "add_device", "subnet": "subA", "type": "workstation"},
                {"op": "add_device", "subnet": "nope", "type": "workstation"},
            ],
        )
    assert exc.value.index == 1 and "no subnet" in str(exc.value)
    assert data == before


def test_bad_operations_say_what_is_wrong():
    with pytest.raises(EditError, match="unknown operation"):
        apply_ops(TWO_SUBNETS, [{"op": "explode"}])
    with pytest.raises(EditError, match="unknown device type"):
        apply_ops(TWO_SUBNETS, [{"op": "add_device", "subnet": "subA", "type": "toaster"}])
    with pytest.raises(EditError, match="already used"):
        apply_ops(
            TWO_SUBNETS,
            [{"op": "add_device", "subnet": "subA", "type": "workstation", "ip": "10.0.1.5"}],
        )
    with pytest.raises(EditError, match="switch cannot take"):
        apply_ops(TWO_SUBNETS, [{"op": "add_interface", "device": "swA", "subnet": "subB"}])
    with pytest.raises(EditError, match="cannot set"):
        apply_ops(TWO_SUBNETS, [{"op": "update", "id": "subA", "set": {"containers": []}}])
    with pytest.raises(EditError, match="refers to operation"):
        apply_ops(TWO_SUBNETS, [{"op": "connect", "a": "$3", "b": "hA"}])


def test_update_sets_and_unsets_fields():
    r = apply_ops(
        TWO_SUBNETS,
        [
            {
                "op": "update",
                "id": "hA",
                "set": {"name": "Eng WS", "env": {"X": "1"}},
                "unset": ["ip"],
            }
        ],
    )
    host = r.data["sites"][0]["subnets"][0]["containers"][2]
    assert host["name"] == "Eng WS" and host["env"] == {"X": "1"} and "ip" not in host


def test_tutorial_operations():
    r = apply_ops(
        TWO_SUBNETS,
        [
            {"op": "add_tutorial", "title": "Ping"},
            {"op": "add_cell", "tutorial": "$0", "kind": "markdown", "source": "# Hello"},
            {
                "op": "add_cell",
                "tutorial": "$0",
                "kind": "command",
                "device": "hA",
                "command": "ping -c1 10.0.2.5",
            },
            {
                "op": "add_cell",
                "tutorial": "$0",
                "kind": "markdown",
                "source": "between",
                "after": "$1",
            },
            {
                "op": "set_tutorial_setup",
                "tutorial": "$0",
                "steps": [{"device": "hB", "command": "true"}],
            },
        ],
    )
    tut = r.data["tutorials"][0]
    assert [c["kind"] for c in tut["cells"]] == ["markdown", "markdown", "command"]
    assert tut["cells"][1]["source"] == "between"
    assert tut["cells"][2]["containerId"] == "hA"
    assert tut["setup"]["steps"][0]["containerId"] == "hB"
