"""Convert a TopologyData dict into a ContainerLab YAML string."""

from __future__ import annotations

from collections import defaultdict

import yaml


def generate_clab_yaml(topology: dict) -> str:
    """Accept the raw topology dict (as stored in the DB) and return clab YAML.

    The topology dict matches the frontend TopologyData shape:
      { name?, sites[], siteConnections[] }
    """
    nodes: dict[str, dict] = {}
    links: list[dict] = []

    # Per-container interface counter for auto-assignment
    iface_counter: dict[str, int] = defaultdict(int)  # container_id → next eth index
    container_ifaces: dict[str, set[str]] = defaultdict(set)  # container_id → {eth1, …}

    def _next_iface(container_id: str) -> str:
        """Return next available ethN for a container."""
        iface_counter[container_id] += 1
        iface = f"eth{iface_counter[container_id]}"
        container_ifaces[container_id].add(iface)
        return iface

    def _resolve_conn(conn: dict, from_key: str = "from", to_key: str = "to") -> tuple[str | None, str, str | None, str]:
        """Resolve a connection's node IDs and interfaces, auto-assigning if missing."""
        from_id = conn.get("fromContainer") or conn.get(from_key)
        to_id = conn.get("toContainer") or conn.get(to_key)
        fi = conn.get("fromInterface") or (from_id and _next_iface(from_id))
        ti = conn.get("toInterface") or (to_id and _next_iface(to_id))
        # Track explicitly-provided interfaces too
        if from_id and conn.get("fromInterface"):
            container_ifaces[from_id].add(conn["fromInterface"])
            iface_counter[from_id] = max(iface_counter[from_id], _eth_index(conn["fromInterface"]))
        if to_id and conn.get("toInterface"):
            container_ifaces[to_id].add(conn["toInterface"])
            iface_counter[to_id] = max(iface_counter[to_id], _eth_index(conn["toInterface"]))
        return from_id, fi, to_id, ti

    # ── Collect all connections, resolve interfaces, build links ─────

    for site in topology.get("sites", []):
        for subnet in site.get("subnets", []):
            for conn in subnet.get("connections", []):
                from_id, fi, to_id, ti = _resolve_conn(conn)
                if from_id and to_id:
                    links.append({"endpoints": [f"{from_id}:{fi}", f"{to_id}:{ti}"]})

        for conn in site.get("subnetConnections", []):
            from_id, fi, to_id, ti = _resolve_conn(conn)
            if from_id and to_id:
                links.append({"endpoints": [f"{from_id}:{fi}", f"{to_id}:{ti}"]})

    for conn in topology.get("siteConnections", []):
        from_id, fi, to_id, ti = _resolve_conn(conn)
        if from_id and to_id:
            links.append({"endpoints": [f"{from_id}:{fi}", f"{to_id}:{ti}"]})

    # ── Build nodes with IP configuration ───────────────────────────

    for site in topology.get("sites", []):
        for subnet in site.get("subnets", []):
            cidr = subnet.get("cidr", "")
            prefix_len = cidr.split("/")[1] if "/" in cidr else "24"

            for container in subnet.get("containers", []):
                cid = container["id"]
                ctype = container.get("type", "")
                ip = container.get("ip", "")

                ifaces = sorted(container_ifaces.get(cid, set()), key=_eth_index)
                exec_cmds: list[str] = []

                if ctype == "switch" and len(ifaces) > 1:
                    # Create a bridge so the switch actually forwards traffic
                    exec_cmds.append("ip link add br0 type bridge")
                    for iface in ifaces:
                        exec_cmds.append(f"ip link set {iface} master br0")
                    exec_cmds.append("ip link set br0 up")
                    if ip:
                        exec_cmds.append(f"ip addr add {ip}/{prefix_len} dev br0")
                elif ip and ifaces:
                    # Assign IP on first data interface
                    exec_cmds.append(f"ip addr add {ip}/{prefix_len} dev {ifaces[0]}")

                if ctype in ("router", "firewall"):
                    exec_cmds.append("sysctl -w net.ipv4.ip_forward=1")

                # Always use alpine — topology "image" is descriptive metadata,
                # not a real pullable Docker image.
                node_cfg: dict = {"kind": "linux", "image": "alpine:latest"}
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


def _eth_index(iface: str) -> int:
    """Extract numeric index from interface name like 'eth1' → 1."""
    try:
        return int(iface.replace("eth", ""))
    except ValueError:
        return 0
