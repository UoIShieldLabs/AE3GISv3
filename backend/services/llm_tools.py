"""Tool definitions and executors for the AI assistant.

Each tool has:
  - A schema (OpenAI function-calling format) for the LLM
  - An executor function that runs the action and returns a result string
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from models import Topology
from services.clab_manager import _docker_exec, deployment_name

log = logging.getLogger(__name__)

# ── Pending topology store (confirmation flow) ────────────────────

_pending_topologies: dict[str, dict] = {}
_PENDING_TTL = 1800  # 30 minutes


def _cleanup_pending():
    """Remove expired pending topologies."""
    now = time.time()
    expired = [k for k, v in _pending_topologies.items() if now - v["created_at"] > _PENDING_TTL]
    for k in expired:
        del _pending_topologies[k]


# ── Topology generation system prompt ─────────────────────────────

TOPOLOGY_GEN_SYSTEM_PROMPT = """You are a network topology JSON generator for AE3GIS. Given a description, produce a valid TopologyData JSON object.

## Schema

TopologyData:
  name: string (optional)
  sites: Site[]
  siteConnections: Connection[]  (connections between sites using gateway router IDs)

Site:
  id: string (kebab-case, unique)
  name: string
  location: string
  position: { x: number, y: number }  (space sites ~300px apart)
  subnets: Subnet[]
  subnetConnections: Connection[]  (connections between subnets within the site, using router IDs)

Subnet:
  id: string (kebab-case, unique)
  name: string
  cidr: string (e.g. "10.0.1.0/24")
  gateway: string (IP of the subnet's router)
  containers: Container[]
  connections: Connection[]

Container:
  id: string (kebab-case, unique across entire topology)
  name: string (human-readable)
  type: one of "web-server", "file-server", "plc", "firewall", "switch", "router", "workstation"
  ip: string (must be within subnet CIDR)

Connection (intra-subnet only — inside subnet.connections):
  from: string (container ID)
  to: string (container ID)
  fromInterface: string (e.g. "eth1")
  toInterface: string (e.g. "eth1")

SubnetConnection / SiteConnection (cross-subnet or cross-site):
  from: string (router container ID from one subnet/site)
  to: string (router container ID from the other subnet/site)
  NOTE: Do NOT include fromInterface or toInterface — the system auto-assigns them.

## Rules
1. Every subnet MUST have exactly one router and one switch.
2. The router and switch must be connected: router eth1 <-> switch eth1.
3. All other containers connect to the switch: switch ethN <-> container eth1.
4. Gateway IP is the router's IP (typically .1 in the subnet).
5. Container IDs must be globally unique across the entire topology.
6. Use sequential interface names on the switch: eth1, eth2, eth3, etc.
7. For inter-subnet connections within a site, use subnetConnections with router IDs from each subnet. Do NOT specify interfaces.
8. For inter-site connections, use siteConnections with gateway router IDs from each site. Do NOT specify interfaces.
9. Use realistic CIDR ranges (10.x.x.0/24). Different subnets must use different ranges.
10. Container types: router and firewall get frrouting/frr:latest; everything else gets alpine:latest.
11. CRITICAL: Only specify fromInterface/toInterface inside subnet.connections (intra-subnet). NEVER on subnetConnections or siteConnections.

## Example (two subnets in one site)

{
  "sites": [{
    "id": "office", "name": "Office", "location": "HQ", "position": {"x": 100, "y": 100},
    "subnets": [
      {
        "id": "office-lan", "name": "Office LAN", "cidr": "10.0.1.0/24", "gateway": "10.0.1.1",
        "containers": [
          {"id": "lan-router", "name": "LAN Router", "type": "router", "ip": "10.0.1.1"},
          {"id": "lan-switch", "name": "LAN Switch", "type": "switch", "ip": "10.0.1.2"},
          {"id": "ws1", "name": "Workstation 1", "type": "workstation", "ip": "10.0.1.100"}
        ],
        "connections": [
          {"from": "lan-router", "to": "lan-switch", "fromInterface": "eth1", "toInterface": "eth1"},
          {"from": "lan-switch", "to": "ws1", "fromInterface": "eth2", "toInterface": "eth1"}
        ]
      },
      {
        "id": "office-dmz", "name": "DMZ", "cidr": "10.0.2.0/24", "gateway": "10.0.2.1",
        "containers": [
          {"id": "dmz-router", "name": "DMZ Router", "type": "router", "ip": "10.0.2.1"},
          {"id": "dmz-switch", "name": "DMZ Switch", "type": "switch", "ip": "10.0.2.2"},
          {"id": "web1", "name": "Web Server", "type": "web-server", "ip": "10.0.2.100"}
        ],
        "connections": [
          {"from": "dmz-router", "to": "dmz-switch", "fromInterface": "eth1", "toInterface": "eth1"},
          {"from": "dmz-switch", "to": "web1", "fromInterface": "eth2", "toInterface": "eth1"}
        ]
      }
    ],
    "subnetConnections": [
      {"from": "lan-router", "to": "dmz-router"}
    ]
  }],
  "siteConnections": []
}

Respond with ONLY the JSON object. No markdown fences, no explanation, no comments."""


TOPOLOGY_MODIFY_SYSTEM_PROMPT = """You are a network topology JSON modifier for AE3GIS. You will receive the current topology JSON and modification instructions. Apply the requested changes and return the complete modified topology.

Follow the EXACT same schema and rules as topology generation:
- Every subnet needs exactly one router and one switch, wired together.
- All other containers connect to the switch.
- Container IDs must be globally unique (kebab-case).
- Use sequential eth interfaces on switches.
- Gateway IP is the router's IP.
- Different subnets must use different CIDR ranges.
- For inter-subnet connections, use subnetConnections with router IDs. Do NOT include interfaces.
- For inter-site connections, use siteConnections with gateway router IDs. Do NOT include interfaces.
- ONLY specify fromInterface/toInterface inside subnet.connections (intra-subnet links).

IMPORTANT:
- Preserve ALL existing parts of the topology that are not being changed.
- Keep existing container IDs, IPs, and connections intact unless the instructions say to change them.
- Only add, remove, or modify what the instructions specify.

Respond with ONLY the complete modified JSON object. No markdown fences, no explanation."""


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
    {
        "type": "function",
        "function": {
            "name": "generate_topology",
            "description": "Generate a brand new network topology from a natural language description. Returns a preview summary for the user to confirm before saving. Use this when the user wants to create a new topology from scratch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Detailed natural language description of the desired topology: sites, subnets, container types, and how they should be connected.",
                    },
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modify_topology",
            "description": "Modify the current topology based on natural language instructions. Returns a preview summary of the changes for the user to confirm before saving. Use this when the user wants to add, remove, or change parts of the existing topology.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instructions": {
                        "type": "string",
                        "description": "Natural language instructions describing what to change (e.g. 'add a DMZ subnet with a web server and firewall', 'remove the workstation from the corporate LAN', 'change the SCADA network CIDR to 10.0.20.0/24').",
                    },
                },
                "required": ["instructions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_topology",
            "description": "Save a previously generated or modified topology after the user confirms. ONLY call this after showing the user the preview and receiving their confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pending_id": {
                        "type": "string",
                        "description": "The pending topology ID returned by generate_topology or modify_topology.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Name for the topology. Required when saving a newly generated topology.",
                    },
                },
                "required": ["pending_id"],
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


async def _llm_generate_json(system_prompt: str, user_prompt: str) -> dict:
    """Make a secondary LLM call to generate topology JSON. Returns parsed dict or raises."""
    from services import llm_service

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = await llm_service.chat_completion(messages, tools=None, temperature=0.2)
    content = llm_service.extract_reply(response).get("content", "")

    # Strip markdown fences if present
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r'^```\w*\n?', '', content)
        content = re.sub(r'\n?```$', '', content)
        content = content.strip()

    return json.loads(content)


def _normalize_topology(data: dict) -> None:
    """Post-process LLM-generated topology to fix common issues.

    - Strips fromInterface/toInterface from subnetConnections and siteConnections
      (the clab_generator auto-assigns them; explicit ones cause duplicate endpoint errors).
    """
    for conn in data.get("siteConnections", []):
        conn.pop("fromInterface", None)
        conn.pop("toInterface", None)
    for site in data.get("sites", []):
        for conn in site.get("subnetConnections", []):
            conn.pop("fromInterface", None)
            conn.pop("toInterface", None)


def _validate_topology(data: dict) -> list[str]:
    """Validate topology structure. Returns list of error messages (empty = valid)."""
    errors = []
    if not isinstance(data.get("sites"), list):
        errors.append("Missing or invalid 'sites' array.")
        return errors

    container_ids: set[str] = set()
    for site in data["sites"]:
        if not site.get("id") or not site.get("name"):
            errors.append(f"Site missing id or name: {site}")
        for subnet in site.get("subnets", []):
            if not subnet.get("cidr"):
                errors.append(f"Subnet '{subnet.get('name', '?')}' missing CIDR.")
            routers = [c for c in subnet.get("containers", []) if c.get("type") == "router"]
            switches = [c for c in subnet.get("containers", []) if c.get("type") == "switch"]
            if not routers:
                errors.append(f"Subnet '{subnet.get('name', '?')}' has no router.")
            if not switches:
                errors.append(f"Subnet '{subnet.get('name', '?')}' has no switch.")
            for c in subnet.get("containers", []):
                cid = c.get("id", "")
                if cid in container_ids:
                    errors.append(f"Duplicate container ID: '{cid}'.")
                container_ids.add(cid)
                if not c.get("ip"):
                    errors.append(f"Container '{c.get('name', '?')}' missing IP.")
    return errors


def _summarize_topology(data: dict) -> str:
    """Generate a human-readable summary of a topology."""
    lines = []
    sites = data.get("sites", [])
    total_containers = 0
    for site in sites:
        subnet_descs = []
        for subnet in site.get("subnets", []):
            containers = subnet.get("containers", [])
            total_containers += len(containers)
            types = {}
            for c in containers:
                t = c.get("type", "unknown")
                types[t] = types.get(t, 0) + 1
            type_str = ", ".join(f"{v} {k}{'s' if v > 1 else ''}" for k, v in types.items())
            subnet_descs.append(f"  - {subnet['name']} ({subnet.get('cidr', '?')}): {type_str}")
        lines.append(f"Site: {site['name']} ({len(site.get('subnets', []))} subnet{'s' if len(site.get('subnets', [])) != 1 else ''})")
        lines.extend(subnet_descs)

    site_conns = data.get("siteConnections", [])
    summary = f"Total: {len(sites)} site{'s' if len(sites) != 1 else ''}, {total_containers} containers"
    if site_conns:
        summary += f", {len(site_conns)} inter-site connection{'s' if len(site_conns) != 1 else ''}"
    lines.insert(0, summary)
    return "\n".join(lines)


async def exec_generate_topology(topo_data: dict, description: str, **_: Any) -> str:
    """Generate a new topology from a natural language description."""
    _cleanup_pending()
    try:
        data = await _llm_generate_json(TOPOLOGY_GEN_SYSTEM_PROMPT, description)
    except json.JSONDecodeError as e:
        return f"Failed to parse generated topology JSON: {e}. Please try rephrasing."
    except Exception as e:
        return f"LLM generation failed: {e}"

    # Ensure top-level fields and normalize
    data.setdefault("siteConnections", [])
    for site in data.get("sites", []):
        site.setdefault("subnetConnections", [])
        site.setdefault("position", {"x": 100, "y": 100})
    _normalize_topology(data)

    errors = _validate_topology(data)
    if errors:
        return "Generated topology has validation errors:\n" + "\n".join(f"- {e}" for e in errors) + "\nPlease try with a more specific description."

    pending_id = uuid.uuid4().hex[:12]
    _pending_topologies[pending_id] = {
        "data": data,
        "mode": "create",
        "created_at": time.time(),
    }

    summary = _summarize_topology(data)
    return (
        f"Topology generated successfully. Preview:\n\n{summary}\n\n"
        f"Pending ID: {pending_id}\n"
        f"Ask the user to confirm before calling save_topology."
    )


async def exec_modify_topology(topo_data: dict, instructions: str, **_: Any) -> str:
    """Modify the current topology based on natural language instructions."""
    _cleanup_pending()
    current_json = json.dumps(topo_data, indent=2)
    user_prompt = (
        f"## Current Topology\n```json\n{current_json}\n```\n\n"
        f"## Modification Instructions\n{instructions}"
    )

    try:
        data = await _llm_generate_json(TOPOLOGY_MODIFY_SYSTEM_PROMPT, user_prompt)
    except json.JSONDecodeError as e:
        return f"Failed to parse modified topology JSON: {e}. Please try rephrasing."
    except Exception as e:
        return f"LLM modification failed: {e}"

    # Ensure top-level fields and normalize
    data.setdefault("siteConnections", [])
    for site in data.get("sites", []):
        site.setdefault("subnetConnections", [])
        site.setdefault("position", {"x": 100, "y": 100})
    _normalize_topology(data)

    errors = _validate_topology(data)
    if errors:
        return "Modified topology has validation errors:\n" + "\n".join(f"- {e}" for e in errors) + "\nPlease try with clearer instructions."

    pending_id = uuid.uuid4().hex[:12]
    _pending_topologies[pending_id] = {
        "data": data,
        "mode": "modify",
        "created_at": time.time(),
    }

    summary = _summarize_topology(data)
    return (
        f"Topology modified successfully. Preview:\n\n{summary}\n\n"
        f"Pending ID: {pending_id}\n"
        f"Ask the user to confirm before calling save_topology."
    )


async def exec_save_topology(
    topo_data: dict, topo_id: str, pending_id: str, name: str | None = None,
    db: Session | None = None, **_: Any,
) -> str:
    """Save a pending topology after user confirmation."""
    pending = _pending_topologies.get(pending_id)
    if not pending:
        return f"Pending topology '{pending_id}' not found or expired. Please generate/modify again."

    if not db:
        return "Database session unavailable — cannot save."

    data = pending["data"]
    mode = pending["mode"]

    if mode == "create":
        topo_name = name or data.get("name") or "AI-Generated Topology"
        new_topo = Topology(name=topo_name, data=data)
        db.add(new_topo)
        db.commit()
        db.refresh(new_topo)
        del _pending_topologies[pending_id]
        return f"TOPOLOGY_CREATED:{new_topo.id}:{topo_name}"
    else:
        # Modify existing
        topo = db.get(Topology, topo_id)
        if not topo:
            return f"Topology '{topo_id}' not found."
        if name:
            topo.name = name
        topo.data = data
        db.commit()
        del _pending_topologies[pending_id]
        return f"TOPOLOGY_MODIFIED:{topo_id}:{topo.name}"


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
    "generate_topology": exec_generate_topology,
    "modify_topology": exec_modify_topology,
    "save_topology": exec_save_topology,
}

# Tools that require a db session
_DB_TOOLS = {"save_topology"}

# Instructor-only tools (students blocked from these)
INSTRUCTOR_ONLY_TOOLS = {"exec_command", "describe_topology", "generate_topology", "modify_topology", "save_topology"}


async def execute_tool(
    tool_name: str,
    args: dict[str, Any],
    topo_data: dict,
    topo_id: str,
    is_instructor: bool = False,
    db: Session | None = None,
) -> str:
    executor = EXECUTORS.get(tool_name)
    if not executor:
        return f"Unknown tool: {tool_name}"
    # Build extra kwargs without mutating the original args dict
    # (args is referenced by ai.py's tool_results and gets serialized)
    extra: dict[str, Any] = {}
    if tool_name == "run_command":
        extra["is_instructor"] = is_instructor
    if tool_name in _DB_TOOLS:
        extra["db"] = db
    return await executor(topo_data=topo_data, topo_id=topo_id, **args, **extra)
