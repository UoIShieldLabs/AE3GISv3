import copy

from domain.validation import has_errors, summarize, validate
from tests.conftest import TWO_SUBNETS


def codes(data):
    return {d.code for d in validate(data)}


def test_valid_topology_has_no_errors():
    diags = validate(TWO_SUBNETS)
    assert not has_errors(diags), [d.to_dict() for d in diags]


def test_non_object_is_an_error():
    assert codes([]) == {"topology.shape"}
    assert codes({"sites": "nope"}) == {"topology.shape"}


def test_ip_checks():
    t = copy.deepcopy(TWO_SUBNETS)
    cs = t["sites"][0]["subnets"][0]["containers"]
    cs[0]["ip"] = "not-an-ip"
    cs[1]["ip"] = "192.168.9.9"
    cs[2]["ip"] = "10.0.1.7"
    cs.append({"id": "dup", "name": "Dup", "type": "workstation", "ip": "10.0.1.7"})
    c = codes(t)
    assert {"ip.invalid", "ip.outside_subnet", "ip.duplicate"} <= c


def test_bad_cidr_and_gateway():
    t = copy.deepcopy(TWO_SUBNETS)
    t["sites"][0]["subnets"][0]["cidr"] = "10.0.1.0/33"
    t["sites"][0]["subnets"][1]["gateway"] = "10.0.2.99"
    c = codes(t)
    assert "cidr.invalid" in c and "gateway.not_router" in c


def test_connection_endpoints_and_missing_router():
    t = copy.deepcopy(TWO_SUBNETS)
    t["sites"][0]["subnets"][0]["connections"].append({"id": "x", "from": "swA", "to": "ghost"})
    t["sites"][0]["subnets"][1]["containers"] = [
        c for c in t["sites"][0]["subnets"][1]["containers"] if c["type"] != "router"
    ]
    t["sites"][0]["subnets"][1]["connections"] = [
        c for c in t["sites"][0]["subnets"][1]["connections"] if c["to"] != "rB"
    ]
    c = codes(t)
    assert "connection.endpoint_unknown" in c and "subnet.no_router" in c


def test_duplicate_ids_and_self_link():
    t = copy.deepcopy(TWO_SUBNETS)
    t["sites"][0]["subnets"][1]["id"] = "subA"
    t["sites"][0]["subnets"][0]["connections"].append({"id": "self", "from": "hA", "to": "hA"})
    c = codes(t)
    assert "id.duplicate" in c and "connection.self" in c


def test_warnings_do_not_block():
    t = copy.deepcopy(TWO_SUBNETS)
    cs = t["sites"][0]["subnets"][0]["containers"]
    cs[2]["type"] = "quantum-toaster"
    cs[2]["persistencePaths"] = ["/var/lib/x"]
    cs.append({"id": "lonely", "name": "Host A", "type": "workstation", "ip": "10.0.1.9"})
    diags = validate(t)
    assert not has_errors(diags)
    c = {d.code for d in diags}
    assert {"type.unknown", "field.unsupported", "device.unlinked", "name.duplicate"} <= c
    assert summarize(diags)["errors"] == 0


def test_paths_point_at_the_offending_field():
    t = copy.deepcopy(TWO_SUBNETS)
    t["sites"][0]["subnets"][0]["containers"][2]["ip"] = "bad"
    d = next(d for d in validate(t) if d.code == "ip.invalid")
    assert d.path == "sites[0].subnets[0].containers[2].ip" and d.node_id == "hA"


# ── Multi-homing: interface legs ──────────────────────────────────────────


def _with_leg(leg):
    t = copy.deepcopy(TWO_SUBNETS)
    # hA lives in subA (10.0.1.0/24); give it a leg.
    t["sites"][0]["subnets"][0]["containers"][2]["interfaces"] = [leg]
    return t


def test_valid_interface_leg_has_no_errors():
    t = _with_leg({"subnetId": "subB", "ip": "10.0.2.9"})
    diags = validate(t)
    assert not has_errors(diags), [d.to_dict() for d in diags]


def test_interface_leg_unknown_subnet():
    assert "interface.subnet_unknown" in codes(_with_leg({"subnetId": "nope", "ip": "10.0.2.9"}))


def test_interface_leg_ip_outside_target_subnet():
    assert "interface.ip_outside_subnet" in codes(_with_leg({"subnetId": "subB", "ip": "10.9.9.9"}))


def test_interface_leg_ip_duplicate_in_target_subnet():
    # 10.0.2.5 is hB's address in subB.
    assert "interface.ip_duplicate" in codes(_with_leg({"subnetId": "subB", "ip": "10.0.2.5"}))


def test_interface_leg_to_own_subnet():
    assert "interface.home_subnet" in codes(_with_leg({"subnetId": "subA", "ip": "10.0.1.9"}))


def test_interface_leg_missing_subnet():
    assert "interface.subnet_missing" in codes(_with_leg({"ip": "10.0.2.9"}))


def test_gateway_may_be_a_leg_attached_router():
    # rA (a router in subA) legs into subB and is declared subB's gateway.
    t = copy.deepcopy(TWO_SUBNETS)
    t["sites"][0]["subnets"][0]["containers"][0]["interfaces"] = [
        {"subnetId": "subB", "ip": "10.0.2.254"}
    ]
    t["sites"][0]["subnets"][1]["gateway"] = "10.0.2.254"
    c = codes(t)
    assert "gateway.not_router" not in c
    assert not has_errors(validate(t))


# ── Port mirroring (SPAN) ─────────────────────────────────────────────────


def _mirror_subnet(switch_image, mirror_to="ids"):
    t = copy.deepcopy(TWO_SUBNETS)
    sub = t["sites"][0]["subnets"][0]
    sub["containers"][1]["image"] = switch_image  # swA
    sub["containers"][1]["mirrorTo"] = mirror_to
    sub["containers"].append({"id": "ids", "name": "IDS", "type": "ids", "ip": "10.0.1.40"})
    sub["connections"].append({"id": "cids", "from": "swA", "to": "ids"})
    return t


def test_mirror_on_ovs_switch_is_clean():
    assert "mirror.unsupported_switch" not in codes(_mirror_subnet("ae3gis.local/open-vswitch"))


def test_mirror_on_plain_switch_warns():
    assert "mirror.unsupported_switch" in codes(_mirror_subnet("kathara/base"))


def test_mirror_unknown_target_errors():
    assert "mirror.target_unknown" in codes(
        _mirror_subnet("ae3gis.local/open-vswitch", mirror_to="nope")
    )
