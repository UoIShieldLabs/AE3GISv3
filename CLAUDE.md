# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AE3GIS v2 is an interactive network topology visualization and deployment platform. It provides a three-level drill-down view (Geographic → Subnet → LAN) and integrates with **ContainerLab** to deploy Docker-based network simulations from the topology designs.

## Development Commands

### Frontend (React/TypeScript)

```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Dev server at http://localhost:5173
npm run build        # Type-check + production build
npm run lint         # Run ESLint
```

### Backend (FastAPI/Python)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Frontend proxies `/api/*` and WebSocket paths to backend at `http://localhost:8000` (5-minute timeout for deploy/destroy operations).

## Architecture

### Frontend (`frontend/src/`)

**Three-level drill-down views:**

- `GeographicView` → Sites on a graph
- `SubnetView` → Subnets within a site
- `LanView` → Containers/devices within a subnet

**State management:** Immer-based reducer (`store/topologyReducer.ts`) with `useImmerReducer`. A `dirty` flag tracks unsaved changes; `UPDATE_CONTAINER_STATUSES` is the only action that does NOT set `dirty`. Key automatic behaviors in the reducer:

- `ADD_SUBNET` auto-creates a router and switch, wired together
- `ADD_INTER_SUBNET_CONNECTION` auto-creates gateway routers in both subnets if not present

**Key dependencies:** `@xyflow/react` (ReactFlow) for graph visualization, `@dagrejs/dagre` for auto-layout.

**Component structure:**

- `components/nodes/` — Custom ReactFlow node types (SiteNode, SubnetCloudNode, DeviceNode, RouterNode)
- `components/edges/` — NeonEdge for visual styling
- `components/dialogs/` — CRUD modal dialogs (also BulkContainerDialog, BulkConnectionDialog)
- `api/client.ts` — REST client for all backend calls

**Utilities (`utils/`):**

- `validation.ts` — IP/CIDR arithmetic (`parseCidr`, `getNextAvailableIp`, `isIpInCidr`, etc.)
- `deploymentName.ts` — `deploymentName(id, name)` → `{name}-{id_first_8_chars}` (must match backend)

### Backend (`backend/`)

**Routers:**

- `routers/topologies.py` — CRUD for topologies (`/api/topologies`)
- `routers/containerlab.py` — Deploy, destroy, status, exec, WebSocket endpoints

**Services:**

- `services/clab_generator.py` — Converts frontend topology JSON → ContainerLab YAML (see below)
- `services/clab_manager.py` — ContainerLab lifecycle management (deploys via `sudo containerlab deploy/destroy`). Self-heals stale Docker bridge metadata: detects "Failed to lookup link" error, removes the stale network, and retries.

**Database:** SQLite (`ae3gis.db`) with SQLAlchemy ORM. Topology data stored as a JSON column. Status lifecycle: `idle` → `deployed` → `idle`.

**WebSocket endpoints:**

- `ws/{id}/status` — Live container status via 5-second polling; strips `clab-{topo_name}-` prefix from container names to recover container IDs
- `ws/{id}/exec/{container_id}` — Interactive terminal via PTY bridge (`pty.openpty()` + `docker exec -it`); strips ANSI escape codes, normalizes CRLF → LF
- `GET /{id}/exec/{container_id}/precheck` — Validates docker access before opening terminal (returns structured reason codes: `docker_permission_denied`, `container_not_found`, etc.)

### Data Model

```typescript
Container { id, name, type, ip, kind?, image?, status?, metadata? }
Connection { from, to, label?, fromInterface?, toInterface?, fromContainer?, toContainer? }
Subnet { id, name, cidr, gateway?, containers[], connections[] }
Site { id, name, location, position, subnets[], subnetConnections[] }
TopologyData { name?, sites[], siteConnections[] }
```

Container types: `web-server`, `file-server`, `plc`, `firewall`, `switch`, `router`, `workstation`

### YAML Generation (`services/clab_generator.py`)

Four-step process to convert TopologyData → ContainerLab YAML:

**Step 1 – Build metadata:** Collect IP/subnet info per container. Auto-detect gateway: if `subnet.gateway` is unset, uses the first router/firewall container's IP in that subnet. Builds lookup maps (subnet_id → gateway_router_id) for cross-subnet routing.

**Step 2 – Resolve connections & assign interfaces:** Pre-registers explicitly named interfaces to prevent collisions. Auto-assigns sequential `eth{N}` via `_next_iface()`. Resolves subnet/site IDs in connections to actual container IDs via gateway routers.

**Step 3 – Compute per-interface IPs & static routes:**

- Same-subnet links: container's primary IP on its first (home) interface
- Cross-subnet router↔router links: auto-assigns /30 point-to-point IPs sequentially from `10.255.0.0/24` (10.255.0.1/30, 10.255.0.5/30, …; supports ~63 cross-subnet links). Each router gets a static route to the peer's subnet via the peer's PtP IP.

**Step 4 – Build node exec configs:**

- **Switches**: Creates a Linux bridge (`ip link add br0 type bridge`), adds all non-home interfaces to it, assigns IP to bridge. Falls back to primary interface if bridge creation fails.
- **Routers/Firewalls**: Enables IP forwarding (`sysctl -w net.ipv4.ip_forward=1`), assigns IPs to all interfaces, adds static routes for PtP-connected remote subnets.
- **Hosts**: Assigns IP to home interface only; uses a default route via subnet gateway (not per-subnet routes, so PtP reply traffic from 10.255.0.x addresses works correctly).

**Container images:**

- Router/Firewall → `frrouting/frr:latest`
- Switch → `alpine:latest` (OVS image was dropped; it required host kernel modules)
- Everything else → `alpine:latest`

**Naming conventions:**

- Deployment name: `{topology_name}-{first_8_chars_of_id}` (must stay in sync with `utils/deploymentName.ts`)
- ContainerLab container name: `clab-{topology_name}-{container_id}`
- Management network: deterministic Docker network name + subnet from `172.16.0.0/12` space (+ IPv6 /64 from `3fff:172::/32`)

### App-Level Behaviors (`App.tsx`)

- `handleDeploy()` auto-saves the topology if `dirty` before generating YAML and deploying
- `handleLoad()` reconnects the WebSocket status stream if topology status is already `deployed`
- Navigation guards prevent going to a deleted site/subnet mid-session
- Students get a read-only view: `readOnly = auth?.role === 'student'` disables all edit controls and the Classroom/Browser panels
- On student login, `handleLogin()` immediately calls `handleLoad(assignedTopologyId)` to auto-load their topology

## Authentication & Roles

The app requires login before rendering. Two roles exist:

**Instructor** — token-based. The frontend calls `listTopologies()` to validate the token server-side. Token is sent as `Authorization: Bearer <token>` on all requests.

**Student** — join-code-based. `POST /api/classroom/login` exchanges a join code for a token (the join code itself serves as the bearer token) and returns the student's assigned `topology_id`.

Auth state (`AuthState` in `store/AuthContext.ts`): `{ role, token, assignedTopologyId }`.

Backend auth (`backend/auth.py`):

- `require_instructor` — validates bearer token against `INSTRUCTOR_TOKEN`
- `require_any_auth` — accepts instructor token or a valid student join code; returns `InstructorIdentity | StudentIdentity`
- `validate_student_topology(identity, topology_id)` — raises 403 if a student tries to access another topology

## Classroom Mode

Instructor-only feature for managing multi-student lab sessions. Accessible via the "Classroom" button in `ControlBar` (hidden from students).

### Data Model

```
ClassSession { id, name, template_id, created_at, updated_at }
StudentSlot  { id, session_id, topology_id, join_code, label, created_at }
```

- A `ClassSession` references a template topology and groups a set of `StudentSlot`s.
- Each `StudentSlot` owns a cloned topology (deep-copied from the template at instantiation) and a unique `join_code` (UUID hex) that students use to log in.

### Backend (`routers/classroom.py` — prefix `/api/classroom`)

| Method   | Path                             | Auth       | Description                                         |
| -------- | -------------------------------- | ---------- | --------------------------------------------------- |
| `POST`   | `/login`                         | public     | Student exchanges join code for token + topology_id |
| `GET`    | `/sessions`                      | instructor | List all sessions                                   |
| `POST`   | `/sessions`                      | instructor | Create a session (requires `template_id`)           |
| `GET`    | `/sessions/{id}`                 | instructor | Get session details                                 |
| `DELETE` | `/sessions/{id}`                 | instructor | Delete session and all its slots/topologies         |
| `POST`   | `/sessions/{id}/instantiate`     | instructor | Clone template N times, create StudentSlots (1–200) |
| `GET`    | `/sessions/{id}/slots`           | instructor | List slots for a session                            |
| `DELETE` | `/sessions/{id}/slots/{slot_id}` | instructor | Remove a single student slot                        |

Instantiation (`/instantiate`): deep-copies template topology data via `copy.deepcopy()`, creates a new `Topology` row named `"{session.name} — {label}"`, then creates a `StudentSlot` linking to it.

### Frontend (`components/ClassroomPanel.tsx`)

Two-level UI inside a `Dialog`:

**Session list view** — Create a new session (name + template topology dropdown), list existing sessions with Manage/Delete buttons.

**Session detail view** — Shows session name, template, created date. Sub-sections:

- _Add Students_: count (1–200) + label prefix → calls `instantiate` endpoint, marks new slots as `idle`
- _Student Slots_: lists all slots with label, join code, and live deployment status badge. Batch actions: **Copy All Codes** (copies label+code TSV to clipboard), **Deploy All** (sequential, skips already-deployed), **Destroy All** (sequential, skips already-idle). Per-slot: **Copy** (code to clipboard), **Del** (removes slot with confirm dialog).

Slot topology statuses are fetched via `getTopologyStatus()` on session open and updated optimistically after batch deploy/destroy operations.
