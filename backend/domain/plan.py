"""Topology -> engine-agnostic lab plan (domain logic, no engine imports).

This module owns the network *domain logic* (interface assignment, gateway
detection, point-to-point WAN links, static-route propagation, per-node boot
commands). It is deliberately free of any ContainerLab/Kathara specifics: it
emits an ordered set of nodes, collision domains, and shell startup commands
that any container orchestrator can realise. The startup commands are plain
Linux `ip`/`sysctl` invocations that work identically under any engine.

Ported from the original ContainerLab YAML generator, preserving its
multi-homing-aware behaviour, but decoupled from image lookup (now catalog
driven) and from clab node/exec schema.
"""

from __future__ import annotations

import ipaddress
import logging
import re
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from typing import Any

import catalog

log = logging.getLogger(__name__)

# Point-to-point WAN links between routers are numbered out of this /24.
_PTP_BASE = "10.255.0"


@dataclass
class Interface:
    """A single network interface on a node."""

    name: str  # e.g. "eth1"
    collision_domain: str  # the L2 segment (Kathara link) this attaches to
    ip: str | None = None  # host IP, no prefix
    prefix_len: str | None = None  # e.g. "24"

    @property
    def index(self) -> int:
        return _eth_index(self.name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def safe_name(node_id: str) -> str:
    """Sanitize a node id into a name valid for Kathara/ContainerLab (alnum + underscore)."""
    name = re.sub(r"[^a-z0-9_]+", "_", (node_id or "").lower()).strip("_")
    return name or "node"


@dataclass
class NodePlan:
    """A container to instantiate, with its interfaces and boot commands."""

    id: str
    name: str
    type: str
    role: str  # router | switch | host
    image: str
    interfaces: list[Interface] = field(default_factory=list)
    startup: list[str] = field(default_factory=list)

    @property
    def machine_name(self) -> str:
        return safe_name(self.id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "machine_name": self.machine_name,
            "type": self.type,
            "role": self.role,
            "image": self.image,
            "interfaces": [i.to_dict() for i in self.interfaces],
            "startup": list(self.startup),
        }


@dataclass
class LabPlan:
    """The full, engine-agnostic realisation of a topology."""

    name: str
    nodes: list[NodePlan] = field(default_factory=list)

    @property
    def collision_domains(self) -> list[str]:
        seen: dict[str, None] = {}
        for node in self.nodes:
            for iface in node.interfaces:
                seen.setdefault(iface.collision_domain, None)
        return list(seen)

    def links(self) -> list[dict[str, Any]]:
        """Collision domains with their endpoints (node id + interface)."""
        by_cd: dict[str, list[dict[str, Any]]] = {}
        for node in self.nodes:
            for iface in node.interfaces:
                by_cd.setdefault(iface.collision_domain, []).append(
                    {
                        "node": node.id,
                        "machine_name": node.machine_name,
                        "interface": iface.name,
                        "ip": iface.ip,
                        "prefix_len": iface.prefix_len,
                    }
                )
        return [{"collision_domain": cd, "endpoints": eps} for cd, eps in by_cd.items()]

    def images(self) -> list[str]:
        seen: dict[str, None] = {}
        for n in self.nodes:
            seen.setdefault(n.image, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "nodes": [n.to_dict() for n in self.nodes],
            "collision_domains": self.collision_domains,
            "links": self.links(),
            "images": self.images(),
        }


def _eth_index(iface: str) -> int:
    try:
        return int(iface.replace("eth", ""))
    except ValueError:
        return 0


def _gateway_belongs_to_subnet(gateway: str, cidr: str) -> bool:
    if not gateway or not cidr:
        return False
    try:
        return ipaddress.ip_address(gateway) in ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return False


def build_lab_plan(topology: dict, lab_name: str, *, iface_base: int = 0) -> LabPlan:
    """Convert a TopologyData dict into a LabPlan.

    Cross-subnet routing is automatic: connections that reference subnet or site
    IDs are resolved to the gateway router of each side; router<->router links
    with no subnet context get a /30 PtP address pair and matching static
    routes; hosts get a default route via their subnet gateway.

    ``iface_base`` is the first interface number: Kathara wants eth0, ContainerLab
    reserves eth0 for management and wants eth1.
    """
    # Roles are resolved from the catalog. Unknown types default to "host".
    container_type: dict[str, str] = {}
    container_role: dict[str, str] = {}
    container_name: dict[str, str] = {}
    container_image: dict[str, str] = {}
    container_memberships: dict[str, list[dict]] = defaultdict(list)
    subnet_id_containers: dict[str, list] = {}
    site_id_subnets: dict[str, list] = {}

    def _is_router(cid: str) -> bool:
        return container_role.get(cid) == "router"

    # ── Step 1: container + subnet metadata (multi-homing aware) ──────────
    for site in topology.get("sites", []):
        site_id = site.get("id", "")
        if site_id:
            site_id_subnets[site_id] = site.get("subnets", [])

        for subnet in site.get("subnets", []):
            sid = subnet.get("id", "")
            cidr = subnet.get("cidr", "")
            gateway = subnet.get("gateway") or ""
            pfx = cidr.split("/")[1] if "/" in cidr else "24"
            containers = subnet.get("containers", [])

            if gateway and not _gateway_belongs_to_subnet(gateway, cidr):
                log.warning("Subnet %s gateway %s outside %s; auto-detecting", sid, gateway, cidr)
                gateway = ""

            if not gateway:
                for c in containers:
                    if catalog.role_for(
                        c.get("type", "")
                    ) == "router" and _gateway_belongs_to_subnet(c.get("ip", ""), cidr):
                        gateway = c.get("ip", "")
                        break

            if sid:
                subnet_id_containers[sid] = containers

            for c in containers:
                cid = c["id"]
                ctype = c.get("type", "")
                container_type.setdefault(cid, ctype)
                container_role.setdefault(cid, catalog.role_for(ctype))
                container_name.setdefault(cid, c.get("name") or cid)
                container_image.setdefault(cid, catalog.resolve_image(ctype, c.get("image")))
                container_memberships[cid].append(
                    {
                        "subnet_id": sid,
                        "cidr": cidr,
                        "ip": c.get("ip", ""),
                        "prefix_len": pfx,
                        "gateway": gateway,
                    }
                )

    def _primary(cid: str) -> dict:
        return (container_memberships.get(cid) or [{}])[0]

    def _membership_for_subnet(cid: str, sid: str | None) -> dict | None:
        if not sid:
            return None
        for m in container_memberships.get(cid, []):
            if m["subnet_id"] == sid:
                return m
        return None

    container_info: dict[str, dict] = {
        cid: {"type": container_type[cid], **_primary(cid)} for cid in container_memberships
    }

    # ── Gateway-router resolution (subnet_id / site_id -> router container) ──
    def _find_gateway_router(containers: list[dict], sid: str | None = None) -> str | None:
        best = fallback = None
        for c in containers:
            cid = c["id"]
            if not _is_router(cid):
                continue
            m = _membership_for_subnet(cid, sid) or _primary(cid)
            if c.get("ip") == m.get("gateway") and not best:
                best = cid
            if not fallback:
                fallback = cid
        return best or fallback

    gateway_router_map: dict[str, str] = {}
    site_gateway_router_map: dict[str, str] = {}
    for sid, containers in subnet_id_containers.items():
        gw = _find_gateway_router(containers, sid)
        if gw:
            gateway_router_map[sid] = gw
    for site_id, subnets in site_id_subnets.items():
        for subnet in subnets:
            gw = _find_gateway_router(subnet.get("containers", []), subnet.get("id"))
            if gw:
                site_gateway_router_map[site_id] = gw
                break

    def _resolve_endpoint(raw_id: str | None) -> str | None:
        if not raw_id:
            return None
        if raw_id in container_memberships:
            return raw_id
        return gateway_router_map.get(raw_id) or site_gateway_router_map.get(raw_id)

    # ── Step 2: resolve connections, auto-assign interfaces + collision domains ──
    iface_counter: dict[str, int] = defaultdict(int)
    container_ifaces: dict[str, set[str]] = defaultdict(set)

    def _next_iface(cid: str) -> str:
        iface_counter[cid] += 1
        iface = f"eth{iface_counter[cid]}"
        container_ifaces[cid].add(iface)
        return iface

    def _preregister(conn: dict) -> None:
        from_id = _resolve_endpoint(conn.get("fromContainer") or conn.get("from")) or (
            conn.get("fromContainer") or conn.get("from")
        )
        to_id = _resolve_endpoint(conn.get("toContainer") or conn.get("to")) or (
            conn.get("toContainer") or conn.get("to")
        )
        if from_id and conn.get("fromInterface"):
            iface_counter[from_id] = max(iface_counter[from_id], _eth_index(conn["fromInterface"]))
            container_ifaces[from_id].add(conn["fromInterface"])
        if to_id and conn.get("toInterface"):
            iface_counter[to_id] = max(iface_counter[to_id], _eth_index(conn["toInterface"]))
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
        to_id = conn.get("toContainer") or conn.get("to")
        fi = conn.get("fromInterface") or (from_id and _next_iface(from_id))
        ti = conn.get("toInterface") or (to_id and _next_iface(to_id))
        if from_id and conn.get("fromInterface"):
            container_ifaces[from_id].add(conn["fromInterface"])
            iface_counter[from_id] = max(iface_counter[from_id], _eth_index(conn["fromInterface"]))
        if to_id and conn.get("toInterface"):
            container_ifaces[to_id].add(conn["toInterface"])
            iface_counter[to_id] = max(iface_counter[to_id], _eth_index(conn["toInterface"]))
        return from_id, fi, to_id, ti

    # (from_id, from_iface, to_id, to_iface, subnet_id, collision_domain)
    link_registry: list[tuple[str, str, str, str, str | None, str]] = []
    cd_seq = [0]

    def _add_link(conn: dict, subnet_id: str | None) -> None:
        from_id = _resolve_endpoint(conn.get("fromContainer") or conn.get("from"))
        to_id = _resolve_endpoint(conn.get("toContainer") or conn.get("to"))
        if not from_id or not to_id:
            return
        if from_id not in container_memberships or to_id not in container_memberships:
            return
        resolved = {**conn, "fromContainer": from_id, "toContainer": to_id}
        _, fi, _, ti = _resolve_conn(resolved)
        cd = f"cd{cd_seq[0]}"
        cd_seq[0] += 1
        link_registry.append((from_id, fi, to_id, ti, subnet_id, cd))

    for site in topology.get("sites", []):
        for subnet in site.get("subnets", []):
            for conn in subnet.get("connections", []):
                _add_link(conn, subnet.get("id"))
        for conn in site.get("subnetConnections", []):
            _add_link(conn, None)
    for conn in topology.get("siteConnections", []):
        _add_link(conn, None)

    # ── Step 3: per-interface IPs + static routes ─────────────────────────
    iface_ips: dict[tuple[str, str], tuple[str, str]] = {}
    iface_cd: dict[tuple[str, str], str] = {}
    home_iface: dict[str, str] = {}
    router_links: dict[str, list[tuple[str, str]]] = defaultdict(list)
    router_networks: dict[str, set[str]] = defaultdict(set)
    ptp_seq = [0]

    def _next_ptp() -> tuple[str, str, str]:
        n = ptp_seq[0]
        ptp_seq[0] += 1
        b = 4 * n
        return f"{_PTP_BASE}.{b + 1}", f"{_PTP_BASE}.{b + 2}", "30"

    assigned_iface_for_subnet: dict[tuple[str, str], str] = {}

    for from_id, fi, to_id, ti, subnet_id, cd in link_registry:
        iface_cd[(from_id, fi)] = cd
        iface_cd[(to_id, ti)] = cd
        f_mem = _membership_for_subnet(from_id, subnet_id)
        t_mem = _membership_for_subnet(to_id, subnet_id)

        if subnet_id and (f_mem or t_mem):
            if f_mem:
                iface = assigned_iface_for_subnet.setdefault((from_id, subnet_id), fi)
                iface_ips[(from_id, iface)] = (f_mem["ip"], f_mem["prefix_len"])
                home_iface.setdefault(from_id, iface)
            if t_mem:
                iface = assigned_iface_for_subnet.setdefault((to_id, subnet_id), ti)
                iface_ips[(to_id, iface)] = (t_mem["ip"], t_mem["prefix_len"])
                home_iface.setdefault(to_id, iface)
        else:
            from_ptp, to_ptp, ptp_pfx = _next_ptp()
            ptp_net = str(ipaddress.ip_network(f"{from_ptp}/{ptp_pfx}", strict=False))
            iface_ips[(from_id, fi)] = (from_ptp, ptp_pfx)
            iface_ips[(to_id, ti)] = (to_ptp, ptp_pfx)
            router_links[from_id].append((to_id, to_ptp))
            router_links[to_id].append((from_id, from_ptp))
            router_networks[from_id].add(ptp_net)
            router_networks[to_id].add(ptp_net)

    # Router adjacency via shared subnet membership (multi-legged firewalls).
    router_subnets: dict[str, set[str]] = defaultdict(set)
    for cid, memberships in container_memberships.items():
        if not _is_router(cid):
            continue
        for m in memberships:
            if m["cidr"]:
                router_networks[cid].add(m["cidr"])
                router_subnets[cid].add(m["cidr"])

    routers_by_subnet: dict[str, list[str]] = defaultdict(list)
    for cid, cidrs in router_subnets.items():
        for cidr in cidrs:
            routers_by_subnet[cidr].append(cid)
    for cidr, cids in routers_by_subnet.items():
        for i, cid_a in enumerate(cids):
            for cid_b in cids[i + 1 :]:
                ip_a = next(
                    (m["ip"] for m in container_memberships[cid_a] if m["cidr"] == cidr), None
                )
                ip_b = next(
                    (m["ip"] for m in container_memberships[cid_b] if m["cidr"] == cidr), None
                )
                if ip_a and ip_b:
                    router_links[cid_a].append((cid_b, ip_b))
                    router_links[cid_b].append((cid_a, ip_a))

    # BFS static-route propagation: every router to every remote subnet.
    router_static_routes: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for src_router in router_subnets:
        first_hop_via: dict[str, str] = {}
        seen = {src_router}
        queue = deque([(src_router, None)])
        while queue:
            current_router, current_via = queue.popleft()
            for neighbor, neighbor_via in router_links.get(current_router, []):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                first_hop_via[neighbor] = current_via or neighbor_via
                queue.append((neighbor, first_hop_via[neighbor]))
        added: set[tuple[str, str]] = set()
        directly_connected = router_networks.get(src_router, set())
        for dst_router, via_ip in first_hop_via.items():
            for dst_network in router_networks.get(dst_router, set()):
                route = (dst_network, via_ip)
                if not dst_network or dst_network in directly_connected or route in added:
                    continue
                router_static_routes[src_router].append(route)
                added.add(route)

    # ── Step 4: assemble node plans with role-based startup commands ──────
    #
    # Interfaces are renumbered to a contiguous, 0-based sequence per node.
    # The topology model may leave gaps or start at eth1 (the old ContainerLab
    # convention reserved eth0 for management), but engines like Kathara require
    # each device's interfaces to be sequential from eth0. Renumbering here —
    # before startup commands are generated — keeps the device references in
    # those commands consistent with the attached collision domains.
    plan = LabPlan(name=lab_name)
    for cid in container_memberships:
        info = container_info.get(cid, {})
        ctype = container_type.get(cid, "")
        role = container_role.get(cid, "host")
        ip = info.get("ip", "")
        pfx = info.get("prefix_len", "24")

        old_ifaces = sorted(container_ifaces.get(cid, set()), key=_eth_index)
        remap = {old: f"eth{i + iface_base}" for i, old in enumerate(old_ifaces)}

        interfaces = [
            Interface(
                name=remap[old],
                collision_domain=iface_cd.get((cid, old), f"cd_{cid}_{old}"),
                ip=iface_ips.get((cid, old), (None, None))[0],
                prefix_len=iface_ips.get((cid, old), (None, None))[1],
            )
            for old in old_ifaces
        ]

        new_ifaces = [remap[o] for o in old_ifaces]
        new_iface_ips = {
            remap[k[1]]: v for k, v in iface_ips.items() if k[0] == cid and k[1] in remap
        }
        old_home = home_iface.get(cid)
        new_home = (
            remap.get(old_home) if old_home in remap else (new_ifaces[0] if new_ifaces else None)
        )

        startup = _startup_commands(
            role=role,
            ifaces=new_ifaces,
            ip=ip,
            pfx=pfx,
            gateway=info.get("gateway", ""),
            home=new_home,
            iface_ips=new_iface_ips,
            static_routes=router_static_routes.get(cid, []),
        )

        plan.nodes.append(
            NodePlan(
                id=cid,
                name=container_name.get(cid, cid),
                type=ctype,
                role=role,
                image=container_image.get(cid, catalog.default_image_for(ctype)),
                interfaces=interfaces,
                startup=startup,
            )
        )
    return plan


def _startup_commands(
    *,
    role: str,
    ifaces: list[str],
    ip: str,
    pfx: str,
    gateway: str,
    home: str | None,
    iface_ips: dict[str, tuple[str, str]],
    static_routes: list[tuple[str, str]],
) -> list[str]:
    """Return the ordered Linux boot commands for a node.

    These run inside the container at startup (engine `exec`). They are plain
    iproute2/sysctl commands, portable across orchestrators and architectures.
    """
    cmds: list[str] = []

    if role == "switch":
        if ifaces:
            iface_list = " ".join(ifaces)
            first = ifaces[0]
            cmds.append(
                f'for i in {iface_list}; do ip link set "$i" up 2>/dev/null || true; done; '
                "ip link show br0 >/dev/null 2>&1 || ip link add br0 type bridge || true; "
                f'for i in {iface_list}; do ip link set "$i" master br0 2>/dev/null || true; done; '
                "ip link set br0 up 2>/dev/null || true"
            )
            if ip:
                cmds.append(
                    f"ip addr replace {ip}/{pfx} dev br0 2>/dev/null || "
                    f"ip addr replace {ip}/{pfx} dev {first} 2>/dev/null || true"
                )
        if gateway:
            cmds.append(f"ip route replace default via {gateway}")

    elif role == "router":
        cmds.append("sysctl -w net.ipv4.ip_forward=1")
        for iface in ifaces:
            r_ip, r_pfx = iface_ips.get(iface, (None, None))
            if r_ip:
                cmds.append(f"ip addr add {r_ip}/{r_pfx} dev {iface}")
        for dest_cidr, via_ip in static_routes:
            cmds.append(f"ip route add {dest_cidr} via {via_ip}")

    else:  # host
        if ip and ifaces:
            target = home or ifaces[0]
            cmds.append(f"ip addr add {ip}/{pfx} dev {target}")
        if gateway:
            cmds.append(f"ip route replace default via {gateway}")

    return cmds
