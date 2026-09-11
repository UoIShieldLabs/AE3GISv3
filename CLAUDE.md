# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project Overview

AE3GIS v3 is an interactive network-topology editor and deployment platform.
A React drill-down editor (Geographic → Subnet → LAN) drives a FastAPI backend
that instantiates topologies as live containers via **Kathara** (multi-arch,
unprivileged, Docker-SDK based — runs on Apple silicon). v3 is a ground-up
rebuild; ContainerLab has been fully removed.

## Commands

```bash
./start.sh                                   # docker compose up (frontend :3000, backend :8000)
cd frontend && npm run dev                   # :5173
cd frontend && npm run build && npm run test # typecheck + vitest
cd backend && python -m pytest               # backend tests
cd backend && python -m uvicorn main:app --reload --port 8000
```

Backend runs unprivileged with only the Docker socket mounted (no `sudo`, no
`privileged`, no host netns). Push to `main` → SSH deploy via `.github/workflows/deploy.yml`.

## Architecture

### Deployment engine (the key seam)
`backend/engine/base.py` defines `DeploymentEngine` (deploy/destroy/status/
resolve_container). Routers depend only on this and speak `TopologyData` + node
ids. `engine/kathara/` implements it via the Kathara Python API. Re-homing a
deferred feature = extend this interface, not the routers.

- `engine/networking.py` — **pure, unit-tested** topology → `LabPlan` logic:
  gateway detection, interface assignment, `/30` point-to-point router links
  from `10.255.0.0/24`, BFS static-route propagation, and per-role startup
  commands (router = ip_forward + routes; switch = linux bridge; host = IP +
  default route). Emits plain iproute2/sysctl commands (engine-agnostic).
- `engine/kathara/lab_builder.py` — `LabPlan` → Kathara `Lab`: one collision
  domain per point-to-point link, image from the catalog, startup commands
  written to `/ae3gis-init.sh` and run via the machine `exec` meta.
- `engine/terminal.py` — engine-agnostic PTY↔WebSocket bridge (`docker exec`, no sudo).

### Node catalog (single source of truth)
`backend/catalog/node_types.json` defines every node type: `role`
(router|switch|host), `defaultImage`, `images`, `color`, `label`, `icon`,
`category`, optional `webUiPort`/`purdueLevel`. **Images live here as data, never
hardcoded in source.** Served at `GET /api/catalog`; the frontend consumes it via
`src/catalog/` (colors, labels, icons via `catalog/icons.tsx`, layout rank via
`rankFor`). `role` drives how the engine configures a node; unknown types default
to `host`. Adding a node type should be a single `node_types.json` edit. (One
holdout: `PurdueView` still classifies zones/levels with local logic.)

### Data model — the frontend is decoupled from the backend schema
There is **no shared topology schema**. The backend persists and serves topology
`data` as **opaque JSON** (`schemas.py` types only the API envelope:
`TopologyCreate/Update/Record/Summary`, all with `data: dict`); it does NOT model
the internal shape and never strips unknown fields. The frontend owns its own view
of that data in `frontend/src/types/topology.ts` (with an index signature so
unknown backend fields round-trip). Either side can add/rename/drop fields with no
change to the other. The deployment engine reads the fields it needs defensively.
The only cross-tier contracts are the API envelope and the catalog. Do not
reintroduce a Pydantic mirror of the topology.

**DB:** SQLite. `Topology.data` (JSON) holds the topology; `Topology.engine_state`
(JSON) holds opaque per-deploy engine state (Kathara lab name + node map).
Status lifecycle: `idle` → `deployed` → `idle`.

### Frontend
`App.tsx` is thin: navigation + wiring. Orchestration lives in `hooks/`
(`useDeployment`, `useStatusPolling`, `useTerminalSessions`). State is an Immer
reducer (`store/topologyReducer.ts`); `dirty` tracks unsaved changes and every
mutating action sets it except `UPDATE_CONTAINER_STATUSES`. `ADD_SUBNET`
auto-creates a router + switch; `ADD_INTER_SUBNET_CONNECTION` auto-creates
gateway routers. All REST/WS calls go through `api/client.ts`.

### Backend routers
- `routers/topologies.py` — CRUD + JSON import (`/api/topologies`)
- `routers/deployment.py` — deploy/destroy/status + exec-terminal WebSocket
- `routers/catalog.py` — `GET /api/catalog`
- `routers/presets.py` — templates from `backend/presets/*.json`

## Auth
Instructor-only (bearer token vs `AE3GIS_INSTRUCTOR_TOKEN`, default `test`).
WebSockets take the token as `?token=`. Student/classroom auth is deferred.

## Deferred (rebuild on the engine abstraction later)
Firewall editor, scenarios/scripts, classroom mode, Wireshark capture, web-UI
proxy, AI assistant. Keep the `DeploymentEngine` seam and the catalog when adding them back.
