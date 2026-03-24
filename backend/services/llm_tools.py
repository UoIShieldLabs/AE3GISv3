"""Tool definitions and executors for the AI assistant.

Each tool has:
  - A schema (OpenAI function-calling format) for the LLM
  - An executor function that runs the action and returns a result string
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from models import Topology
from services.clab_manager import _docker_exec, deployment_name

log = logging.getLogger(__name__)


# ── Tool schemas (OpenAI function-calling format) ──────────────────

STUDENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_topology_summary",
            "description": "Get a summary of the current topology: sites, subnets, containers, and their IPs/connections.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_container_details",
            "description": "Get detailed info about a specific container: type, IP, interfaces, connections, and status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_name": {
                        "type": "string",
                        "description": "The name of the container to look up.",
                    },
                },
                "required": ["container_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_routing_path",
            "description": "Analyze the expected network path between two containers, including subnets traversed, gateways, and routers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_container": {"type": "string", "description": "Source container name."},
                    "to_container": {"type": "string", "description": "Destination container name."},
                },
                "required": ["from_container", "to_container"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a command on a deployed container. For students: only safe read-only commands (ping, ip, traceroute, nslookup, arp, cat, ifconfig, route, ss, netstat). For instructors: any command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_name": {"type": "string", "description": "Container name to run the command on."},
                    "command": {"type": "string", "description": "The command to run (e.g. 'ping -c 3 10.0.1.2', 'ip route', 'ip addr')."},
                },
                "required": ["container_name", "command"],
            },
        },
    },
]

INSTRUCTOR_TOOLS = STUDENT_TOOLS + [
    {
        "type": "function",
        "function": {
            "name": "describe_topology",
            "description": "Generate a natural language description of the entire topology or a specific site/subnet, suitable for documentation or student instructions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["full", "site", "subnet"],
                        "description": "What scope to describe.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Site or subnet name (required if scope is 'site' or 'subnet').",
                    },
                },
                "required": ["scope"],
            },
        },
    },
]


# ── Tool executors ─────────────────────────────────────────────────

# Safe commands students can run
_SAFE_COMMANDS = {"ping", "ip", "traceroute", "nslookup", "arp", "cat", "ifconfig", "route", "ss", "netstat"}


def _normalize(s: str) -> str:
    """Normalize a string for fuzzy matching: lowercase, strip separators."""
    return re.sub(r'[\s_\-]+', '', s.lower())


def _word_set(s: str) -> set[str]:
    """Split a string into a set of lowercase words (split on spaces, hyphens, underscores)."""
    return set(re.split(r'[\s_\-]+', s.lower()))


def _all_containers(topo_data: dict) -> list[tuple[dict, dict, dict]]:
    """Return all (container, subnet, site) tuples."""
    results = []
    for site in topo_data.get("sites", []):
        for subnet in site.get("subnets", []):
            for container in subnet.get("containers", []):
                results.append((container, subnet, site))
    return results


def _container_list_str(topo_data: dict) -> str:
    """Format available containers for error messages."""
    entries = []
    for c, sub, site in _all_containers(topo_data):
        entries.append(f'  "{c["name"]}" (id: {c["id"]}, ip: {c["ip"]})')
    return "\n".join(entries) if entries else "  (no containers)"


def _find_container(topo_data: dict, name_or_id: str) -> tuple[dict | None, dict | None, dict | None]:
    """Find a container by name or ID with fuzzy matching.

    Matching priority:
      1. Exact ID match
      2. Exact name match (case-insensitive)
      3. Normalized match (ignoring spaces/hyphens/underscores)
      4. Substring match (input is contained in name, or name is contained in input)
      5. Word overlap match (most words in common wins)
    """
    all_c = _all_containers(topo_data)
    if not all_c:
        return None, None, None

    query = name_or_id.strip()
    query_lower = query.lower()
    query_norm = _normalize(query)
    query_words = _word_set(query)

    # 1. Exact ID match
    for container, subnet, site in all_c:
        if container["id"] == query:
            return container, subnet, site

    # 2. Exact name match (case-insensitive)
    for container, subnet, site in all_c:
        if container["name"].lower() == query_lower:
            return container, subnet, site

    # 3. Normalized match (ignore separators)
    for container, subnet, site in all_c:
        if _normalize(container["name"]) == query_norm or _normalize(container["id"]) == query_norm:
            return container, subnet, site

    # 4. Substring match
    substring_matches = []
    for container, subnet, site in all_c:
        name_lower = container["name"].lower()
        id_lower = container["id"].lower()
        if query_lower in name_lower or name_lower in query_lower:
            substring_matches.append((container, subnet, site))
        elif query_lower in id_lower or id_lower in query_lower:
            substring_matches.append((container, subnet, site))
    if len(substring_matches) == 1:
        return substring_matches[0]

    # 5. Word overlap (best match by number of shared words)
    best_match = None
    best_score = 0
    for container, subnet, site in all_c:
        name_words = _word_set(container["name"])
        overlap = len(query_words & name_words)
        if overlap > best_score:
            best_score = overlap
            best_match = (container, subnet, site)
    if best_score > 0 and best_match:
        return best_match

    return None, None, None


def _not_found_msg(name: str, topo_data: dict) -> str:
    """Build a helpful 'not found' error with the list of available containers."""
    return (
        f"Container '{name}' not found. Available containers:\n"
        + _container_list_str(topo_data)
        + "\nPlease use one of the exact names listed above."
    )


def _docker_name(topo_id: str, topo_data: dict, container_id: str) -> str:
    dep_name = deployment_name(topo_id, topo_data)
    return f"clab-{dep_name}-{container_id}"


async def exec_get_topology_summary(topo_data: dict, **_: Any) -> str:
    lines = []
    name = topo_data.get("name", "Unnamed")
    sites = topo_data.get("sites", [])
    lines.append(f"Topology: {name}")
    lines.append(f"Sites: {len(sites)}")

    for site in sites:
        lines.append(f"\n## Site: {site['name']} ({site.get('location', 'N/A')})")
        for subnet in site.get("subnets", []):
            lines.append(f"  Subnet: {subnet['name']} ({subnet['cidr']}), gateway: {subnet.get('gateway', 'auto')}")
            for c in subnet.get("containers", []):
                status = c.get("status", "unknown")
                lines.append(f"    - {c['name']} ({c['type']}) IP: {c['ip']} [{status}]")
        if site.get("subnetConnections"):
            lines.append(f"  Inter-subnet connections: {len(site['subnetConnections'])}")

    site_conns = topo_data.get("siteConnections", [])
    if site_conns:
        lines.append(f"\nInter-site connections: {len(site_conns)}")

    return "\n".join(lines)


async def exec_get_container_details(topo_data: dict, container_name: str, **_: Any) -> str:
    container, subnet, site = _find_container(topo_data, container_name)
    if not container:
        return _not_found_msg(container_name, topo_data)

    lines = [
        f"Name: {container['name']}",
        f"ID: {container['id']}",
        f"Type: {container['type']}",
        f"IP: {container['ip']}",
        f"Status: {container.get('status', 'unknown')}",
        f"Site: {site['name']}",
        f"Subnet: {subnet['name']} ({subnet['cidr']})",
        f"Gateway: {subnet.get('gateway', 'auto')}",
    ]
    if container.get("image"):
        lines.append(f"Image: {container['image']}")

    # Find connections involving this container
    conns = []
    for conn in subnet.get("connections", []):
        if conn.get("from") == container["id"] or conn.get("to") == container["id"]:
            conns.append(conn)
    if conns:
        lines.append("Connections:")
        for conn in conns:
            peer = conn["to"] if conn.get("from") == container["id"] else conn.get("from")
            peer_c, _, _ = _find_container(topo_data, peer)
            peer_name = peer_c["name"] if peer_c else peer
            iface_from = conn.get("fromInterface", "auto")
            iface_to = conn.get("toInterface", "auto")
            lines.append(f"  {container['name']}({iface_from}) <-> {peer_name}({iface_to})")

    return "\n".join(lines)


async def exec_get_routing_path(topo_data: dict, from_container: str, to_container: str, **_: Any) -> str:
    src, src_sub, src_site = _find_container(topo_data, from_container)
    dst, dst_sub, dst_site = _find_container(topo_data, to_container)

    if not src:
        return _not_found_msg(from_container, topo_data)
    if not dst:
        return _not_found_msg(to_container, topo_data)

    lines = [f"Path analysis: {src['name']} ({src['ip']}) -> {dst['name']} ({dst['ip']})"]

    if src_sub["id"] == dst_sub["id"]:
        lines.append(f"Same subnet ({src_sub['name']} - {src_sub['cidr']}): direct L2 path via switch.")
    elif src_site["id"] == dst_site["id"]:
        lines.append(f"Same site ({src_site['name']}), different subnets:")
        lines.append(f"  Source subnet: {src_sub['name']} ({src_sub['cidr']})")
        lines.append(f"  Dest subnet: {dst_sub['name']} ({dst_sub['cidr']})")
        lines.append(f"  Traffic flows: {src['name']} -> subnet gateway -> inter-subnet router -> dest gateway -> {dst['name']}")
    else:
        lines.append(f"Cross-site path:")
        lines.append(f"  Source: {src_site['name']}/{src_sub['name']} ({src_sub['cidr']})")
        lines.append(f"  Dest: {dst_site['name']}/{dst_sub['name']} ({dst_sub['cidr']})")
        lines.append(f"  Traffic flows through site gateways with point-to-point links.")

    # Check for firewalls in path
    for site in [src_site, dst_site]:
        for subnet in site.get("subnets", []):
            for c in subnet.get("containers", []):
                if c["type"] == "firewall":
                    lines.append(f"  Note: Firewall '{c['name']}' present in {site['name']}/{subnet['name']} — may filter traffic.")

    return "\n".join(lines)


async def exec_run_command(
    topo_data: dict, topo_id: str, container_name: str, command: str,
    is_instructor: bool = False, **_: Any,
) -> str:
    """Unified command executor. Students are restricted to safe commands; instructors can run anything."""
    container, _, _ = _find_container(topo_data, container_name)
    if not container:
        return _not_found_msg(container_name, topo_data)

    # Validate command safety for students
    if not is_instructor:
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return "Empty command."
        base_cmd = cmd_parts[0]
        if base_cmd not in _SAFE_COMMANDS:
            return f"Command '{base_cmd}' is not allowed. Safe commands: {', '.join(sorted(_SAFE_COMMANDS))}"

    docker_name = _docker_name(topo_id, topo_data, container["id"])
    try:
        rc, stdout, stderr = await _docker_exec(docker_name, ["sh", "-c", command])
        output = stdout
        if stderr:
            output += f"\n[stderr]: {stderr}"
        if rc != 0:
            output += f"\n[exit code: {rc}]"
        return output[:4000]
    except Exception as e:
        return f"Failed to execute: {e}"


# Keep old executor names as aliases for backwards compatibility with ai.py security checks
async def exec_run_diagnostic(topo_data: dict, topo_id: str, container_name: str, command: str, **kw: Any) -> str:
    return await exec_run_command(topo_data=topo_data, topo_id=topo_id, container_name=container_name, command=command, is_instructor=False, **kw)


async def exec_exec_command(topo_data: dict, topo_id: str, container_name: str, command: str, **kw: Any) -> str:
    return await exec_run_command(topo_data=topo_data, topo_id=topo_id, container_name=container_name, command=command, is_instructor=True, **kw)


async def exec_describe_topology(topo_data: dict, scope: str, name: str | None = None, **_: Any) -> str:
    # Just return structured data — the LLM will generate the natural language description
    if scope == "full":
        return await exec_get_topology_summary(topo_data)
    elif scope == "site":
        for site in topo_data.get("sites", []):
            if site["name"].lower() == (name or "").lower():
                return json.dumps(site, indent=2)
        return f"Site '{name}' not found."
    elif scope == "subnet":
        for site in topo_data.get("sites", []):
            for subnet in site.get("subnets", []):
                if subnet["name"].lower() == (name or "").lower():
                    return json.dumps(subnet, indent=2)
        return f"Subnet '{name}' not found."
    return "Invalid scope."


# ── Executor dispatch ──────────────────────────────────────────────

EXECUTORS = {
    "get_topology_summary": exec_get_topology_summary,
    "get_container_details": exec_get_container_details,
    "get_routing_path": exec_get_routing_path,
    "run_command": exec_run_command,
    # Legacy names — still referenced by text-tool-call extraction and security checks
    "run_diagnostic": exec_run_diagnostic,
    "exec_command": exec_exec_command,
    "describe_topology": exec_describe_topology,
}


async def execute_tool(
    tool_name: str,
    args: dict[str, Any],
    topo_data: dict,
    topo_id: str,
    is_instructor: bool = False,
) -> str:
    executor = EXECUTORS.get(tool_name)
    if not executor:
        return f"Unknown tool: {tool_name}"
    # Pass is_instructor for run_command's safety check
    if tool_name == "run_command":
        args["is_instructor"] = is_instructor
    return await executor(topo_data=topo_data, topo_id=topo_id, **args)
