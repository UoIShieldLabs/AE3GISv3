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
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models import Topology
from services.clab_manager import _docker_exec, deployment_name

log = logging.getLogger(__name__)

# ── Pending topology store (confirmation flow) ────────────────────

_pending_topologies: dict[str, dict] = {}
_pending_scenarios: dict[str, dict] = {}
_PENDING_TTL = 1800  # 30 minutes


def _cleanup_pending():
    """Remove expired pending topologies and scenarios."""
    now = time.time()
    expired = [k for k, v in _pending_topologies.items() if now - v["created_at"] > _PENDING_TTL]
    for k in expired:
        del _pending_topologies[k]
    expired = [k for k, v in _pending_scenarios.items() if now - v["created_at"] > _PENDING_TTL]
    for k in expired:
        del _pending_scenarios[k]


def _load_script_catalog() -> list[dict]:
    """Load catalog.json from the scripts directory."""
    catalog_path = Path(__file__).parent.parent / "scripts" / "catalog.json"
    if catalog_path.exists():
        return json.loads(catalog_path.read_text())
    return []


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
  type: one of "web-server", "file-server", "plc", "firewall", "switch", "router", "workstation", "hmi"
       NEVER use "server", "database", "historian", "domain-controller", or any other type not in this list.
  ip: string (must be within subnet CIDR)

Connection (all types — intra-subnet, subnetConnections, siteConnections):
  from: string (container ID)
  to: string (container ID)
  NOTE: Do NOT include fromInterface or toInterface on ANY connection — the system auto-assigns all interfaces to prevent duplicates.

## Rules
1. Every subnet MUST have exactly one router and one switch.
2. The router and switch must be connected (just from/to IDs, no interfaces).
3. All other containers connect to the switch (just from/to IDs, no interfaces).
4. Gateway IP is the router's IP (typically .1 in the subnet).
5. Container IDs must be globally unique across the entire topology.
6. Do NOT set fromInterface or toInterface on ANY connection — the system auto-assigns all interfaces.
7. For inter-subnet connections within a site, use subnetConnections with router IDs from each subnet.
8. For inter-site connections, use siteConnections with gateway router IDs from each site.
9. Use realistic CIDR ranges (10.x.x.0/24). Different subnets must use different ranges.
10. Container images: ONLY use images from this approved list — any other image name will fail to pull:
    - alpine:latest (default for all containers unless a specific image is listed below)
    - frrouting/frr:latest (auto-applied to router and firewall by the system — you don't need to set it)
    - b3nwilson/mal-client:latest
    - b3nwilson/ot-ws:latest
    - b3nwilson/stuxnet-plc:latest
    - b3nwilson/stux-new-hmi:latest
    - b3nwilson/stux-metasploit:latest
    NEVER invent image names like "ubuntu-apache", "kali-linux", "metasploit-framework", etc. If no specific image is needed, omit the image field entirely.
11. CRITICAL: Only specify fromInterface/toInterface inside subnet.connections (intra-subnet). NEVER on subnetConnections or siteConnections.
12. CRITICAL: NEVER use eth0 as an interface name. eth0 is reserved by ContainerLab for management. All interfaces must start at eth1.
13. Every subnet should have 2-4 additional containers beyond the required role-specific ones. Use varied types (workstation, web-server, file-server, plc, firewall) with realistic names (e.g. "Dev Workstation", "Internal Wiki", "Backup Server") to make the topology feel like a real environment. These extra containers connect to the switch in the normal way.

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


SCENARIO_GEN_SYSTEM_PROMPT = """You are a cybersecurity scenario generator for AE3GIS. Given a user's description, a list of available attack scripts (catalog), and the current topology containers, produce a valid Scenario JSON object.

## Scenario Schema

Scenario:
  id: string (kebab-case, unique — generate with uuid4 hex[:12])
  name: string
  description: string (1-2 sentences about the scenario)
  phases: AttackPhase[]

AttackPhase:
  id: string (kebab-case, e.g. "phase-recon-1")
  name: string (e.g. "Reconnaissance", "Initial Access", "Lateral Movement", "Impact")
  description: string (what this phase accomplishes)
  executions: ScriptExecution[]

ScriptExecution:
  containerId: string  (MUST be a real container ID from the topology)
  script: string       (MUST be a path from the catalog, e.g. "/scripts/workstation/router-nmap.sh")
  args: string[]       (positional args matching the script's catalog entry; populate with real IPs/values from topology)

## CRITICAL: Selecting the right container for each script

Each catalog entry has a `runOnImage` field. This is the Docker image the script MUST run inside — it contains the required tools and payload files.

**Step 1 — match by image:** Find the topology container whose `image` field matches the catalog entry's `runOnImage`. Use that container's `id` as `containerId`.
**Step 2 — fallback by type:** If no container has that image, fall back to the catalog's `runOn` type (e.g. "workstation"), preferring the one in the most logical subnet.
**Step 3 — never guess:** Do not put a script on a container just because it has the right type if a better image match exists.

### Known image → role mappings (Stuxnet topology)
- `b3nwilson/mal-client:latest` → attacker/victim machine in the IT subnet. Runs: router-nmap.sh, dmz-network-scan.sh, exploit-samba.sh, access-ot-ws.sh
- `b3nwilson/ot-ws:latest` → OT engineering workstation. Runs: deploy_motor_plc.sh, deploy_stuxnet.sh, deploy_hmi.sh. This container has the firmware and payload files needed by those scripts.
- `b3nwilson/stuxnet-plc:latest` → the OpenPLC target (PLC 1). Never runs scripts — only its IP is used as an arg.
- `b3nwilson/stux-new-hmi:latest` → the ScadaBR/HMI target. Never runs scripts — only its IP is used as an arg.
- `b3nwilson/stux-metasploit:latest` → the Samba-vulnerable file server in the DMZ. Never runs scripts — its IP is the SAMBA_TARGET arg for exploit-samba.sh.

## Arg formatting rules

### deploy_motor_plc.sh and deploy_stuxnet.sh — arg 1: PLC_URL
- Format: `"IP:8080"` where IP is from the container with image `b3nwilson/stuxnet-plc:latest`
- Example: `["192.168.1.6:8080"]`
- The script auto-prepends `http://` — do NOT include it yourself.

### deploy_hmi.sh — arg 1: HMI_URL
- Format: `"IP:8080"` where IP is from the container with image `b3nwilson/stux-new-hmi:latest`
- Example: `["192.168.1.3:8080"]`
- The script auto-prepends `http://` and appends `/ScadaBR` — do NOT include them yourself.
- This script takes ONLY ONE argument. Do not add a second arg.

### exploit-samba.sh — args 1 and 2
- arg 1 (SAMBA_TARGET): IP of the file-server/jump-host running vulnerable Samba (image: `b3nwilson/stux-metasploit:latest`)
- arg 2 (LHOST): IP of the container running this script (the mal-client container's own IP)

### access-ot-ws.sh — args 1 and 2
- arg 1 (OT_WS_IP): IP of the OT workstation (image: `b3nwilson/ot-ws:latest`)
- arg 2 (OT_CIDR): CIDR of the OT subnet (e.g. "192.168.1.0/24")
- Omit arg 3 (SSH_KEY) — defaults to /root/.ssh/stux-key

### router-nmap.sh — arg 1
- arg 1 (ROUTER_IP): IP of the perimeter/gateway router container (type: "router" in the IT or DMZ subnet)
- Omit args 2 and 3 — defaults to root/root

### dmz-network-scan.sh — arg 1 (optional)
- arg 1 (SCAN_CIDR): CIDR of the DMZ subnet. If omitted the script reads ~/routes.txt.
- Include it explicitly with the DMZ subnet CIDR for reliability.

## Reference topology — Polished Stuxnet

When the user's topology matches this layout (look for the same images), use the container IDs and IPs from the actual topology provided, but apply these exact mappings:

```
OT Subnet (192.168.1.0/24)
  LAN Router         type=router      ip=192.168.1.1  image=(none)                           — subnet gateway
  LAN Switch         type=switch      ip=192.168.1.2  image=(none)
  Workstation 1      type=workstation ip=192.168.1.5  image=b3nwilson/ot-ws:latest           — RUNS deploy scripts
  PLC 1              type=plc         ip=192.168.1.6  image=b3nwilson/stuxnet-plc:latest     — TARGET for PLC_URL arg (use "192.168.1.6:8080")
  HMI-new            type=hmi         ip=192.168.1.3  image=b3nwilson/stux-new-hmi:latest    — TARGET for HMI_URL arg (use "192.168.1.3:8080")
  (+ extra containers: e.g. Historian DB, Safety Controller, Engineering Laptop)

IT Subnet (192.168.2.0/24)
  IT Router          type=router      ip=192.168.2.1  image=(none)                           — ROUTER_IP arg for router-nmap.sh
  Victim Machine     type=workstation ip=192.168.2.3  image=b3nwilson/mal-client:latest      — RUNS recon + exploit scripts; LHOST arg = 192.168.2.3
  (+ extra containers: e.g. HR Workstation, Dev Workstation, Internal Web Server)

DMZ Subnet (192.168.3.0/24)
  DMZ Router         type=router      ip=192.168.3.1  image=(none)
  File Server 1      type=file-server ip=192.168.3.5  image=b3nwilson/stux-metasploit:latest — SAMBA_TARGET arg for exploit-samba.sh
  (+ extra containers: e.g. Jump Box, Mail Relay, Proxy Server)
```

### Complete Polished Stuxnet scenario — ONE script per phase (use this as canonical output):

Phase 1 "Initial Enumeration" (reconnaissance):
  containerId = Victim Machine id,    script = router-nmap.sh,       args = ["192.168.2.1"]

Phase 2 "DMZ Vuln Scan" (reconnaissance):
  containerId = Victim Machine id,    script = dmz-network-scan.sh,  args = ["192.168.3.0/24"]

Phase 3 "Exploit Found Vuln" (initial-access):
  containerId = Victim Machine id,    script = exploit-samba.sh,     args = ["192.168.3.5", "192.168.2.3"]

Phase 4 "Access OT Network" (lateral-movement):
  containerId = Victim Machine id,    script = access-ot-ws.sh,      args = ["192.168.1.5", "192.168.1.0/24"]

Phase 5 "Push Stuxnet Payload" (impact):
  containerId = OT Workstation 1 id,  script = deploy_stuxnet.sh,    args = ["192.168.1.6:8080"]

Always replace the example IPs above with the real IPs from the provided topology containers.

## General rules
1. Only use scripts from the catalog, only use container IDs from the topology.
2. CRITICAL: Each phase must have EXACTLY ONE execution. Never put two scripts in the same phase.
3. The `args` array contains only the positional arg values in order (pos 1, 2, 3...). Omit trailing optional args you cannot resolve.
4. Use `null` for args when ALL args are optional and env vars will provide them at runtime.
5. Use `killChainStage` to group scripts into logical phases. Respect `requires` ordering.

Respond with ONLY the JSON object. No markdown fences, no explanation."""


TOPOLOGY_AND_SCENARIO_GEN_SYSTEM_PROMPT = """You are a combined network topology and cybersecurity scenario generator for AE3GIS.

Given a user's description and a script catalog, you will generate BOTH:
1. A complete network topology with the correct Docker container images so the scripts can actually run
2. A multi-phase attack scenario that references those exact containers

## Output format

Respond with a single JSON object with exactly two top-level keys:

{
  "topology": { ...TopologyData... },
  "scenario": { ...Scenario... }
}

---

## Topology rules (same as standard topology generation)

TopologyData: { name, sites[], siteConnections[] }
Site: { id (kebab), name, location, position {x,y}, subnets[], subnetConnections[] }
Subnet: { id (kebab), name, cidr, gateway (router IP), containers[], connections[] }
Container: { id (kebab, globally unique), name, type, ip, image? }
  type MUST be one of: "web-server", "file-server", "plc", "firewall", "switch", "router", "workstation", "hmi"
  NEVER use "server", "database", "historian", "domain-controller", or any other unlisted type.
Connection (all types): { from, to } — NEVER include fromInterface or toInterface; the system auto-assigns all interfaces

Rules:
- Every subnet needs exactly one router and one switch, wired together
- All other containers connect to the switch
- Use realistic CIDRs (10.x.x.0/24); different subnets use different ranges
- NEVER include fromInterface or toInterface on ANY connection — the system auto-assigns all interfaces to prevent duplicates
- Every subnet should include 2-4 extra containers beyond the required script-execution and target containers. Use varied realistic types (workstation, web-server, file-server, plc, firewall) with descriptive names (e.g. "HR Workstation", "Internal Wiki", "Backup Server", "Historian DB"). These connect to the switch normally and do not need special images.
- CRITICAL — container images: ONLY use images from this approved list. Any other image will fail to pull and break deployment:
    alpine:latest (default — omit the image field for generic containers, the system will use alpine)
    frrouting/frr:latest (auto-applied to routers/firewalls — you don't need to set this)
    b3nwilson/mal-client:latest, b3nwilson/ot-ws:latest, b3nwilson/stuxnet-plc:latest,
    b3nwilson/stux-new-hmi:latest, b3nwilson/stux-metasploit:latest
  NEVER invent image names. If a container doesn't need a special image, omit the image field entirely.

---

## Container image requirements (CRITICAL)

Each script in the catalog has a `runOnImage` field. You MUST include containers with those exact images in the topology so the scripts have somewhere to run. The images are also required for the TARGET containers (PLC, HMI).

### Required images for Stuxnet-style scenarios:
- `b3nwilson/mal-client:latest`   — attacker workstation (runs recon + exploit scripts). Place in IT/corporate subnet.
- `b3nwilson/ot-ws:latest`        — OT engineering workstation (runs all deploy scripts; has firmware files). Place in OT/SCADA subnet.
- `b3nwilson/stuxnet-plc:latest`  — OpenPLC target. type="plc". Place in OT/SCADA subnet. Port 8080 for web API.
- `b3nwilson/stux-new-hmi:latest` — ScadaBR HMI target. type="hmi". Place in OT/SCADA subnet. Port 8080 for web UI.
- `b3nwilson/stux-metasploit:latest` — Samba-vulnerable file server. type="file-server". Place in DMZ subnet.

If the user's request is Stuxnet-related, include ALL five of these images in the topology.

---

## Scenario rules

Scenario: { id (hex12), name, description, phases[] }
AttackPhase: { id (kebab), name, description, executions[] }
ScriptExecution: { containerId (from topology above), script (from catalog), args[] }

CRITICAL: Each phase must contain EXACTLY ONE script execution. Never put two scripts in the same phase's executions array. Give each script its own named phase.

### Container selection for each script — match by image:
- router-nmap.sh, dmz-network-scan.sh, exploit-samba.sh, access-ot-ws.sh → container with image `b3nwilson/mal-client:latest`
- deploy_motor_plc.sh, deploy_stuxnet.sh, deploy_hmi.sh → container with image `b3nwilson/ot-ws:latest`

### Arg formats (scripts auto-add http:// — pass bare IP:PORT):
- deploy_motor_plc.sh arg 1: `"<plc_ip>:8080"` (IP of the stuxnet-plc container)
- deploy_stuxnet.sh  arg 1: `"<plc_ip>:8080"` (IP of the stuxnet-plc container)
- deploy_hmi.sh      arg 1: `"<hmi_ip>:8080"` (IP of the stux-new-hmi container) — ONE arg only
- exploit-samba.sh   arg 1: IP of stux-metasploit container; arg 2: IP of mal-client container (LHOST)
- access-ot-ws.sh    arg 1: IP of ot-ws container; arg 2: OT subnet CIDR
- router-nmap.sh     arg 1: IP of IT/corporate router
- dmz-network-scan.sh arg 1: DMZ subnet CIDR

Use the ACTUAL IPs you assigned to containers in the topology above — not placeholders.

---

## Reference — full Polished Stuxnet layout (use this when the request is Stuxnet-related):

Subnet layout:
  OT  (192.168.1.0/24): LAN Router .1, LAN Switch .2, ot-ws .5, stuxnet-plc .6, stux-new-hmi .3
  IT  (192.168.2.0/24): IT Router .1,  IT Switch .2,  mal-client .3
  DMZ (192.168.3.0/24): DMZ Router .1, DMZ Switch .2, stux-metasploit .5

subnetConnections: IT↔DMZ (IT Router ↔ DMZ Router), DMZ↔OT (DMZ Router ↔ LAN Router)

Canonical scenario phases — ONE script per phase (substitute real IDs and IPs):
  Phase 1 "Initial Enumeration": mal-client runs router-nmap.sh ["192.168.2.1"]
  Phase 2 "DMZ Vuln Scan":       mal-client runs dmz-network-scan.sh ["192.168.3.0/24"]
  Phase 3 "Exploit Found Vuln":  mal-client runs exploit-samba.sh ["192.168.3.5", "192.168.2.3"]
  Phase 4 "Access OT Network":   mal-client runs access-ot-ws.sh ["192.168.1.5", "192.168.1.0/24"]
  Phase 5 "Push Stuxnet Payload": ot-ws runs deploy_stuxnet.sh ["192.168.1.6:8080"]

---

Respond with ONLY the JSON object { "topology": {...}, "scenario": {...} }. No markdown fences, no explanation."""


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
    {
        "type": "function",
        "function": {
            "name": "generate_topology_and_scenario",
            "description": "Generate a complete network topology WITH the correct container images AND a matching attack scenario — all from scratch. Use this when the user wants to create a lab environment from a description (e.g. 'create a Stuxnet scenario'). The topology will include the exact images needed for the scripts to run. Returns a preview of both for confirmation before saving.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Natural language description of the desired topology and scenario. Include the attack goal, network layout, and which scripts/phases to include.",
                    },
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_topology_and_scenario",
            "description": "Save a topology+scenario pair generated by generate_topology_and_scenario. ONLY call after showing the user the preview and receiving confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pending_id": {
                        "type": "string",
                        "description": "The pending ID returned by generate_topology_and_scenario.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Name for the topology (optional).",
                    },
                },
                "required": ["pending_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_scenario",
            "description": "Generate a cybersecurity attack scenario against the CURRENTLY LOADED topology. Only use this when a topology is already open. Use generate_topology_and_scenario instead when starting from scratch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Natural language description of the desired scenario.",
                    },
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_scenario",
            "description": "Save a scenario generated by generate_scenario to the current topology. ONLY call after user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pending_id": {
                        "type": "string",
                        "description": "The pending scenario ID returned by generate_scenario.",
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


_VALID_CONTAINER_TYPES = {
    "web-server", "file-server", "plc", "firewall", "switch", "router", "workstation", "hmi",
}

# Images that are known to exist and can be pulled. Anything else → alpine:latest.
_APPROVED_IMAGES = {
    "alpine:latest",
    "frrouting/frr:latest",
    "b3nwilson/mal-client:latest",
    "b3nwilson/ot-ws:latest",
    "b3nwilson/stuxnet-plc:latest",
    "b3nwilson/stux-new-hmi:latest",
    "b3nwilson/stux-metasploit:latest",
}

_TYPE_REMAP = {
    # common LLM hallucinations → nearest valid type
    "server": "file-server",
    "database": "file-server",
    "db-server": "file-server",
    "historian": "file-server",
    "data-historian": "file-server",
    "web_server": "web-server",
    "file_server": "file-server",
    "domain-controller": "file-server",
    "dns-server": "file-server",
    "mail-server": "file-server",
    "jump-box": "workstation",
    "jumpbox": "workstation",
    "attacker": "workstation",
    "engineering-station": "workstation",
    "scada": "hmi",
    "hmi-workstation": "hmi",
}


def _normalize_topology(data: dict) -> None:
    """Post-process LLM-generated topology to fix common issues.

    - Strips fromInterface/toInterface from subnetConnections and siteConnections
      (the clab_generator auto-assigns them; explicit ones cause duplicate endpoint errors).
    - Removes any intra-subnet connection that explicitly uses eth0 — ContainerLab
      reserves eth0 for management and will reject it on data-plane links.
    - Remaps unknown container types to the nearest valid type.
    """
    for conn in data.get("siteConnections", []):
        conn.pop("fromInterface", None)
        conn.pop("toInterface", None)
    for site in data.get("sites", []):
        # Ensure required fields have defaults
        if not site.get("location"):
            site["location"] = ""
        site.setdefault("position", {"x": 100, "y": 100})
        site.setdefault("subnetConnections", [])
        for conn in site.get("subnetConnections", []):
            conn.pop("fromInterface", None)
            conn.pop("toInterface", None)
        for subnet in site.get("subnets", []):
            subnet.setdefault("connections", [])
            subnet.setdefault("containers", [])
            for container in subnet.get("containers", []):
                ctype = container.get("type", "")
                if ctype not in _VALID_CONTAINER_TYPES:
                    container["type"] = _TYPE_REMAP.get(ctype, "workstation")
                # Strip any image not in the approved list to prevent pull failures
                img = container.get("image")
                if img and img not in _APPROVED_IMAGES:
                    container.pop("image", None)
            for conn in subnet.get("connections", []):
                # Strip all explicit interface names — clab_generator auto-assigns
                # them sequentially via _next_iface(), preventing duplicate endpoint errors.
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


def _normalize_scenario(scenario: dict) -> None:
    """Split any phase that has more than one execution into separate phases (one script each)."""
    new_phases = []
    for phase in scenario.get("phases", []):
        executions = phase.get("executions", [])
        if len(executions) <= 1:
            new_phases.append(phase)
        else:
            for i, ex in enumerate(executions):
                suffix = f" ({i + 1})" if i > 0 else ""
                new_phases.append({
                    "id": f"{phase['id']}-{i + 1}" if i > 0 else phase["id"],
                    "name": phase["name"] + suffix,
                    "description": phase.get("description"),
                    "executions": [ex],
                })
    scenario["phases"] = new_phases


def _scenario_preview(
    scenario: dict,
    id_to_name: dict[str, str],
    pending_id: str | None,
    save_tool: str | None,
) -> str:
    lines = [f"Scenario: {scenario['name']}", f"Description: {scenario.get('description', '')}"]
    for phase in scenario.get("phases", []):
        lines.append(f"\nPhase: {phase['name']}")
        if phase.get("description"):
            lines.append(f"  {phase['description']}")
        for ex in phase.get("executions", []):
            cname = id_to_name.get(ex["containerId"], ex["containerId"])
            args = ex.get("args") or []
            args_str = " ".join(str(a) for a in args)
            lines.append(f"  - [{cname}] {ex['script']} {args_str}".rstrip())
    result = "\n".join(lines)
    if pending_id and save_tool:
        result += f"\n\nPending ID: {pending_id}\nAsk the user to confirm before calling {save_tool}."
    return result


async def exec_generate_scenario(topo_data: dict, topo_id: str, description: str, **_: Any) -> str:
    """Generate a scenario against an already-loaded topology."""
    _cleanup_pending()
    catalog = _load_script_catalog()
    if not catalog:
        return "No script catalog found. Cannot generate scenario."

    valid_script_paths = {entry["path"] for entry in catalog}

    containers = []
    valid_container_ids: set[str] = set()
    for site in topo_data.get("sites", []):
        for subnet in site.get("subnets", []):
            for c in subnet.get("containers", []):
                valid_container_ids.add(c["id"])
                entry: dict = {
                    "id": c["id"],
                    "name": c["name"],
                    "type": c["type"],
                    "ip": c["ip"],
                    "subnet": subnet["name"],
                    "subnet_cidr": subnet["cidr"],
                    "site": site["name"],
                }
                if c.get("image"):
                    entry["image"] = c["image"]
                containers.append(entry)

    if not containers:
        return (
            "No containers found in the current topology. "
            "Use generate_topology_and_scenario to create both a topology and scenario from scratch."
        )

    user_prompt = (
        f"## User Request\n{description}\n\n"
        f"## Available Scripts (catalog — ONLY use these exact paths)\n"
        f"{json.dumps(catalog, indent=2)}\n\n"
        f"## Topology Containers (ONLY use these exact container IDs)\n"
        f"{json.dumps(containers, indent=2)}\n\n"
        "Every containerId MUST be from the list above. "
        "Every script path MUST be from the catalog above. No other scripts or tools are permitted."
    )

    try:
        data = await _llm_generate_json(SCENARIO_GEN_SYSTEM_PROMPT, user_prompt)
    except json.JSONDecodeError as e:
        return f"Failed to parse generated scenario JSON: {e}. Please try rephrasing."
    except Exception as e:
        return f"LLM generation failed: {e}"

    if not isinstance(data.get("phases"), list):
        return "Generated scenario is missing 'phases'. Please try again."

    _normalize_scenario(data)

    # Hard validation
    invalid_scripts = [ex.get("script", "") for phase in data.get("phases", [])
                       for ex in phase.get("executions", []) if ex.get("script", "") not in valid_script_paths]
    invalid_containers = [ex.get("containerId", "") for phase in data.get("phases", [])
                          for ex in phase.get("executions", []) if ex.get("containerId", "") not in valid_container_ids]
    if invalid_scripts or invalid_containers:
        return (
            f"Generated scenario used invalid scripts or containers and was rejected.\n"
            f"Invalid scripts: {invalid_scripts}\nInvalid container IDs: {invalid_containers}\n"
            "Please try again."
        )

    data.setdefault("id", uuid.uuid4().hex[:12])
    data.setdefault("name", "AI-Generated Scenario")
    data.setdefault("description", description[:200])

    pending_id = uuid.uuid4().hex[:12]
    _pending_scenarios[pending_id] = {"data": data, "topology_id": topo_id, "created_at": time.time()}

    return _scenario_preview(data, {c["id"]: c["name"] for c in containers}, pending_id, "save_scenario")


async def exec_generate_topology_and_scenario(
    topo_data: dict, topo_id: str, description: str, **_: Any
) -> str:
    """Generate a brand-new topology (with correct container images) AND a scenario together from scratch."""
    _cleanup_pending()
    catalog = _load_script_catalog()
    if not catalog:
        return "No script catalog found. Cannot generate scenario."

    valid_script_paths = {entry["path"] for entry in catalog}

    user_prompt = (
        f"## User Request\n{description}\n\n"
        f"## Available Scripts (catalog — ONLY use these exact paths in the scenario)\n"
        f"{json.dumps(catalog, indent=2)}\n\n"
        "Generate a JSON object with two top-level keys: \"topology\" and \"scenario\".\n"
        "The topology MUST include containers with the correct `image` fields so the scripts can run.\n"
        "The scenario MUST only reference container IDs that exist in the generated topology.\n"
        "Every script in the scenario MUST be from the catalog above.\n"
        "No other scripts, commands, or tools are permitted in the scenario."
    )

    try:
        data = await _llm_generate_json(TOPOLOGY_AND_SCENARIO_GEN_SYSTEM_PROMPT, user_prompt)
    except json.JSONDecodeError as e:
        return f"Failed to parse generated JSON: {e}. Please try rephrasing."
    except Exception as e:
        return f"LLM generation failed: {e}"

    topo = data.get("topology")
    scenario = data.get("scenario")

    if not isinstance(topo, dict) or not isinstance(scenario, dict):
        return "Generated output is missing 'topology' or 'scenario' keys. Please try again."

    # Normalize and validate topology
    topo.setdefault("siteConnections", [])
    for site in topo.get("sites", []):
        site.setdefault("subnetConnections", [])
        site.setdefault("position", {"x": 100, "y": 100})
    _normalize_topology(topo)

    topo_errors = _validate_topology(topo)
    if topo_errors:
        return "Generated topology has errors:\n" + "\n".join(f"- {e}" for e in topo_errors) + "\nPlease try again."

    # Build container lookup from the generated topology
    containers = []
    valid_container_ids: set[str] = set()
    for site in topo.get("sites", []):
        for subnet in site.get("subnets", []):
            for c in subnet.get("containers", []):
                valid_container_ids.add(c["id"])
                containers.append(c)

    # Validate scenario
    if not isinstance(scenario.get("phases"), list):
        return "Generated scenario is missing 'phases'. Please try again."

    _normalize_scenario(scenario)

    invalid_scripts = [ex.get("script", "") for phase in scenario.get("phases", [])
                       for ex in phase.get("executions", []) if ex.get("script", "") not in valid_script_paths]
    invalid_containers = [ex.get("containerId", "") for phase in scenario.get("phases", [])
                          for ex in phase.get("executions", []) if ex.get("containerId", "") not in valid_container_ids]
    if invalid_scripts or invalid_containers:
        return (
            f"Generated scenario used invalid scripts or containers and was rejected.\n"
            f"Invalid scripts: {invalid_scripts}\nInvalid container IDs: {invalid_containers}\n"
            "Please try again."
        )

    scenario.setdefault("id", uuid.uuid4().hex[:12])
    scenario.setdefault("name", "AI-Generated Scenario")

    pending_id = uuid.uuid4().hex[:12]
    _pending_topologies[pending_id] = {
        "data": topo,
        "scenario": scenario,
        "mode": "create",
        "created_at": time.time(),
    }

    topo_summary = _summarize_topology(topo)
    scenario_preview = _scenario_preview(
        scenario, {c["id"]: c["name"] for c in containers}, pending_id=None, save_tool=None
    )

    return (
        f"Topology + scenario generated. Preview:\n\n"
        f"=== TOPOLOGY ===\n{topo_summary}\n\n"
        f"=== SCENARIO ===\n{scenario_preview}\n\n"
        f"Pending ID: {pending_id}\n"
        f"Ask the user to confirm, then call save_topology_and_scenario with the pending_id."
    )


async def exec_save_scenario(
    topo_data: dict, topo_id: str, pending_id: str,
    db: Session | None = None, **_: Any,
) -> str:
    """Save a pending scenario to the current topology after user confirmation."""
    pending = _pending_scenarios.get(pending_id)
    if not pending:
        return f"Pending scenario '{pending_id}' not found or expired. Please generate again."

    if not db:
        return "Database session unavailable — cannot save."

    topo = db.get(Topology, topo_id)
    if not topo:
        return f"Topology '{topo_id}' not found."

    scenario = pending["data"]
    topo_data_copy = dict(topo.data) if isinstance(topo.data, dict) else {}
    if "scenarios" not in topo_data_copy:
        topo_data_copy["scenarios"] = []
    topo_data_copy["scenarios"].append(scenario)

    topo.data = topo_data_copy
    db.commit()
    del _pending_scenarios[pending_id]
    return f"SCENARIO_CREATED:{scenario['id']}:{scenario['name']}"


async def exec_save_topology_and_scenario(
    topo_data: dict, topo_id: str, pending_id: str, name: str | None = None,
    db: Session | None = None, **_: Any,
) -> str:
    """Save a pending topology+scenario pair after user confirmation."""
    pending = _pending_topologies.get(pending_id)
    if not pending or pending.get("mode") != "create" or "scenario" not in pending:
        return f"Pending topology+scenario '{pending_id}' not found or expired. Please generate again."

    if not db:
        return "Database session unavailable — cannot save."

    topo_json = pending["data"]
    scenario = pending["scenario"]

    topo_name = name or topo_json.get("name") or "AI-Generated Topology"
    topo_json.setdefault("scenarios", [])
    topo_json["scenarios"].append(scenario)

    new_topo = Topology(name=topo_name, data=topo_json)
    db.add(new_topo)
    db.commit()
    db.refresh(new_topo)
    del _pending_topologies[pending_id]

    return f"TOPOLOGY_CREATED:{new_topo.id}:{topo_name}"


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
    "generate_scenario": exec_generate_scenario,
    "save_scenario": exec_save_scenario,
    "generate_topology_and_scenario": exec_generate_topology_and_scenario,
    "save_topology_and_scenario": exec_save_topology_and_scenario,
}

# Tools that require a db session
_DB_TOOLS = {"save_topology", "save_scenario", "save_topology_and_scenario"}

# Instructor-only tools (students blocked from these)
INSTRUCTOR_ONLY_TOOLS = {
    "exec_command", "describe_topology", "generate_topology", "modify_topology",
    "save_topology", "generate_scenario", "save_scenario",
    "generate_topology_and_scenario", "save_topology_and_scenario",
}


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
