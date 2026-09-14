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
cd frontend && npm run lint                  # eslint (CI gate)
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
`rankFor`, roles via `roleFor`, Purdue level via `purdueLevelFor`). `role` drives
how the engine configures a node; unknown types default to `host`. Adding a node
type is a single `node_types.json` edit (the palette, add menus, inspector type
picker and Purdue view all read the catalog).

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

### Frontend (`frontend/src`, feature-based)
- **Design system.** Tailwind v4 + Radix primitives in `ui/` (Button, Dialog,
  Sheet, menus, Select/Combobox, Tabs, Resizable…). Colors are semantic tokens in
  `styles/tokens.css` (light on `:root`, dark on `[data-theme=dark]`), mapped to
  utilities via `@theme inline` in `styles/index.css`. Never hardcode colors;
  catalog colors are only used as device accents. `styles/reactflow.css` themes
  React Flow through its `--xy-*` variables. A DEV-only `/_gallery` route shows
  every primitive in both themes.
- **State.** One Zustand store (`store/index.ts`) composed of slices
  (`store/slices/`): `topology` (data + `dirty`, all mutations; id-based actions
  like `updateContainer`, `addConnection`, `deleteItems`, `moveNodes`,
  `applyLayout`), `document` (backend id, deploy status, **runtime container
  status lives here, never in the saved data**, `busy`), `view` (selection,
  `expanded`, theme, tool, panels, zoom), `terminal`, `catalog`, `auth`.
  Undo/redo via zundo (`undo()`/`redo()` in `store/index.ts`; only `topology` is
  tracked; load/new reset history). UI prefs persist to `localStorage`
  (`ae3gis.ui`). `normalizeTopology()` (`store/normalize.ts`) runs on every
  load/import: fills connection ids and node positions so old JSON keeps working.
- **Routing.** react-router: `/login`, `/` (library), `/t/draft`,
  `/t/:id`, `/t/:id/site/:siteId`, `/t/:id/site/:siteId/subnet/:subnetId`. The
  URL is the single source of truth for the drill-down **scope**
  (`lib/topology.ts: Scope`). `RequireAuth` restores the sessionStorage token.
- **Canvas** (`canvas/`). One `TopologyCanvas` for every level. `projection.ts`
  is a pure function `project({topology, scope, expanded, containerStatus,
  selection}) → {nodes, edges}`: it renders the children of the scope, draws
  ids in `expanded` as group nodes with their children inside (so 1/2/3 visible
  levels come from the same data), re-targets inter-subnet/site edges to the
  gateway routers when both ends are expanded, and keeps stable edge ids from
  `Connection.id`. Positions are stored per entity (`position` on site/subnet/
  container; container positions are subnet-relative). Edges are *floating*
  (`edges/geometry.ts`), node cards are catalog-driven (`nodes/DeviceNode.tsx`).
  Interactions: `interactions/useCanvasHotkeys.ts`, DnD payload in
  `interactions/dnd.ts`, context menu in `CanvasContextMenu.tsx`.
- **Shell** (`shell/`): TopBar, Sidebar (Palette with drag-and-drop, Explorer
  tree), Inspector (context-sensitive forms that commit on blur), TerminalDock
  (`features/terminal`, xterm lazy-loaded), StatusBar, CommandPalette (⌘K),
  Breadcrumb. `features/topology/AddEntityProvider` owns every "add…" dialog so
  toolbar, palette, menus and drops share one flow. Deployment actions are plain
  functions in `features/deployment/actions.ts`; status polling is a singleton.
- **Data model** (`types/topology.ts`) is frontend-owned; keep the index
  signatures so unknown backend fields round-trip. All REST/WS calls go through
  `api/client.ts`.
- **Tests:** vitest + Testing Library (`src/test/setup.ts` mocks ResizeObserver
  etc. for React Flow). Pure logic (store, projection, layout, validation) has
  unit tests; add one when touching `projection.ts` or a slice.

### Backend routers
- `routers/topologies.py` — CRUD + JSON import (`/api/topologies`)
- `routers/deployment.py` — deploy/destroy/status + exec-terminal WebSocket
- `routers/catalog.py` — `GET /api/catalog`
- `routers/presets.py` — templates from `backend/presets/*.json`

## Auth
**Opt-in, and off by default.** There is no sign-in screen. `AE3GIS_INSTRUCTOR_TOKEN`
unset or empty (the compose default) leaves the API open — fine for a local lab,
unsafe on a shared or reachable host, since the API creates and destroys
containers. Setting it re-enables the bearer check on every REST route and on the
exec WebSocket (which takes the token as `?token=`); the frontend then needs a
matching `VITE_INSTRUCTOR_TOKEN` at build time (a compose build arg). `auth.py`
reads `config.INSTRUCTOR_TOKEN` at call time so tests can patch it.
Student/classroom auth is still deferred.

## Deferred (rebuild on the engine abstraction later)
Firewall editor, scenarios/scripts, classroom mode, Wireshark capture, web-UI
proxy, AI assistant. Keep the `DeploymentEngine` seam and the catalog when adding them back.
