from domain.plan import build_lab_plan


def _two_subnet_topology():
    return {
        "name": "demo",
        "sites": [
            {
                "id": "s1",
                "name": "Site 1",
                "subnets": [
                    {
                        "id": "subA",
                        "name": "A",
                        "cidr": "10.0.1.0/24",
                        "gateway": "10.0.1.1",
                        "containers": [
                            {"id": "rA", "name": "Router A", "type": "router", "ip": "10.0.1.1"},
                            {"id": "swA", "name": "Switch A", "type": "switch", "ip": "10.0.1.2"},
                            {"id": "hA", "name": "Host A", "type": "workstation", "ip": "10.0.1.5"},
                        ],
                        "connections": [{"from": "swA", "to": "rA"}, {"from": "swA", "to": "hA"}],
                    },
                    {
                        "id": "subB",
                        "name": "B",
                        "cidr": "10.0.2.0/24",
                        "gateway": "10.0.2.1",
                        "containers": [
                            {"id": "rB", "name": "Router B", "type": "router", "ip": "10.0.2.1"},
                            {"id": "swB", "name": "Switch B", "type": "switch", "ip": "10.0.2.2"},
                            {"id": "hB", "name": "Host B", "type": "workstation", "ip": "10.0.2.5"},
                        ],
                        "connections": [{"from": "swB", "to": "rB"}, {"from": "swB", "to": "hB"}],
                    },
                ],
                "subnetConnections": [{"from": "subA", "to": "subB"}],
            }
        ],
        "siteConnections": [],
    }


def _node(plan, cid):
    return next(n for n in plan.nodes if n.id == cid)


def test_all_nodes_present_with_roles_and_images():
    plan = build_lab_plan(_two_subnet_topology(), "demo-lab")
    assert {n.id for n in plan.nodes} == {"rA", "swA", "hA", "rB", "swB", "hB"}
    assert _node(plan, "rA").role == "router"
    assert _node(plan, "swA").role == "switch"
    assert _node(plan, "hA").role == "host"
    assert _node(plan, "rA").image == "kathara/frr"


def test_router_gets_ip_forward_and_cross_subnet_static_route():
    plan = build_lab_plan(_two_subnet_topology(), "demo-lab")
    rA = _node(plan, "rA")
    assert "sysctl -w net.ipv4.ip_forward=1" in rA.startup
    assert any("ip addr add 10.0.1.1/24" in c for c in rA.startup)
    # PtP /30 WAN address to the peer router
    assert any("10.255.0.1/30" in c for c in rA.startup)
    # static route to the far subnet via the peer's PtP address
    assert any("ip route add 10.0.2.0/24 via 10.255.0.2" in c for c in rA.startup)


def test_peer_router_has_mirror_route():
    plan = build_lab_plan(_two_subnet_topology(), "demo-lab")
    rB = _node(plan, "rB")
    assert any("ip route add 10.0.1.0/24 via 10.255.0.1" in c for c in rB.startup)


def test_host_gets_ip_and_default_route():
    plan = build_lab_plan(_two_subnet_topology(), "demo-lab")
    hA = _node(plan, "hA")
    assert any("ip addr add 10.0.1.5/24" in c for c in hA.startup)
    assert any("ip route replace default via 10.0.1.1" in c for c in hA.startup)


def test_switch_builds_bridge():
    plan = build_lab_plan(_two_subnet_topology(), "demo-lab")
    swA = _node(plan, "swA")
    assert any("br0 type bridge" in c for c in swA.startup)


def test_point_to_point_collision_domains_have_two_endpoints():
    plan = build_lab_plan(_two_subnet_topology(), "demo-lab")
    counts = {}
    for n in plan.nodes:
        for i in n.interfaces:
            counts.setdefault(i.collision_domain, []).append((n.id, i.name))
    # every collision domain is a point-to-point link (exactly two endpoints)
    for cd, endpoints in counts.items():
        assert len(endpoints) == 2, f"{cd} has {endpoints}"


def test_wan_link_shared_between_routers():
    plan = build_lab_plan(_two_subnet_topology(), "demo-lab")
    rA_wan = {
        i.collision_domain
        for i in _node(plan, "rA").interfaces
        if i.ip and i.ip.startswith("10.255")
    }
    rB_wan = {
        i.collision_domain
        for i in _node(plan, "rB").interfaces
        if i.ip and i.ip.startswith("10.255")
    }
    assert rA_wan and rA_wan == rB_wan


def test_gateway_auto_detected_when_unset():
    topo = _two_subnet_topology()
    # drop the explicit gateway on subnet A; the router IP should be detected
    topo["sites"][0]["subnets"][0]["gateway"] = ""
    plan = build_lab_plan(topo, "demo-lab")
    hA = _node(plan, "hA")
    assert any("ip route replace default via 10.0.1.1" in c for c in hA.startup)


def test_empty_topology_yields_empty_plan():
    plan = build_lab_plan({"sites": [], "siteConnections": []}, "empty")
    assert plan.nodes == []
    assert plan.collision_domains == []


def test_iface_base_shifts_interface_names_and_commands():
    plan = build_lab_plan(_two_subnet_topology(), "demo-lab", iface_base=1)
    names = {i.name for n in plan.nodes for i in n.interfaces}
    assert "eth0" not in names and "eth1" in names
    hA = _node(plan, "hA")
    assert any("dev eth1" in c for c in hA.startup)


def test_plan_serialises_with_links_and_images():
    plan = build_lab_plan(_two_subnet_topology(), "demo-lab")
    d = plan.to_dict()
    assert d["name"] == "demo-lab"
    assert {n["id"] for n in d["nodes"]} == {"rA", "swA", "hA", "rB", "swB", "hB"}
    assert all(len(link["endpoints"]) == 2 for link in d["links"])
    assert "kathara/frr" in d["images"]
    assert _node(plan, "rA").machine_name == "ra"
