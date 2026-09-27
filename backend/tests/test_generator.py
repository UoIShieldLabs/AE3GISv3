"""Generated topologies: shape, limits, and that they validate and plan cleanly."""

import pytest

from domain import validation
from domain.generator import GeneratorError, GeneratorParams, counts, generate
from domain.plan import build_lab_plan


@pytest.mark.parametrize("hosts", [1, 10, 230, 1000, 4000])
def test_generated_topologies_validate_and_plan(hosts):
    p = GeneratorParams(hosts=hosts, servers=2)
    data = generate(p)
    diags = validation.validate(data)
    assert not validation.has_errors(diags), [d.message for d in diags if d.severity == "error"][:3]
    plan = build_lab_plan(data, "bench")
    c = counts(p)
    assert len(plan.nodes) == c["nodes"] and len(plan.collision_domains) == c["links"]


def test_layout_and_addresses():
    data = generate(
        GeneratorParams(hosts=250, servers=1, hosts_per_subnet=200, hosts_per_switch=48)
    )
    [site] = data["sites"]
    subnets = {s["id"]: s for s in site["subnets"]}
    assert set(subnets) == {"sub-srv", "sub-0", "sub-1"}
    assert [c["from"] for c in site["subnetConnections"]] == ["sub-0", "sub-1"]
    s0 = subnets["sub-0"]
    ips = {c["id"]: c.get("ip") for c in s0["containers"]}
    assert ips["r0"] == "10.1.0.1" and ips["sw0"] == "10.1.0.2" and ips["sw0-1"] == "10.1.0.240"
    assert ips["h0-1"] == "10.1.0.10" and ips["h0-200"] == "10.1.0.209"
    assert len([c for c in s0["containers"] if c["id"].startswith("sw0-")]) == 5  # 200 / 48
    # Every host hangs off an access switch, every access switch off the distribution one.
    links = {(c["from"], c["to"]) for c in s0["connections"]}
    assert ("h0-49", "sw0-2") in links and ("sw0-2", "sw0") in links and ("sw0", "r0") in links
    assert len([c for c in subnets["sub-1"]["containers"] if c["id"].startswith("h1-")]) == 50
    assert data["generator"]["hosts"] == 250


def test_limits():
    with pytest.raises(GeneratorError, match="at most 64"):
        generate(GeneratorParams(hosts=65 * 10, hosts_per_subnet=10))
    with pytest.raises(GeneratorError, match="access switches"):
        generate(GeneratorParams(hosts=200, hosts_per_switch=4))
    with pytest.raises(GeneratorError):
        generate(GeneratorParams(hosts=0, servers=0))


def test_generate_endpoint(client):
    r = client.post("/api/v1/topologies/generate", json={"hosts": 12, "servers": 2, "name": "g"})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["name"] == "g" and not [d for d in rec["diagnostics"] if d["severity"] == "error"]
    bad = client.post("/api/v1/topologies/generate", json={"hosts": 200, "hosts_per_switch": 4})
    assert bad.status_code == 422 and bad.json()["code"] == "bad_generator"
