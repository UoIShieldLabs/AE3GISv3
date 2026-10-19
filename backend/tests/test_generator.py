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


MIX = {
    "host_mix": [
        {"type": "workstation", "image": "ae3gis.local/benign-client", "weight": 60},
        {"type": "workstation", "weight": 20},
        {"type": "workstation", "image": "ae3gis.local/wazuh-agent", "weight": 15},
        {"type": "workstation", "image": "ae3gis.local/firefox", "weight": 5},
    ],
    "server_mix": [
        {"type": "dns-server", "count": 1},
        {"type": "web-server", "image": "ae3gis.local/nginx", "per_hosts": 50},
        {"type": "database-server", "per_hosts": 100},
    ],
    "switch_mix": [
        {"type": "switch", "weight": 3},
        {"type": "switch", "image": "ae3gis.local/open-vswitch", "weight": 1},
    ],
    "core_type": "firewall",
    "core_image": "ae3gis.local/iptables",
    "seed": 1,
}


def _containers(data):
    return [c for s in data["sites"][0]["subnets"] for c in s["containers"]]


def _composition(data, prefix):
    out = {}
    for c in _containers(data):
        if c["id"].startswith(prefix):
            key = (c["type"], c.get("image"))
            out[key] = out.get(key, 0) + 1
    return out


def test_apportion_is_exact_and_stable():
    from domain.generator import _apportion

    assert _apportion(10, [60, 20, 15, 5]) == [6, 2, 2, 0]  # 1.5 vs 0.5: the larger remainder
    assert _apportion(25, [60, 20, 15, 5]) == [15, 5, 4, 1]
    assert _apportion(7, [1, 1, 1]) == [3, 2, 2]  # ties go to the earlier entry
    assert _apportion(0, [1, 2]) == [0, 0]
    for n in (1, 13, 200, 801):
        assert sum(_apportion(n, [60, 20, 15, 5])) == n


@pytest.mark.parametrize("hosts", [10, 100, 250, 800])
def test_mixed_topology_validates_plans_and_matches_counts(hosts):
    p = GeneratorParams(hosts=hosts, **MIX)
    data = generate(p)
    diags = validation.validate(data)
    assert not validation.has_errors(diags), [d.message for d in diags if d.severity == "error"][:3]
    plan = build_lab_plan(data, "bench")
    c = counts(p)
    assert len(plan.nodes) == c["nodes"] and len(plan.collision_domains) == c["links"]
    hosts_by_kind = _composition(data, "h")
    assert sum(hosts_by_kind.values()) == hosts
    assert hosts_by_kind[("workstation", "ae3gis.local/benign-client")] == round(hosts * 0.6)
    servers = _composition(data, "srv-")
    assert servers[("dns-server", None)] == 1
    assert servers[("web-server", "ae3gis.local/nginx")] == -(-hosts // 50)
    assert servers[("database-server", None)] == -(-hosts // 100)
    switches = _composition(data, "sw")
    assert sum(switches.values()) == c["switches"]
    assert switches.get(("switch", "ae3gis.local/open-vswitch"), 0) == round(c["switches"] / 4)
    core = next(x for x in _containers(data) if x["id"] == "core")
    assert core["type"] == "firewall" and core["image"] == "ae3gis.local/iptables"
    # the plan deploys each node's mix image (or its type's default)
    images = {n.id: n.image for n in plan.nodes}
    assert images["core"] == "ae3gis.local/iptables"
    assert {images[x["id"]] for x in _containers(data) if x["id"].startswith("srv-")} >= {
        "kathara/base",
        "ae3gis.local/nginx",
        "postgres:alpine",
    }


def test_mixed_topology_is_seeded():
    a = generate(GeneratorParams(hosts=120, **MIX))
    b = generate(GeneratorParams(hosts=120, **MIX))
    c = generate(GeneratorParams(hosts=120, **{**MIX, "seed": 2}))
    assert a == b
    kinds = [(x["id"], x["type"], x.get("image")) for x in _containers(a)]
    assert kinds != [(x["id"], x["type"], x.get("image")) for x in _containers(c)]
    assert _composition(a, "h") == _composition(c, "h")  # same mix, different places


def test_kinds_used_lists_every_placeable_kind():
    from domain.generator import kinds_used

    kinds = kinds_used(GeneratorParams(hosts=2, **MIX))
    # Every mix entry counts, even those a 2-host topology leaves out.
    assert ("workstation", "ae3gis.local/firefox") in kinds
    assert ("web-server", "ae3gis.local/nginx") in kinds and ("switch", None) in kinds
    assert ("router", None) in kinds and ("firewall", "ae3gis.local/iptables") in kinds
    assert len(kinds) == len(set(kinds))
    assert kinds_used(GeneratorParams(hosts=2)) == [
        ("router", None),
        ("workstation", None),
        ("switch", None),
    ]


def test_no_mix_keeps_the_plain_topology():
    data = generate(GeneratorParams(hosts=60, servers=2))
    assert all("image" not in c for c in _containers(data))
    assert {c["type"] for c in _containers(data) if c["id"].startswith(("h", "srv-"))} == {
        "workstation"
    }
    core = next(x for x in _containers(data) if x["id"] == "core")
    assert core["type"] == "router"


def test_mix_errors():
    from domain.generator import check_types

    bad = [
        {"host_mix": []},
        {"host_mix": [{"type": "workstation", "weight": 0}]},
        {"host_mix": [{"weight": 1}]},
        {"server_mix": [{"type": "web-server"}]},
        {"server_mix": [{"type": "web-server", "count": 1, "per_hosts": 10}]},
        {"server_mix": [{"type": "web-server", "count": 231}]},
    ]
    for extra in bad:
        with pytest.raises(GeneratorError):
            generate(GeneratorParams(hosts=10, **extra))
    p = GeneratorParams(hosts=10, host_mix=[{"type": "toaster", "weight": 1}])
    with pytest.raises(GeneratorError, match="toaster"):
        check_types(p, {"workstation", "router", "switch"})


def test_generate_endpoint_with_a_mix(client):
    body = {"hosts": 100, "name": "mixed", **MIX}
    r = client.post("/api/v1/topologies/generate", json=body)
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["generator"]["seed"] == 1
    assert any(c.get("image") == "ae3gis.local/open-vswitch" for c in _containers(data))
    unknown = {**body, "host_mix": [{"type": "toaster", "weight": 1}]}
    bad = client.post("/api/v1/topologies/generate", json=unknown)
    assert bad.status_code == 422 and bad.json()["code"] == "bad_generator"


def test_max_hosts():
    from domain.generator import max_hosts

    assert max_hosts(GeneratorParams(hosts=1)) == 64 * 200  # 64 client subnets of 200
    assert max_hosts(GeneratorParams(hosts=1, hosts_per_subnet=230)) == 64 * 230
    p = GeneratorParams(hosts=1, **MIX)  # 1 per 50 + 1 per 100 servers (+1) ≤ 230
    most = max_hosts(p)
    generate(GeneratorParams(**{**p.to_dict(), "hosts": most}))
    with pytest.raises(GeneratorError):
        generate(GeneratorParams(**{**p.to_dict(), "hosts": most + 1}))


# Every catalog type as a leaf (networking types too), as the random benchmark does.
RANDOM = {
    "hosts": [
        {"type": "workstation", "images": ["kathara/base", "ae3gis.local/benign-client"]},
        {"type": "web-server", "images": ["httpd:alpine", "ae3gis.local/nginx"]},
        {"type": "database-server", "images": ["postgres:alpine"]},
        {"type": "router", "images": ["kathara/frr"]},
        {"type": "firewall", "images": ["kathara/frr", "ae3gis.local/nftables"]},
        {"type": "switch", "images": ["kathara/base", "ae3gis.local/open-vswitch"]},
    ],
    "switches": [{"type": "switch", "images": ["kathara/base", "ae3gis.local/open-vswitch"]}],
    "routers": [
        {"type": "router", "images": ["kathara/frr"]},
        {"type": "firewall", "images": ["kathara/frr", "ae3gis.local/iptables"]},
    ],
}


def _hosts(data):
    return {c["id"]: (c["type"], c["image"]) for c in _containers(data) if c["id"].startswith("h")}


@pytest.mark.parametrize("hosts", [1, 60, 450])
def test_random_topology_validates_plans_and_matches_counts(hosts):
    p = GeneratorParams(hosts=hosts, servers=0, random=RANDOM, seed=4)
    data = generate(p)
    diags = validation.validate(data)
    assert not validation.has_errors(diags), [d.message for d in diags if d.severity == "error"][:3]
    plan = build_lab_plan(data, "bench")
    c = counts(p)
    assert len(plan.nodes) == c["nodes"] and len(plan.collision_domains) == c["links"]
    # Every node carries its drawn image; structural slots come from their pools.
    nodes = {n.id: n for n in plan.nodes}
    assert {nodes["core"].type, nodes["r0"].type} <= {"router", "firewall"}
    assert all(nodes[i].image != "ae3gis.local/nftables" for i in nodes if i.startswith("r"))
    assert nodes["sw0"].role == "switch"
    # Hosts drawn as routers still get the subnet's gateway as theirs; the
    # subnet's hosts keep the real gateway router.
    assert data["sites"][0]["subnets"][1]["gateway"] == "10.1.0.1"


def test_random_topology_is_seeded_and_prefix_stable():
    a = generate(GeneratorParams(hosts=120, random=RANDOM, seed=1))
    assert a == generate(GeneratorParams(hosts=120, random=RANDOM, seed=1))
    assert _hosts(a) != _hosts(generate(GeneratorParams(hosts=120, random=RANDOM, seed=2)))
    small = _hosts(generate(GeneratorParams(hosts=50, random=RANDOM, seed=1)))
    assert all(_hosts(a)[h] == kind for h, kind in small.items())  # a climb keeps its hosts


def test_random_draws_give_types_equal_odds():
    pool = [
        {"type": f"t{i}", "images": [f"img{i}-{j}" for j in range(i % 3 + 1)]} for i in range(15)
    ]
    data = generate(GeneratorParams(hosts=9000, hosts_per_subnet=230, random={"hosts": pool}))
    kinds = list(_hosts(data).values())
    by_type: dict[str, int] = {}
    for t, _ in kinds:
        by_type[t] = by_type.get(t, 0) + 1
    assert len(by_type) == 15
    assert all(abs(n / len(kinds) - 1 / 15) < 0.015 for n in by_type.values())  # ~4 sigma
    # Within a type, images too (t2 has 3).
    t2 = [img for t, img in kinds if t == "t2"]
    assert all(abs(t2.count(f"img2-{j}") / len(t2) - 1 / 3) < 0.07 for j in range(3))


def test_random_errors_and_catalog_checks():
    from domain.generator import check, check_catalog, kinds_used

    bad = [
        {"random": {"switches": RANDOM["switches"]}},
        {"random": {"hosts": [{"type": "workstation", "images": []}]}},
        {"random": {"hosts": RANDOM["hosts"], "extra": []}},
        {"random": RANDOM, "host_mix": [{"type": "workstation", "weight": 1}]},
        {"random": RANDOM, "core_type": "firewall"},
    ]
    for extra in bad:
        with pytest.raises(GeneratorError):
            check(GeneratorParams(hosts=10, **extra))
    import catalog

    types = catalog.node_types()
    check_catalog(GeneratorParams(hosts=10, random=RANDOM), types)
    wrong_role = {**RANDOM, "switches": [{"type": "workstation", "images": ["kathara/base"]}]}
    with pytest.raises(GeneratorError, match="not a switch"):
        check_catalog(GeneratorParams(hosts=10, random=wrong_role), types)
    foreign = {"hosts": [{"type": "router", "images": ["ae3gis.local/nginx"]}]}
    with pytest.raises(GeneratorError, match="has no image"):
        check_catalog(GeneratorParams(hosts=10, random=foreign), types)
    kinds = kinds_used(GeneratorParams(hosts=1, servers=0, random=RANDOM))
    assert ("firewall", "ae3gis.local/nftables") in kinds and (
        "firewall",
        "ae3gis.local/iptables",
    ) in kinds
    assert ("workstation", None) not in kinds  # the pool replaces host_type


def test_generate_endpoint_with_random_pools(client):
    body = {"hosts": 40, "name": "random", "random": RANDOM, "seed": 9}
    r = client.post("/api/v1/topologies/generate", json=body)
    assert r.status_code == 201, r.text
    assert {c["type"] for c in _containers(r.json()["data"]) if c["id"].startswith("h")} > {
        "router"
    }
    wrong = {**body, "random": {"hosts": [{"type": "router", "images": ["httpd:alpine"]}]}}
    assert client.post("/api/v1/topologies/generate", json=wrong).json()["code"] == "bad_generator"
