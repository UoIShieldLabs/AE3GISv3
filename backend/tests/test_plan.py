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
    # IP forwarding is a creation-time sysctl (read-only /proc/sys at runtime).
    assert rA.sysctls.get("net.ipv4.ip_forward") == "1"
    assert not any("ip_forward" in c for c in rA.startup)
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


def test_switch_with_own_bridge_is_only_addressed():
    topo = _two_subnet_topology()
    sw = topo["sites"][0]["subnets"][0]["containers"][1]
    sw["image"] = "ae3gis.local/open-vswitch"  # builds br0 itself
    plan = build_lab_plan(topo, "demo-lab")
    swA = _node(plan, "swA")
    assert not any("type bridge" in c or "master" in c for c in swA.startup)
    assert "until ip link show br0" in swA.startup[0]
    assert "ip addr replace 10.0.1.2/24 dev br0" in swA.startup
    # the other switch still bridges its ports itself
    assert any("br0 type bridge" in c for c in _node(plan, "swB").startup)


def test_nodes_carry_their_image_env():
    topo = _two_subnet_topology()
    topo["sites"][0]["subnets"][0]["containers"][2].update(
        type="database-server", image="postgres:alpine"
    )
    plan = build_lab_plan(topo, "demo-lab")
    assert _node(plan, "hA").env == {"POSTGRES_PASSWORD": "pass"}
    assert _node(plan, "hB").env == {}
    assert _node(plan, "hA").to_dict()["env"] == {"POSTGRES_PASSWORD": "pass"}


def test_per_node_env_overrides_and_extends_image_env():
    topo = _two_subnet_topology()
    hA = topo["sites"][0]["subnets"][0]["containers"][2]
    hA.update(
        type="database-server",
        image="postgres:alpine",
        # Override the image's value, add a new one, and include malformed
        # entries (non-str value is coerced; None and blank key are dropped).
        env={"POSTGRES_PASSWORD": "secret", "IEC104_SERVER": "10.0.3.50", "PORT": 2404, "SKIP": None, "": "x"},
    )
    plan = build_lab_plan(topo, "demo-lab")
    assert _node(plan, "hA").env == {
        "POSTGRES_PASSWORD": "secret",
        "IEC104_SERVER": "10.0.3.50",
        "PORT": "2404",
    }
    # A node with no env override still gets just its image env.
    assert _node(plan, "hB").env == {}


def test_images_without_bash_name_their_shell():
    topo = _two_subnet_topology()
    topo["sites"][0]["subnets"][0]["containers"][2].update(type="web-server", image="httpd:alpine")
    plan = build_lab_plan(topo, "demo-lab")
    assert _node(plan, "hA").shell == "/bin/sh"
    assert _node(plan, "hB").shell is None


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


# ── Multi-homing: interface legs (interfaces[]) ───────────────────────────


def _multihomed_topology():
    """IT-LAN + OT-LAN in one site. ``fw`` is a dual-homed router (the gateway
    of both subnets); ``historian`` is a dual-homed HOST (IT/OT) that must not
    forward. Legs are declared via ``interfaces[]`` and attach to the OT switch.
    """
    return {
        "name": "ics",
        "sites": [
            {
                "id": "site1",
                "name": "Lab",
                "subnets": [
                    {
                        "id": "it",
                        "name": "IT-LAN",
                        "cidr": "10.0.5.0/24",
                        "gateway": "10.0.5.1",
                        "containers": [
                            {
                                "id": "fw",
                                "name": "fw",
                                "type": "firewall",
                                "ip": "10.0.5.1",
                                "interfaces": [{"subnetId": "ot", "ip": "10.0.3.1"}],
                            },
                            {"id": "itsw", "name": "it-sw", "type": "switch", "ip": "10.0.5.2"},
                            {
                                "id": "historian",
                                "name": "hist",
                                "type": "database-server",
                                "ip": "10.0.5.20",
                                "interfaces": [{"subnetId": "ot", "ip": "10.0.3.20"}],
                            },
                        ],
                        "connections": [
                            {"id": "c1", "from": "itsw", "to": "fw"},
                            {"id": "c3", "from": "itsw", "to": "historian"},
                        ],
                    },
                    {
                        "id": "ot",
                        "name": "OT-LAN",
                        "cidr": "10.0.3.0/24",
                        # No explicit gateway: it must resolve to fw's leg (10.0.3.1).
                        "containers": [
                            {"id": "otsw", "name": "ot-sw", "type": "switch", "ip": "10.0.3.2"},
                            {"id": "plc", "name": "plc", "type": "plc", "ip": "10.0.3.50"},
                        ],
                        "connections": [{"id": "c4", "from": "otsw", "to": "plc"}],
                    },
                ],
                "subnetConnections": [],
            }
        ],
        "siteConnections": [],
    }


def test_dualhomed_host_addresses_every_leg_without_forwarding():
    plan = build_lab_plan(_multihomed_topology(), "ics")
    hist = _node(plan, "historian")
    assert hist.role == "host"
    ips = {(i.ip, i.prefix_len) for i in hist.interfaces}
    assert ("10.0.5.20", "24") in ips
    assert ("10.0.3.20", "24") in ips
    assert any("ip addr add 10.0.5.20/24" in c for c in hist.startup)
    assert any("ip addr add 10.0.3.20/24" in c for c in hist.startup)
    # A multi-homed host must not route between its legs: forwarding off, set as
    # a creation-time sysctl (not a runtime command, since /proc/sys is read-only).
    assert hist.sysctls.get("net.ipv4.ip_forward") == "0"
    assert not any("ip_forward" in c for c in hist.startup)
    # Default route via the home (IT) subnet's gateway only.
    assert any("ip route replace default via 10.0.5.1" in c for c in hist.startup)


def test_dualhomed_router_forwards_and_addresses_both_legs():
    plan = build_lab_plan(_multihomed_topology(), "ics")
    fw = _node(plan, "fw")
    assert fw.role == "router"
    assert fw.sysctls.get("net.ipv4.ip_forward") == "1"
    assert any("ip addr add 10.0.5.1/24" in c for c in fw.startup)
    assert any("ip addr add 10.0.3.1/24" in c for c in fw.startup)


def test_leg_shares_collision_domain_with_target_subnet_switch():
    plan = build_lab_plan(_multihomed_topology(), "ics")
    otsw = _node(plan, "otsw")
    sw_cds = {i.collision_domain for i in otsw.interfaces}
    # The OT switch bridges every OT leg: plc, fw's leg and historian's leg.
    for cid in ("plc", "fw", "historian"):
        node = _node(plan, cid)
        ot_leg = next(i for i in node.interfaces if i.ip and i.ip.startswith("10.0.3."))
        assert ot_leg.collision_domain in sw_cds, f"{cid} OT leg not bridged by the switch"


def test_subnet_gateway_resolves_through_a_leg_router():
    # OT-LAN has no explicit gateway; it should resolve to fw's leg (10.0.3.1),
    # so an OT host (plc) gets its default route via it.
    plan = build_lab_plan(_multihomed_topology(), "ics")
    plc = _node(plan, "plc")
    assert any("ip route replace default via 10.0.3.1" in c for c in plc.startup)


def test_leg_with_unknown_subnet_is_ignored():
    topo = _multihomed_topology()
    topo["sites"][0]["subnets"][0]["containers"][0]["interfaces"] = [
        {"subnetId": "does-not-exist", "ip": "10.9.9.9"}
    ]
    plan = build_lab_plan(topo, "ics")  # must not raise
    fw = _node(plan, "fw")
    assert not any("10.9.9.9" in c for c in fw.startup)


def test_leg_on_a_switch_is_not_bridged():
    # A switch leg would put the other subnet's segment into the switch's bridge
    # (one L2 domain for both subnets). The plan ignores it; validation errors.
    topo = _multihomed_topology()
    topo["sites"][0]["subnets"][0]["containers"][1]["interfaces"] = [
        {"subnetId": "ot", "ip": "10.0.3.9"}
    ]
    plan = build_lab_plan(topo, "ics")
    itsw, otsw = _node(plan, "itsw"), _node(plan, "otsw")
    shared = {i.collision_domain for i in itsw.interfaces} & {
        i.collision_domain for i in otsw.interfaces
    }
    assert not shared, "the IT switch must not share a segment with the OT switch"
    assert not any("10.0.3.9" in c for c in itsw.startup)


def _lan(sid, cidr, gw, members, links):
    return {
        "id": sid,
        "name": sid,
        "cidr": cidr,
        "gateway": gw,
        "containers": members,
        "connections": [{"id": f"{sid}-{a}-{b}", "from": a, "to": b} for a, b in links],
    }


def _site(subnets, subnet_links=()):
    return {
        "name": "t",
        "sites": [
            {
                "id": "s1",
                "name": "S",
                "location": "",
                "subnets": subnets,
                "subnetConnections": [
                    {"id": f"w-{a}-{b}", "from": a, "to": b} for a, b in subnet_links
                ],
            }
        ],
        "siteConnections": [],
    }


def _dev(cid, ctype, ip, **extra):
    return {"id": cid, "name": cid, "type": ctype, "ip": ip, **extra}


def test_leg_gated_subnet_can_link_to_another_subnet():
    # fw (home A) gateways C through a leg; C is linked to D: the link must land
    # on fw (a /30 to D's router) and routes must flow both ways.
    topo = _site(
        [
            _lan(
                "A",
                "10.0.1.0/24",
                "10.0.1.1",
                [
                    _dev(
                        "fw",
                        "firewall",
                        "10.0.1.1",
                        interfaces=[{"subnetId": "C", "ip": "10.0.3.1"}],
                    ),
                    _dev("swA", "switch", "10.0.1.2"),
                ],
                [("swA", "fw")],
            ),
            _lan(
                "C",
                "10.0.3.0/24",
                "10.0.3.1",
                [_dev("swC", "switch", "10.0.3.2"), _dev("hC", "workstation", "10.0.3.5")],
                [("swC", "hC")],
            ),
            _lan(
                "D",
                "10.0.4.0/24",
                "10.0.4.1",
                [_dev("rD", "router", "10.0.4.1"), _dev("swD", "switch", "10.0.4.2")],
                [("swD", "rD")],
            ),
        ],
        subnet_links=[("C", "D")],
    )
    plan = build_lab_plan(topo, "t")
    fw, rd = _node(plan, "fw"), _node(plan, "rD")
    shared = {i.collision_domain for i in fw.interfaces} & {
        i.collision_domain for i in rd.interfaces
    }
    assert len(shared) == 1, "the C-D link must be a link between fw and rD"
    assert any("ip route add 10.0.3.0/24 via" in c for c in rd.startup)
    assert any("ip route add 10.0.4.0/24 via" in c for c in fw.startup)


def _switchless(c_members, c_links, legs):
    # h (home A) legs into C; C has no switch.
    return _site(
        [
            _lan(
                "A",
                "10.0.1.0/24",
                "10.0.1.1",
                [
                    _dev("rA", "router", "10.0.1.1"),
                    _dev("swA", "switch", "10.0.1.2"),
                    _dev("h", "workstation", "10.0.1.5", interfaces=legs),
                ],
                [("swA", "rA"), ("swA", "h")],
            ),
            _lan("C", "10.0.3.0/24", "", c_members, c_links),
        ]
    )


def test_leg_into_a_switchless_subnet_links_to_an_unwired_router():
    topo = _switchless(
        [_dev("rC", "router", "10.0.3.1")], [], [{"subnetId": "C", "ip": "10.0.3.7"}]
    )
    plan = build_lab_plan(topo, "t")
    h, rc = _node(plan, "h"), _node(plan, "rC")
    cd = (
        {i.collision_domain for i in h.interfaces} & {i.collision_domain for i in rc.interfaces}
    ).pop()
    # Both ends are addressed on that link, so they share the segment.
    assert next(i.ip for i in h.interfaces if i.collision_domain == cd) == "10.0.3.7"
    assert next(i.ip for i in rc.interfaces if i.collision_domain == cd) == "10.0.3.1"


def test_leg_into_a_fully_wired_switchless_subnet_is_not_attached():
    # rC already holds its C address on its link to hC: a leg to rC would be dead.
    topo = _switchless(
        [_dev("rC", "router", "10.0.3.1"), _dev("hC", "workstation", "10.0.3.5")],
        [("rC", "hC")],
        [{"subnetId": "C", "ip": "10.0.3.7"}],
    )
    h = _node(build_lab_plan(topo, "t"), "h")
    assert not any(i.ip == "10.0.3.7" for i in h.interfaces)


def test_two_legs_into_an_empty_subnet_share_a_segment():
    topo = _switchless([], [], [{"subnetId": "C", "ip": "10.0.3.7"}])
    a = topo["sites"][0]["subnets"][0]["containers"]
    a.append(
        _dev("h2", "workstation", "10.0.1.6", interfaces=[{"subnetId": "C", "ip": "10.0.3.8"}])
    )
    topo["sites"][0]["subnets"][0]["connections"].append({"id": "x", "from": "swA", "to": "h2"})
    plan = build_lab_plan(topo, "t")
    h, h2 = _node(plan, "h"), _node(plan, "h2")
    cd = {i.collision_domain for i in h.interfaces if i.ip == "10.0.3.7"}
    assert cd and cd == {i.collision_domain for i in h2.interfaces if i.ip == "10.0.3.8"}


# ── OVS port mirroring (SPAN) ─────────────────────────────────────────────


def _mirror_topology(switch_image="ae3gis.local/open-vswitch"):
    return {
        "name": "m",
        "sites": [
            {
                "id": "s",
                "name": "s",
                "subnets": [
                    {
                        "id": "ot",
                        "name": "OT",
                        "cidr": "10.0.3.0/24",
                        "gateway": "10.0.3.1",
                        "containers": [
                            {
                                "id": "sw",
                                "name": "sw",
                                "type": "switch",
                                "ip": "10.0.3.2",
                                "image": switch_image,
                                "mirrorTo": "ids",
                            },
                            {"id": "plc", "name": "plc", "type": "plc", "ip": "10.0.3.50"},
                            {"id": "ids", "name": "ids", "type": "ids", "ip": "10.0.3.40"},
                        ],
                        "connections": [
                            {"id": "a", "from": "sw", "to": "plc"},
                            {"id": "b", "from": "sw", "to": "ids"},
                        ],
                    }
                ],
                "subnetConnections": [],
            }
        ],
        "siteConnections": [],
    }


def test_ovs_switch_mirrors_to_the_ids_facing_port():
    plan = build_lab_plan(_mirror_topology(), "m")
    sw = _node(plan, "sw")
    ids_cd = _node(plan, "ids").interfaces[0].collision_domain
    port = next(i.name for i in sw.interfaces if i.collision_domain == ids_cd)
    mirror = next((c for c in sw.startup if "create mirror" in c), None)
    assert mirror is not None
    assert f"get port {port}" in mirror
    assert "select-all=true" in mirror
    assert "mirrors=@m" in mirror


def test_no_mirror_without_own_bridge_switch():
    plan = build_lab_plan(_mirror_topology(switch_image="kathara/base"), "m")
    sw = _node(plan, "sw")
    assert not any("create mirror" in c for c in sw.startup)
