# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AE3GIS v2 is an interactive network topology visualization and deployment platform. Three-level drill-down: Geographic → Subnet → LAN. Integrates with **ContainerLab** to deploy Docker-based network simulations.

## Development Commands

```bash
./start.sh

# Frontend dev
cd frontend && npm run dev        # :5173

# Backend dev
cd backend && source .venv/bin/activate
python -m uvicorn main:app --reload --port 8000
```

Backend container requires `network_mode: host` + `privileged: true` for Docker socket and host netns access. Scripts are mounted at the same absolute host path inside the container (ContainerLab resolves paths at the host daemon level). CI/CD: push to `main` → SSH deploy via `.github/workflows/deploy.yml`.

## Architecture

### State Management

Immer reducer (`store/topologyReducer.ts`). `dirty` flag tracks unsaved changes — `UPDATE_CONTAINER_STATUSES` is the only action that does NOT set it. Key side effects:
- `ADD_SUBNET` auto-creates a router + switch, wired together
- `ADD_INTER_SUBNET_CONNECTION` auto-creates gateway routers in both subnets

`handleDeploy()` in `App.tsx` auto-saves if `dirty` before deploying.

### Data Model

```typescript
Container { id, name, type, ip, kind?, image?, status?, metadata? }
Connection { from, to, label?, fromInterface?, toInterface?, fromContainer?, toContainer? }
Subnet { id, name, cidr, gateway?, containers[], connections[] }
Site { id, name, location, position, subnets[], subnetConnections[] }
TopologyData { name?, sites[], siteConnections[], scenarios? }

ScriptExecution { containerId, script, args? }
AttackPhase { id, name, description?, executions: ScriptExecution[] }
Scenario { id, name, description?, phases: AttackPhase[] }
```

Container types: `web-server`, `file-server`, `plc`, `firewall`, `switch`, `router`, `workstation`

### Backend Routers

- `routers/topologies.py` — CRUD (`/api/topologies`)
- `routers/containerlab.py` — deploy/destroy/status/exec/WebSocket; `GET /scripts/available`; `POST /{id}/scenarios/{scenario_id}/phases/{phase_id}/execute`
- `routers/classroom.py` — sessions + student slots (`/api/classroom`)
- `routers/presets.py` — preset templates from `backend/presets/*.json` (`/api/presets`)
- `routers/proxy.py` — HTTP reverse proxy to container management IPs (`/api/proxy/{topology_id}/{container_id}/{path}`)

### Backend Services

- `clab_generator.py` — TopologyData → ContainerLab YAML (see below)
- `clab_importer.py` — `.clab.yml` → TopologyData; groups by CIDR into subnets, by `group` field into sites
- `clab_manager.py` — `sudo containerlab deploy/destroy`; self-heals stale Docker bridge metadata on "Failed to lookup link" error
- `ansible_manager.py` — pushes configurations to containers after topology is deemed healthy

**Database:** SQLite (`/app/data/ae3gis.db` in Docker, `ae3gis.db` locally). Status lifecycle: `idle` → `deployed` → `idle`.

**WebSocket — exec terminal:** PTY bridge via `pty.openpty()` + `docker exec -it`. Strips ANSI codes, normalizes CRLF→LF. `GET /precheck` validates access before opening (returns `docker_permission_denied`, `container_not_found`, etc.).

### YAML Generation (`clab_generator.py`)

1. **Metadata:** Auto-detect gateway — if `subnet.gateway` unset, uses first router/firewall IP in subnet. Builds subnet_id → gateway_router_id maps.
2. **Interfaces:** Pre-registers explicit names to prevent collisions. Auto-assigns `eth{N}` via `_next_iface()`. Resolves subnet/site IDs in connections to container IDs via gateway routers.
3. **IPs & routes:** Same-subnet links use the container's primary IP. Cross-subnet router↔router links get /30 PtP IPs from `10.255.0.0/24` (sequential: .1/30, .5/30, …; ~63 links max). Each router gets a static route to the peer subnet.
4. **Exec configs:** Switches — Linux bridge (`br0`), all non-home interfaces added, IP on bridge. Routers/Firewalls — `ip_forward=1`, IPs on all interfaces, static routes. Hosts — IP on home interface only, default route via subnet gateway (keeps PtP reply traffic working).

**Images:** Pulled dynamically from Docker Hub by a script executed during the start.sh script for container aspects and by clab_generator.py to mape ctype to container images.

**Naming (must stay in sync across frontend + backend):**
- Deployment: `{topology_name}-{first_8_chars_of_id}` (`utils/deploymentName.ts` ↔ `clab_manager.deployment_name()`)
- Container: `clab-{topology_name}-{container_id}`

## Authentication & Roles

**Instructor** — Bearer token validated against `INSTRUCTOR_TOKEN` env var. Token sent on all requests.

**Student** — UUID join code exchanged via `POST /api/classroom/login` for a token + `topology_id`. Join code doubles as bearer token. Students get read-only UI and are locked to their assigned topology (403 on any other).

## Classroom Mode

`ClassSession` groups `StudentSlot`s, each owning a deep-copied topology and a unique join code. Instantiation clones the template via `copy.deepcopy()`. `ScenarioPanel` (instructor-only) supports per-phase script execution and batch execution across all classroom slots.
