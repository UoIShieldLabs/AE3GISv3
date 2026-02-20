"""Convert a TopologyData dict into a ContainerLab YAML string."""

from __future__ import annotations

from collections import defaultdict

import yaml

_IMAGE_ROUTER = "frrouting/frr:latest"
# Use a plain Linux image for switch containers. The previous OVS image
# attempts to load host kernel modules on startup, which breaks on vanilla
# installs where openvswitch is not present.
_IMAGE_SWITCH = "alpine:latest"
_IMAGE_HOST   = "alpine:latest"

_ROUTER_TYPES = frozenset({"router", "firewall"})
_SWITCH_TYPES = frozenset({"switch"})


def _image_for(ctype: str) -> str:
    if ctype in _ROUTER_TYPES:
        return _IMAGE_ROUTER
    if ctype in _SWITCH_TYPES:
        return _IMAGE_SWITCH
    return _IMAGE_HOST


def _eth_index(iface: str) -> int:
    """Extract numeric index from interface name like 'eth1' → 1."""
    try:
        return int(iface.replace("eth", ""))
    except ValueError:
        return 0


def generate_clab_yaml(topology: dict) -> str:
    """Accept the raw topology dict (as stored in the DB) and return clab YAML.

    The topology dict matches the frontend TopologyData shape:
      { name?, sites[], siteConnections[] }

    Node images chosen by type:
      router / firewall  → frrouting/frr:latest
      switch             → tollan/openvswitch-xp:v0.1
      everything else    → alpine:latest

    Cross-subnet routing is fully automatic:
      - When a subnet/site connection has no explicit container endpoints, the
        generator finds the gateway router in each subnet and connects them.
      - Router↔router cross-subnet links get auto-assigned /30 PtP IPs from
        10.255.0.0/24 plus matching static routes on each side.
      - Hosts get static routes to every other subnet via their effective gateway.
        If subnet.gateway is unset, the first router/firewall in the subnet is
        used as the effective gateway so hosts are always routed correctly.
      - Switches are configured with Open vSwitch (ovs-vsctl).
    """

    nodes: dict[str, dict] = {}
    links: list[dict] = []

    # ── Step 1: Build container and subnet metadata ──────────────────────────

    container_info: dict[str, dict] = {}   # cid → {type, ip, subnet_cidr, prefix_len, gateway}
    all_subnets:    dict[str, dict] = {}   # cidr → {gateway, prefix_len}
    subnet_id_map:  dict[str, dict] = {}   # subnet_id → {cidr, gateway, prefix_len}
    subnet_id_containers: dict[str, list] = {}  # subnet_id → [container dicts]
    site_id_subnets: dict[str, list] = {}   # site_id → [subnet dicts]

    for site in topology.get("sites", []):
        site_id = site.get("id", "")
        if site_id:
            site_id_subnets[site_id] = site.get("subnets", [])

        for subnet in site.get("subnets", []):
            sid     = subnet.get("id", "")
            cidr    = subnet.get("cidr", "")
            gateway = subnet.get("gateway") or ""
            pfx     = cidr.split("/")[1] if "/" in cidr else "24"
            containers = subnet.get("containers", [])

            # If gateway is unset, auto-detect from the first router/firewall in
            # the subnet so that hosts always have a working cross-subnet gateway.
            if not gateway:
                for c in containers:
                    if c.get("type", "") in _ROUTER_TYPES and c.get("ip"):
                        gateway = c["ip"]
                        break

            if cidr:
                all_subnets[cidr] = {"gateway": gateway, "prefix_len": pfx}
            if sid:
                subnet_id_map[sid] = {"cidr": cidr, "gateway": gateway, "prefix_len": pfx}
                subnet_id_containers[sid] = containers

            for c in containers:
                container_info[c["id"]] = {
                    "type":        c.get("type", ""),
                    "ip":          c.get("ip", ""),
                    "subnet_cidr": cidr,
                    "prefix_len":  pfx,
                    "gateway":     gateway,  # effective gateway (may be auto-detected)
                }

    # Build lookup: subnet_id / site_id → best gateway router container_id.
    # Priority: router/firewall whose IP matches the subnet gateway.
    # Fallback:  first router/firewall found in the subnet.
    # This lets subnet/site-level connections auto-resolve to the correct routers
    # without the user having to specify container endpoints manually.

    def _find_gateway_router(containers: list[dict]) -> str | None:
        subnet_gateway = None
        # Try to infer gateway from subnet metadata if available
        best = fallback = None
        for c in containers:
            if c.get("type", "") in _ROUTER_TYPES and c["id"] in container_info:
                gw = container_info[c["id"]].get("gateway", "")
                if c.get("ip") == gw and not best:
                    best = c["id"]
                if not fallback:
                    fallback = c["id"]
        return best or fallback

    gateway_router_map: dict[str, str] = {}   # subnet_id → container_id
    site_gateway_router_map: dict[str, str] = {}  # site_id → container_id

    for sid, containers in subnet_id_containers.items():
        gw = _find_gateway_router(containers)
        if gw:
            gateway_router_map[sid] = gw

    for site_id, subnets in site_id_subnets.items():
        for subnet in subnets:
            gw = _find_gateway_router(subnet.get("containers", []))
            if gw:
                site_gateway_router_map[site_id] = gw
                break  # use first subnet that has a router

    def _resolve_endpoint(raw_id: str | None) -> str | None:
        """Map subnet/site IDs to their gateway router; pass container IDs through."""
        if not raw_id:
            return None
        if raw_id in container_info:
            return raw_id
        return gateway_router_map.get(raw_id) or site_gateway_router_map.get(raw_id)

    # ── Step 2: Resolve all connections and auto-assign interfaces ───────────

    iface_counter:   dict[str, int]       = defaultdict(int)
    container_ifaces: dict[str, set[str]] = defaultdict(set)

    def _next_iface(cid: str) -> str:
        iface_counter[cid] += 1
        iface = f"eth{iface_counter[cid]}"
        container_ifaces[cid].add(iface)
        return iface

    # Pre-register all explicitly named interfaces so that auto-assignment
    # (_next_iface) never collides with an interface already claimed by an
    # existing connection in the topology data.
    def _preregister(conn: dict) -> None:
        raw_from = conn.get("fromContainer") or conn.get("from")
        raw_to   = conn.get("toContainer")   or conn.get("to")
        from_id  = _resolve_endpoint(raw_from) or raw_from
        to_id    = _resolve_endpoint(raw_to)   or raw_to
        if from_id and conn.get("fromInterface"):
            idx = _eth_index(conn["fromInterface"])
            iface_counter[from_id] = max(iface_counter[from_id], idx)
            container_ifaces[from_id].add(conn["fromInterface"])
        if to_id and conn.get("toInterface"):
            idx = _eth_index(conn["toInterface"])
            iface_counter[to_id] = max(iface_counter[to_id], idx)
            container_ifaces[to_id].add(conn["toInterface"])

    for site in topology.get("sites", []):
        for subnet in site.get("subnets", []):
            for conn in subnet.get("connections", []):
                _preregister(conn)
        for conn in site.get("subnetConnections", []):
            _preregister(conn)
    for conn in topology.get("siteConnections", []):
        _preregister(conn)

    def _resolve_conn(conn: dict) -> tuple[str | None, str, str | None, str]:
        from_id = conn.get("fromContainer") or conn.get("from")
        to_id   = conn.get("toContainer")   or conn.get("to")
        fi = conn.get("fromInterface") or (from_id and _next_iface(from_id))
        ti = conn.get("toInterface")   or (to_id   and _next_iface(to_id))
        if from_id and conn.get("fromInterface"):
            container_ifaces[from_id].add(conn["fromInterface"])
            iface_counter[from_id] = max(iface_counter[from_id], _eth_index(conn["fromInterface"]))
        if to_id and conn.get("toInterface"):
            container_ifaces[to_id].add(conn["toInterface"])
            iface_counter[to_id] = max(iface_counter[to_id], _eth_index(conn["toInterface"]))
        return from_id, fi, to_id, ti

    link_registry: list[tuple[str, str, str, str]] = []

    def _add_link(conn: dict) -> None:
        """Resolve a connection and add it only if both endpoints are containers.

        Subnet and site IDs are automatically resolved to their gateway router/
        firewall so that a user dragging a connection between two subnets or
        sites in the UI automatically sets up a physical WAN link (and routing)
        between the appropriate router containers without manual configuration.
        """
        raw_from = conn.get("fromContainer") or conn.get("from")
        raw_to   = conn.get("toContainer")   or conn.get("to")

        from_id = _resolve_endpoint(raw_from)
        to_id   = _resolve_endpoint(raw_to)

        if not from_id or not to_id:
            return
        if from_id not in container_info or to_id not in container_info:
            return

        # Rebuild conn with resolved container IDs so _resolve_conn picks them up.
        resolved = {**conn, "fromContainer": from_id, "toContainer": to_id}
        _, fi, _, ti = _resolve_conn(resolved)

        links.append({"endpoints": [f"{from_id}:{fi}", f"{to_id}:{ti}"]})
        link_registry.append((from_id, fi, to_id, ti))

    # Intra-subnet connections first → routers/hosts get their home interface
    # assigned as eth1 before any cross-subnet WAN interfaces are allocated.
    for site in topology.get("sites", []):
        for subnet in site.get("subnets", []):
            for conn in subnet.get("connections", []):
                _add_link(conn)
        for conn in site.get("subnetConnections", []):
            _add_link(conn)
    for conn in topology.get("siteConnections", []):
        _add_link(conn)

    # ── Step 3: Compute per-interface IPs and static routes ─────────────────
    #
    # Same-subnet links      → container's primary IP on its first interface.
    # Router↔router WAN link → auto-assigned /30 PtP IPs from 10.255.0.0/24.
    #   Each side also gets a static route to the peer's subnet via the PtP IP.

    iface_ips:  dict[tuple[str, str], tuple[str, str]] = {}  # (cid, iface) → (ip, pfx)
    home_iface: dict[str, str] = {}                           # cid → home eth name
    ptp_routes: dict[str, list[tuple[str, str]]] = defaultdict(list)  # cid → [(dest, via)]
    ptp_seq:    list[int] = [0]

    def _next_ptp() -> tuple[str, str, str]:
        """Allocate next /30 PtP pair from 10.255.0.0/24."""
        n = ptp_seq[0]; ptp_seq[0] += 1
        b = 4 * n
        return f"10.255.0.{b + 1}", f"10.255.0.{b + 2}", "30"

    for from_id, fi, to_id, ti in link_registry:
        f_info   = container_info.get(from_id, {})
        t_info   = container_info.get(to_id,   {})
        f_subnet = f_info.get("subnet_cidr", "")
        t_subnet = t_info.get("subnet_cidr", "")
        f_type   = f_info.get("type", "")
        t_type   = t_info.get("type", "")

        if f_subnet != t_subnet and f_type in _ROUTER_TYPES and t_type in _ROUTER_TYPES:
            # Cross-subnet router↔router WAN link → auto PtP /30.
            from_ptp, to_ptp, ptp_pfx = _next_ptp()
            iface_ips[(from_id, fi)] = (from_ptp, ptp_pfx)
            iface_ips[(to_id,   ti)] = (to_ptp,   ptp_pfx)
            if t_subnet:
                ptp_routes[from_id].append((t_subnet, to_ptp))
            if f_subnet:
                ptp_routes[to_id].append((f_subnet, from_ptp))
        else:
            # Within-subnet (or non-router cross-subnet): set the home interface
            # IP once per container (first connection wins).
            if from_id not in home_iface and f_info.get("ip"):
                home_iface[from_id] = fi
                iface_ips[(from_id, fi)] = (f_info["ip"], f_info.get("prefix_len", "24"))
            if to_id not in home_iface and t_info.get("ip"):
                home_iface[to_id] = ti
                iface_ips[(to_id, ti)] = (t_info["ip"], t_info.get("prefix_len", "24"))

    # ── Step 4: Build node exec configs ─────────────────────────────────────

    for site in topology.get("sites", []):
        for subnet in site.get("subnets", []):
            for container in subnet.get("containers", []):
                cid    = container["id"]
                info   = container_info.get(cid, {})
                ctype  = info.get("type", "")
                ip     = info.get("ip", "")
                pfx    = info.get("prefix_len", "24")
                ifaces = sorted(container_ifaces.get(cid, set()), key=_eth_index)

                exec_cmds: list[str] = []

                if ctype in _SWITCH_TYPES:
                    # Use Linux bridge for switch nodes.
                    # If bridge creation/config fails on a host, fall back to
                    # placing the switch IP on the first data interface so nodes
                    # remain reachable on vanilla installs.
                    if ifaces:
                        first_iface = ifaces[0]
                        iface_list = " ".join(ifaces)
                        exec_cmds.append(
                            "sh -lc '"
                            f"for i in {iface_list}; do ip link set \"$i\" up >/dev/null 2>&1 || true; done; "
                            "ip link show br0 >/dev/null 2>&1 || ip link add br0 type bridge || true; "
                            f"for i in {iface_list}; do ip link set \"$i\" master br0 >/dev/null 2>&1 || true; done; "
                            "ip link set br0 up >/dev/null 2>&1 || true'"
                        )
                        if ip:
                            exec_cmds.append(
                                "sh -lc '"
                                f"ip addr replace {ip}/{pfx} dev br0 >/dev/null 2>&1 || "
                                f"ip addr replace {ip}/{pfx} dev {first_iface} >/dev/null 2>&1 || true'"
                            )

                elif ctype in _ROUTER_TYPES:
                    # FRR router: enable forwarding, assign IPs on all interfaces,
                    # then add static routes to directly reachable remote subnets.
                    exec_cmds.append("sysctl -w net.ipv4.ip_forward=1")
                    for iface in ifaces:
                        key = (cid, iface)
                        if key in iface_ips:
                            r_ip, r_pfx = iface_ips[key]
                            exec_cmds.append(f"ip addr add {r_ip}/{r_pfx} dev {iface}")
                    for dest_cidr, via_ip in ptp_routes.get(cid, []):
                        exec_cmds.append(f"ip route add {dest_cidr} via {via_ip}")

                else:
                    # Host (workstation / web-server / plc / etc.): assign IP on
                    # home interface, then add a default route via the effective
                    # gateway. A default route (rather than per-subnet routes) is
                    # required so that replies to cross-subnet pings sourced from
                    # router PtP addresses (10.255.0.x/30) are forwarded correctly —
                    # the host has no explicit route for those PtP ranges otherwise.
                    if ip and ifaces:
                        target_iface = home_iface.get(cid, ifaces[0])
                        exec_cmds.append(f"ip addr add {ip}/{pfx} dev {target_iface}")
                    gateway = info.get("gateway", "")
                    if gateway:
                        exec_cmds.append(f"ip route replace default via {gateway}")

                node_cfg: dict = {"kind": "linux", "image": _image_for(ctype)}
                if exec_cmds:
                    node_cfg["exec"] = exec_cmds
                nodes[cid] = node_cfg

    topo_name = topology.get("name") or "ae3gis-topology"
    clab = {
        "name": topo_name,
        "topology": {
            "nodes": nodes,
            "links": links,
        },
    }

    return yaml.dump(clab, default_flow_style=False, sort_keys=False)
