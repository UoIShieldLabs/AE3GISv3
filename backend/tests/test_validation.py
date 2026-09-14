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
