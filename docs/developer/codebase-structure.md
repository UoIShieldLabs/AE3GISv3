# AE3GIS Codebase Structure

**Audience:** Engineers reading or contributing to AE3GIS.

---

## 1. Repository Layout

```
AE3GISv2/
├── docker-compose.yml          # Service definitions, volumes, env vars
├── .env                        # Local environment variables (not committed)
├── .github/
│   └── workflows/
│       └── deploy.yml          # SSH-based CD pipeline
├── backend/
│   ├── main.py                 # FastAPI app factory, router mounts, CORS
│   ├── auth.py                 # Token validation, identity types
│   ├── config.py               # Env var loading (AE3GIS_* prefix)
│   ├── database.py             # SQLAlchemy engine, session factory
│   ├── models.py               # ORM models: Topology, ClassSession, StudentSlot
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── routers/
│   │   ├── topologies.py       # CRUD: /api/topologies
│   │   ├── containerlab.py     # Deploy/destroy/exec/scenarios: /api/containerlab
│   │   ├── classroom.py        # Sessions + slots: /api/classroom
│   │   ├── presets.py          # Preset templates: /api/presets
│   │   └── proxy.py            # HTTP reverse proxy: /api/proxy
│   ├── services/
│   │   ├── clab_generator.py   # TopologyData dict → ContainerLab YAML string
│   │   ├── clab_manager.py     # Deploy/destroy/inspect/firewall via subprocess
│   │   └── clab_importer.py    # .clab.yml → TopologyData (import flow)
│   ├── presets/
│   │   └── stuxnet.json        # Stuxnet ICS attack scenario preset
│   └── scripts/                # Shell scripts bind-mounted into containers
│       ├── router/             # FRRouting config helpers
│       ├── firewall/           # iptables helpers
│       ├── server/             # Generic server scripts
│       ├── workstation/        # Workstation scripts
│       └── switch/             # Switch (bridge) scripts
└── frontend/
    ├── index.html
    ├── vite.config.ts          # Dev server proxy (:5173 → :8000)
    ├── src/
    │   ├── App.tsx             # Root component: navigation state, deploy logic
    │   ├── index.css           # Global styles including header-bar grid
    │   ├── api/
    │   │   └── client.ts       # All fetch wrappers + auth token management
    │   ├── store/
    │   │   └── topologyReducer.ts  # Immer reducer, all action types
    │   ├── components/
    │   │   ├── GeographicView.tsx   # Site-level map (level 0)
    │   │   ├── SubnetView.tsx       # Subnet-level graph (level 1)
    │   │   ├── LanView.tsx          # Container-level graph (level 2)
    │   │   ├── ControlBar.tsx       # New/Save/Load/Export controls
    │   │   ├── ScenarioPanel.tsx    # Attack scenario builder + executor
    │   │   ├── ClassroomPanel.tsx   # Session/slot management
    │   │   ├── PurdueModelView.tsx  # Purdue model zone/level visualization
    │   │   ├── TerminalPanel.tsx    # xterm.js terminal tabs
    │   │   ├── FirewallRuleDialog.tsx  # Firewall rule editor
    │   │   └── ...
    │   ├── utils/
    │   │   ├── autoLayout.ts       # Dagre/circle/zigzag/grid layout algorithms
    │   │   ├── deploymentName.ts   # Deterministic deployment name calculation
    │   │   └── ...
    │   └── types.ts                # Shared TypeScript interfaces
```

---

## 2. Frontend Architecture

### Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| React | 19 | UI framework |
| ReactFlow | 11 | Graph canvas for subnet/LAN views |
| Immer | 10 | Immutable state updates in reducer |
| xterm.js | 5 | Terminal emulator |
| dagre | 0.8 | Graph layout engine |
| Vite | 5 | Build tool + dev server |
| TypeScript | 5 | Type safety |

### Three-Level Navigation

AE3GIS uses a drill-down navigation model controlled by `NavigationState` in `App.tsx`:

```typescript
type ViewScale = 'geographic' | 'subnet' | 'lan';

interface NavigationState {
  view: ViewScale;
  siteId?: string;     // set when drilling into a site
  subnetId?: string;   // set when drilling into a subnet
}
```

| Level | Component | How to enter | How to exit |
|-------|-----------|--------------|-------------|
| Geographic | `GeographicView` | App start | — |
| Subnet | `SubnetView` | Click a site node | Breadcrumb |
| LAN | `LanView` | Click a subnet cloud | Breadcrumb |

### State Management

State is managed with an Immer reducer in `store/topologyReducer.ts`.

**`TopologyState` shape:**

```typescript
interface TopologyState {
  topology: TopologyData;
  dirty: boolean;               // true = unsaved changes
  backendId: string | null;     // topology UUID from backend
  backendName: string | null;
  deployStatus: DeployStatus;   // 'idle' | 'deploying' | 'deployed' | 'destroying'
}
```

**Dirty flag rules:**
- Set to `true` by every action that modifies topology content
- The **only** exception: `UPDATE_CONTAINER_STATUSES` does not set `dirty` (status is transient runtime data)
- Cleared by `MARK_CLEAN` (after save) and `LOAD_TOPOLOGY`
- `handleDeploy()` in `App.tsx` auto-saves if `dirty` before deploying

**Key action side effects:**

| Action | Side effect |
|--------|-------------|
| `ADD_SUBNET` | Auto-creates a router + switch at the first two available IPs in the CIDR, wires them together |
| `ADD_INTER_SUBNET_CONNECTION` | Auto-creates gateway routers in both subnets if none exist |
| `LOAD_TOPOLOGY` | Must NOT mutate existing container objects — causes blank-screen crash |
| `CLEAR_CONTAINER_STATUSES` | Sets `status = 'stopped'` on all containers (not `undefined`) so red dot always renders |

### Component Map

| File | Purpose |
|------|---------|
| `App.tsx` | Root: navigation state, deploy/destroy, header bar right-hand controls |
| `GeographicView.tsx` | ReactFlow canvas showing sites as nodes, inter-site connections as edges |
| `SubnetView.tsx` | ReactFlow canvas showing subnet clouds + router nodes within a site |
| `LanView.tsx` | ReactFlow canvas showing containers within a subnet |
| `ControlBar.tsx` | New/Save/Load/Export buttons + save dialog; lives in header bar left column |
| `ScenarioPanel.tsx` | Scenario/phase builder, single-topology + batch execution (instructor only) |
| `ClassroomPanel.tsx` | Session creation, slot instantiation, join code display, batch deploy |
| `PurdueModelView.tsx` | Read-only Purdue model overlay (auto-classifies zones and levels) |
| `TerminalPanel.tsx` | xterm.js tabs, one WebSocket per container, minimize/restore |
| `FirewallRuleDialog.tsx` | iptables rule editor for router/firewall containers |

### Auto-Layout Algorithms

All algorithms live in `utils/autoLayout.ts` and return `Map<nodeId, {x, y}>`.

| Function | Mode | Description |
|----------|------|-------------|
| `computeLayout` | Tree (dagre) | Dagre y-positions + custom subtree-centering for x. Used in SubnetView Tree mode. |
| `computeZigzagLayout` | Zigzag | Alternates subnet clouds left/right columns (`xLeft=80`, `xRight=460`, `yStep=210`). Prevents vertical overlap between router-below-cloud and next cloud. |
| `computeCircleLayout` | Circle | Most-connected nodes at center, others on ring. Supports `nodePriority` map. |
| `computeGridLayout` | Grid | `ceil(sqrt(n))` columns, configurable `spacing` (default 60). |

SubnetView router nodes are positioned `{ x: 55, y: 150 }` below their parent subnet cloud (constant `ROUTER_OFFSET`).

### API Client Conventions

All backend communication goes through `api/client.ts`.

- **Auth header:** Every request includes `Authorization: Bearer <token>` via a module-level token stored with `setAuthToken()` / `getAuthToken()`
- **WebSocket auth:** Browsers cannot set headers on WebSocket upgrades, so the token is passed as a query parameter: `wsUrl(path)` appends `?token=<token>`
- **No direct fetch calls** outside `client.ts` — all API calls go through the typed wrapper functions

---

## 3. Backend Architecture

### Tech Stack

| Library | Purpose |
|---------|---------|
| FastAPI | HTTP framework + OpenAPI docs |
| SQLAlchemy | ORM + database session management |
| SQLite | Embedded relational database |
| Pydantic v2 | Request/response validation and serialization |
| `pty` (stdlib) | Pseudo-terminal for WebSocket exec sessions |

### SQLAlchemy Models (`models.py`)

**`Topology`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | String (UUID) | Primary key, generated at creation |
| `name` | String | Display name |
| `status` | String | `idle` or `deployed` |
| `data` | JSON | Full `TopologyData` dict |
| `clab_yaml` | Text | Last-generated ContainerLab YAML |
| `created_at` | DateTime | Auto-set |
| `updated_at` | DateTime | Auto-updated |

**`ClassSession`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | String (UUID) | Primary key |
| `name` | String | Display name |
| `template_id` | String | FK → `Topology.id` (template used for instantiation) |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

**`StudentSlot`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | String (UUID) | Primary key |
| `session_id` | String | FK → `ClassSession.id` |
| `topology_id` | String | FK → `Topology.id` (deep-copied instance) |
| `join_code` | String | UUID used as bearer token + login code |
| `label` | String \| null | Optional display label (e.g. "Student 1") |
| `created_at` | DateTime | |

### TypeScript Data Model Hierarchy

```
TopologyData
  name?: string
  sites: Site[]
  siteConnections: Connection[]
  scenarios?: Scenario[]

Site
  id, name, location
  position: { x, y }
  subnets: Subnet[]
  subnetConnections: Connection[]

Subnet
  id, name, cidr
  gateway?: string
  containers: Container[]
  connections: Connection[]

Container
  id, name, type, ip
  kind?: string
  image?: string
  status?: 'running' | 'stopped' | 'paused'
  metadata?: Record<string, unknown>

Connection
  from, to
  label?: string
  fromInterface?, toInterface?
  fromContainer?, toContainer?

Scenario
  id, name, description?
  phases: AttackPhase[]

AttackPhase
  id, name, description?
  executions: ScriptExecution[]

ScriptExecution
  containerId, script, args?
```

### Container Type → Docker Image

| Container type | Docker image |
|----------------|-------------|
| `router` | `frrouting/frr:latest` |
| `firewall` | `frrouting/frr:latest` |
| `switch` | `alpine:latest` |
| `web-server` | `httpd:alpine` |
| `workstation` | `alpine:latest` |
| `file-server` | `alpine:latest` |
| `plc` | `alpine:latest` |

---

## 4. API Reference

### Topologies — `/api/topologies`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/topologies` | Any | List all topologies (summary) |
| `POST` | `/api/topologies` | Instructor | Create a new topology |
| `POST` | `/api/topologies/import` | Instructor | Import topology from `.clab.yml` file |
| `GET` | `/api/topologies/{id}` | Any | Get full topology record |
| `PUT` | `/api/topologies/{id}` | Instructor | Update topology name and/or data |
| `DELETE` | `/api/topologies/{id}` | Instructor | Delete topology |

### ContainerLab — `/api/containerlab`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/containerlab/scripts/available` | Instructor | List available scripts with container type compatibility |
| `POST` | `/api/containerlab/{id}/generate` | Instructor | Generate and preview ContainerLab YAML |
| `POST` | `/api/containerlab/{id}/deploy` | Instructor | Deploy topology via ContainerLab |
| `POST` | `/api/containerlab/{id}/destroy` | Instructor | Destroy deployed topology |
| `GET` | `/api/containerlab/{id}/status` | Any | Poll container statuses (HTTP) |
| `WS` | `/api/containerlab/ws/{id}/exec/{container_id}` | Any | PTY terminal session |
| `GET` | `/api/containerlab/{id}/exec/{container_id}/precheck` | Any | Validate terminal access before connecting |
| `POST` | `/api/containerlab/{id}/scenarios/{scenario_id}/phases/{phase_id}/execute` | Instructor | Execute an attack phase |
| `GET` | `/api/containerlab/{id}/firewall/{container_id}` | Instructor | Get managed firewall rules |
| `PUT` | `/api/containerlab/{id}/firewall/{container_id}` | Instructor | Replace managed firewall rules |

### Classroom — `/api/classroom`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/classroom/login` | None | Exchange student join code for bearer token |
| `GET` | `/api/classroom/sessions` | Instructor | List all class sessions |
| `POST` | `/api/classroom/sessions` | Instructor | Create a new session |
| `GET` | `/api/classroom/sessions/{id}` | Instructor | Get session details |
| `DELETE` | `/api/classroom/sessions/{id}` | Instructor | Delete session and all slots |
| `POST` | `/api/classroom/sessions/{id}/instantiate` | Instructor | Create student slots (deep-copies template topology) |
| `GET` | `/api/classroom/sessions/{id}/slots` | Instructor | List all slots in a session |
| `DELETE` | `/api/classroom/sessions/{id}/slots/{slot_id}` | Instructor | Delete a single slot |
| `POST` | `/api/classroom/sessions/{id}/execute-phase` | Instructor | Batch execute attack phase across all slots |

### Presets — `/api/presets`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/presets` | Any | List available preset templates |
| `GET` | `/api/presets/{id}` | Any | Get full preset data |
| `POST` | `/api/presets/{id}/load` | Instructor | Create a new topology from a preset |

### Proxy — `/api/proxy`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `ANY` | `/api/proxy/{topology_id}/{container_id}/{path}` | Any | Reverse proxy HTTP to container management IP |

---

## 5. YAML Generation Pipeline

`clab_generator.py` converts a `TopologyData` dict into a ContainerLab YAML string. The pipeline runs in order:

1. **Gateway detection** — If `subnet.gateway` is not set, the first router or firewall container in the subnet is used as the gateway. A `subnet_id → gateway_router_id` map is built for later reference.

2. **Interface pre-registration** — Explicit `fromInterface`/`toInterface` values in connections are registered first to prevent auto-assignment from colliding with them.

3. **Interface auto-assignment** — Remaining connections get `eth{N}` names via `_next_iface(counter)`. The counter is per-container, starting at `eth0` (or after any pre-registered names).

4. **ID resolution** — Connections that reference subnet IDs or site IDs (cross-subnet links) are resolved to actual container IDs via the gateway router map.

5. **IP assignment for cross-subnet links** — Router-to-router links across subnets get `/30` point-to-point addresses from `10.255.0.0/24`, allocated sequentially:
   - Link 1: `10.255.0.1/30` ↔ `10.255.0.2/30`
   - Link 2: `10.255.0.5/30` ↔ `10.255.0.6/30`
   - …up to ~63 cross-subnet links

6. **Static route injection** — Each router receives a static route to the peer subnet via the PtP link address.

7. **Exec configs per container type:**
   - **Switch:** Creates Linux bridge `br0`, adds all non-home interfaces, assigns IP on bridge
   - **Router/Firewall:** Sets `ip_forward=1`, assigns IPs on all interfaces, injects static routes
   - **Host:** Assigns IP on the home interface only, sets default route via subnet gateway

8. **Script bind-mounts** — Each container type has a corresponding subdirectory in `backend/scripts/`. The directory is bind-mounted read-only at `/scripts/<type>` inside the container, using `AE3GIS_HOST_SCRIPTS_DIR` as the host base path.

---

## 6. Naming Conventions

Two naming rules must stay **in sync** between `frontend/src/utils/deploymentName.ts` and `backend/services/clab_manager.py`:

**Deployment name** (used as the ContainerLab topology name):
```
{topology_name}-{first_8_chars_of_topology_id}
```

**Container name** (used by `docker exec` and `docker ps` filtering):
```
clab-{deployment_name}-{container_id}
```

Examples:
- Topology name: `my-lab`, ID: `abc12345-...` → deployment name: `my-lab-abc12345`
- Container ID: `router-1` → full container name: `clab-my-lab-abc12345-router-1`

Breaking this contract causes deploy/status/terminal failures. If you change the naming logic, update both files simultaneously.

---

## 7. Status Polling

Container status is polled via HTTP, not WebSocket (a WebSocket status endpoint exists but is deprecated).

**Why HTTP polling:**
- `containerlab inspect` fails silently in production environments
- `docker ps -a --filter name=clab-<topo_name>- --format "{{.Names}}\t{{.State}}"` is reliable and returns accurate Docker state

**Poll interval:** 5 seconds, managed in `App.tsx` via `setInterval`/`clearInterval` (wrapped as `connectWebSocket`/`disconnectWebSocket` for API compatibility).

**State mapping:**

| Docker state | Frontend status |
|-------------|-----------------|
| `running` | `running` (green dot) |
| `exited` | `stopped` (red dot) |
| `paused` | `stopped` (red dot) |
| `created` | `stopped` (red dot) |
| `restarting` | `stopped` (red dot) |

On `LOAD_TOPOLOGY`, `CLEAR_CONTAINER_STATUSES` is always dispatched first, setting all containers to `stopped` before polling begins. This ensures dots render immediately (red) rather than being invisible.

---

## 8. Authentication Flow

### Instructor

1. User enters token in login dialog
2. Frontend calls no login endpoint — token is stored in memory via `setAuthToken()`
3. Every request includes `Authorization: Bearer <token>`
4. Backend validates against `INSTRUCTOR_TOKEN` env var in `auth.py`

### Student

1. User enters join code (UUID) in login dialog
2. Frontend calls `POST /api/classroom/login` with `{ join_code }`
3. Backend validates join code against `StudentSlot.join_code` in the database
4. Returns `{ role: 'student', token: <join_code>, topology_id: <uuid> }`
5. Frontend stores token via `setAuthToken()`, stores `topology_id` in app state
6. Student is locked to that topology — backend returns 403 for any other topology ID
7. Student UI is read-only: no New/Save/Deploy/Destroy/Classroom buttons

---

## 9. Scripts Directory

Scripts are shell scripts bind-mounted into containers at deploy time.

```
backend/scripts/
├── router/          # FRRouting configuration helpers
├── firewall/        # iptables rule management
├── server/          # Generic server-side scripts (used by web-server, file-server, plc)
├── workstation/     # Workstation scripts
└── switch/          # Linux bridge / switch scripts
```

The `AE3GIS_HOST_SCRIPTS_DIR` env var must point to this directory on the **host** (not inside the container), because ContainerLab resolves bind mount paths against the host Docker daemon.

Container type → script subdirectory mapping:

| Container type | Script directory |
|----------------|-----------------|
| `workstation` | `workstation/` |
| `web-server` | `server/` |
| `file-server` | `server/` |
| `plc` | `server/` |
| `router` | `router/` |
| `firewall` | `firewall/` |
| `switch` | `switch/` |

Scripts are available at `/scripts/<type>/` inside containers after deploy.

---

## 10. Presets

Presets are JSON files in `backend/presets/`. Each file is a self-contained topology + scenario template.

**File format:**

```json
{
  "name": "Human-readable name",
  "description": "One-paragraph description",
  "topology": { ...TopologyData... },
  "scenarios": [ ...Scenario[] ... ]
}
```

To add a new preset, drop a `.json` file into `backend/presets/`. The `GET /api/presets` endpoint automatically discovers it — no code changes needed.

The `stuxnet.json` preset is the reference example: it includes a Corporate, DMZ, and OT/SCADA site with full Stuxnet kill-chain scenario phases.
