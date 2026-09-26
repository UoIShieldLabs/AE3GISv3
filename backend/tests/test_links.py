"""Connection ids in the plan, and capture-target resolution (domain/links.py)."""

import copy

import pytest

from domain.links import TargetError, endpoints_for_connection, interfaces_by_node, resolve_target
from domain.plan import build_lab_plan
from tests.conftest import TWO_SUBNETS


def _links(data=TWO_SUBNETS):
    return build_lab_plan(data, "lab").links()


def test_links_carry_connection_ids_kinds_and_ends():
    by_conn = {link["connection_id"]: link for link in _links()}
    assert set(by_conn) == {"c1", "c2", "c3", "c4", "c5"}
    assert by_conn["c2"]["kind"] == "container"
    assert (by_conn["c2"]["from"], by_conn["c2"]["to"]) == ("swA", "hA")
    # A subnet-to-subnet link lands on the two gateway routers.
    wan = by_conn["c5"]
    assert wan["kind"] == "subnet" and (wan["from"], wan["to"]) == ("rA", "rB")
    assert {e["node"] for e in wan["endpoints"]} == {"rA", "rB"}


def test_interfaces_know_their_connection():
    plan = build_lab_plan(TWO_SUBNETS, "lab")
    hA = next(n for n in plan.nodes if n.id == "hA")
    assert [(i.name, i.connection_id) for i in hA.interfaces] == [("eth0", "c2")]


def test_connections_without_ids_map_to_none():
    data = copy.deepcopy(TWO_SUBNETS)
    for sub in data["sites"][0]["subnets"]:
        for conn in sub["connections"]:
            del conn["id"]
    ids = {link["connection_id"] for link in _links(data)}
    assert ids == {None, "c5"}


def test_resolve_a_link_defaults_to_its_from_end():
    links = _links()
    ep = resolve_target(links, {"kind": "link", "connection_id": "c2"})
    assert (ep.node_id, ep.interface, ep.peer_node_id) == ("swA", "eth1", "hA")
    ep = resolve_target(links, {"kind": "link", "connection_id": "c2", "endpoint": "to"})
    assert (ep.node_id, ep.interface, ep.peer_node_id, ep.ip) == ("hA", "eth0", "swA", "10.0.1.5")
    wan = endpoints_for_connection(links, "c5")
    assert [e.node_id for e in wan] == ["rA", "rB"]
    assert wan[0].collision_domain == wan[1].collision_domain


def test_resolve_an_interface():
    links = _links()
    ep = resolve_target(links, {"kind": "interface", "node_id": "rA", "interface": "eth1"})
    assert ep.connection_id == "c5" and ep.peer_node_id == "rB"
    assert [e.interface for e in interfaces_by_node(links)["swA"]] == ["eth0", "eth1"]


@pytest.mark.parametrize(
    ("target", "code"),
    [
        ({"kind": "link", "connection_id": "nope"}, "link_not_deployed"),
        ({"kind": "interface", "node_id": "hA", "interface": "eth7"}, "interface_not_deployed"),
        ({"kind": "wat"}, "bad_target"),
    ],
)
def test_unknown_targets_are_refused(target, code):
    with pytest.raises(TargetError) as exc:
        resolve_target(_links(), target)
    assert exc.value.code == code
