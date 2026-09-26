# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project Overview

AE3GIS v3 is an interactive network-topology editor and deployment platform.
A React drill-down editor (Network → Site → Subnet) drives a FastAPI backend
that instantiates topologies as live containers via **Kathara** (multi-arch,
unprivileged, Docker-SDK based — runs on Apple silicon). v3 is a ground-up
rebuild; ContainerLab has been fully removed.

Developer onboarding and the full architecture rationale live in
`docs/ARCHITECTURE.md`; keep it current when you change a layer boundary.

## Commands

```bash
./start.sh                                   # docker compose up (frontend :3000, backend :8000)
cd frontend && npm run dev                   # :5173
cd frontend && npm run build && npm run test # typecheck + vitest
cd frontend && npm run lint                  # eslint (CI gate)
cd backend && python -m pytest && ruff check . && ruff format --check .   # backend checks (CI)
cd backend && python -m uvicorn main:create_app --factory --reload --port 8000
cd backend && python scripts/export_openapi.py   # regenerate openapi.json after API changes
cd frontend && npm run api:types                 # regenerate src/api/schema.d.ts from it
```

Backend runs unprivileged with only the Docker socket mounted (no `sudo`, no
`privileged`, no host netns). Push to `main` → SSH deploy via `.github/workflows/deploy.yml`.

## Architecture

### Backend layout (`backend/`)
`main.create_app(settings, engine)` is the only entry point (uvicorn runs it
with `--factory`; tests build their own app with a temp SQLite file and a
`FakeEngine`). Nothing happens at import time.

- `config.py` — `Settings` (pydantic-settings, `AE3GIS_*` env). `api/deps.py`
  resolves settings, DB session, engine and job runner from `app.state`.
- `api/` — thin routers, **all under `/api/v1`**, one error envelope
  `{detail, code, …}` (`api/errors.py`). `openapi.json` at the backend root is
  generated from the app (`scripts/export_openapi.py`, checked in CI) and the
  frontend's TypeScript API types are generated from that file. Change an
  endpoint → regenerate both.
- `domain/` — pure logic over the opaque topology dict: `topology.py` (typed
  read helpers), `validation.py` (diagnostics; errors block deploy, warnings
  inform, **saves are never rejected**), `plan.py` (topology → `LabPlan`:
  gateway detection, `/30` router links from `10.255.0.0/24`, BFS static
  routes, per-role startup commands as plain iproute2/sysctl), `export/`
  (`LabPlan` → lab-spec JSON, Kathara `lab.conf` + startup files, ContainerLab
  `topo.clab.yml`; ContainerLab uses `iface_base=1`). Plan links carry their
  `connection_id`; `links.py` resolves capture targets against them. Also
  `pcap.py`/`packets.py` (pcap framing, packet summaries), `traffic/` (iperf3
  argv + json-stream parser, run summaries), `telemetry.py` (stats → rates),
  `environment.py` (run environment + fingerprint).
- `services/` — orchestration: `topologies` (CRUD, `version` bump, optimistic
  concurrency → 409 `version_conflict`), `deployment` (deploy/destroy as
  **jobs** with steps validate → images → plan → deploy → verify; a provisional
  `engine_state` is saved before the engine runs so failures clean up and leave
  `status=error`), `jobs` (`JobRunner`: in-process asyncio tasks, one per job
  **subject** — `topology:<id>`, `image:<ref>`, `source:<name>`,
  `capture:<topo>:<node>:<iface>`, `traffic:<topo>` — at a time; steps on the
  job row mirrored to events; per-job log files via `joblogs`; `wait`/`cancel`,
  and `request_stop` for `stoppable` kinds (winds down, keeps output, ends
  `succeeded`); `set_result` → `Job.result`; bulk output in `artifacts`
  (`data/artifacts/<job>/`)), `images` + `sources` (node images built from
  Dockerfiles, see below), `capture` + `traffic` (+ `traffic_generators`):
  sidecar jobs, see below; `live` (per-job WebSocket fan-out), `activity`
  (running captures/runs; destroy stops them first), `environment` (run
  metadata), `reconcile` (labs on the engine vs DB: tracked / orphan / stale;
  purge by lab hash), `events` (append-only log per topology).
- `db/` — SQLAlchemy models (`Topology`, `Job`, `Event`) and **Alembic**
  migrations run at startup (`db/migrations`). Add a migration for any schema
  change; `0001` is a baseline that tolerates pre-migration databases.
- `engine/` — the seam. `DeploymentEngine` takes a `LabPlan` and returns an
  `EngineState` (`lab_name`, `lab_hash`, `user_prefix`, node→machine map)
  stored in `Topology.engine_state`. `engine/kathara` deploys through the
  Kathara API but **observes through Docker labels** (`app=kathara`,
  `lab_hash`, `name`) so lookups don't depend on Kathara's per-user prefix.
  `engine/fake.py` is the in-memory engine (`AE3GIS_ENGINE=fake`) for tests
  and Docker-less UI work.

**Runtime invariants worth knowing.** Kathara derives its per-user prefix from
the backend's *hostname*; compose pins `hostname: ae3gis-backend` so labs stay
visible across container recreation. Lab names depend only on the topology id
(`ae3gis_<id[:12]>`), never the display name. Status polling is one
`GET /runtime` call (status + active job + nodes). `persistencePaths` and
`config` are stored but not applied by the Kathara engine (validation warns).

### Deployment engine (the key seam)
`backend/engine/base.py` defines `DeploymentEngine` (deploy/destroy/status/
resolve_container/node_logs/list_labs/purge/images_present/pull_image/
inspect_images/build_support/build_image, plus node_interfaces/start_sidecar/
list_sidecars/remove_sidecars/sample_stats/node_runtime_info/environment for
captures and traffic). Routers never
import an engine; services get it from `app.state`. Re-homing a deferred
feature (exec/script runner, packet capture, telemetry) = extend this
interface. Kathara's own `exec`/stats filter by its hostname-derived user
prefix, so new engine methods resolve containers by Docker labels (like
`resolve_container`) and call the Docker SDK directly.

- `engine/terminal.py` — engine-agnostic PTY↔WebSocket bridge (`docker exec`, no sudo).
- `engine/docker_sidecar.py` — sidecars: containers in a node's netns
  (`network_mode=container:`), log driver `none`, attached **before** start,
  labelled `ae3gis.sidecar/owner/lab_hash/node/job/purpose` (never
  `app=kathara`); Docker stats → `RawStats`. The tools image is
  `ae3gis.local/nettools` (`backend/tools/nettools/`, catalog `tools` map).
- `engine/docker_build.py` — `docker buildx build --load` (BuildKit) as a
  cancellable subprocess; the backend image ships `docker-buildx-plugin` + `git`.

### Node catalog (single source of truth)
`backend/catalog/node_types.json` (schema v2, validated by `catalog/models.py`
and served typed at `GET /api/v1/catalog`) defines ordered `categories`, image
`sources`, `images` (display name, `stability` stable|experimental|hidden,
`source` registry|build, optional `platforms`) and every node type: `role`
(router|switch|host), `defaultImage`, `images` (its **variants**), `color`,
`label`, `icon`, `category`, optional `webUiPort`/`purdueLevel`. **Images live
here as data, never hardcoded in source.** The frontend consumes it via
`src/catalog/` (colors, labels, icons via `catalog/icons.tsx`, layout rank via
`rankFor`, roles via `roleFor`, Purdue level via `purdueLevelFor`, and the one
category → type → variant grouping in `catalog/tree.ts`). `role` drives how the
engine configures a node; unknown types default to `host`. Adding a node type is
a single `node_types.json` edit (the palette, add menus, inspector type picker
and Purdue view all read the catalog). A container with no `image` follows its
type's default.

### Node images built from Dockerfiles
Images with a `build` source (refs under `ae3gis.local/`, which fails closed
rather than pulling from Docker Hub) are built by AE3GIS from a Dockerfile in a
catalog `source`: a git repo cloned into `data/sources/<name>` on first use and
refreshed by an explicit sync job (`AE3GIS_SOURCE_OVERRIDES` maps a source to a
local checkout). Builds are jobs (`source → snapshot → build → verify`), deduped
per image, limited by `AE3GIS_MAX_CONCURRENT_BUILDS`. Each image carries a
fingerprint label (sha256 of its build context + Dockerfile path + args,
`domain/images.py`); status = that label vs the current source (ready / stale /
missing / building / failed / unmanaged / unavailable), computed on demand,
never at startup. A deploy's `images` step builds missing images (joining
running builds) and deploys stale ones with a `deploy.images_stale` warning.
Kathara runs each image's own `CMD`; AE3GIS addressing follows from
`/ae3gis-init.sh` (log: `/var/log/ae3gis-init.log`).

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

**DB:** SQLite via Alembic. `Topology.data` (JSON) holds the topology,
`Topology.engine_state` the engine's bookkeeping, `Topology.version` the
revision. Status lifecycle: `idle → deploying → deployed → destroying → idle`,
any failure → `error` (destroy from `error` cleans up). `jobs` and `events`
tables record every long operation.

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
  `expanded`, theme, tool, panels, zoom, collapsed palette categories),
  `dock` (typed dock tabs: terminal | capture | traffic; `openTerminal` wraps
  it), `activity` (running captures/traffic runs from `/runtime`), `catalog`,
  `images` (GET /images report, kept fresh by the
  `features/images/imagePolling` singleton).
  Undo/redo via zundo (`undo()`/`redo()` in `store/index.ts`; only `topology` is
  tracked; load/new reset history). UI prefs persist to `localStorage`
  (`ae3gis.ui`). `normalizeTopology()` (`store/normalize.ts`) runs on every
  load/import: fills connection ids and node positions so old JSON keeps working;
  a load that had to fill connection ids starts dirty (deployed links are
  addressed by id).
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
  tree), Inspector (context-sensitive forms that commit on blur), Dock
  (`features/dock`: terminal / capture / traffic tabs, bodies lazy-loaded and kept
  mounted), StatusBar, CommandPalette (⌘K),
  Breadcrumb. `features/topology/AddEntityProvider` owns every "add…" dialog so
  toolbar, palette, menus and drops share one flow. Deployment actions are plain
  functions in `features/deployment/actions.ts`; status polling is a singleton.
  Images: `features/images` (ImagesSheet, variant `ImagePicker`, status line,
  `RequiredImagesBanner` over the canvas, build/sync/cancel actions);
  `features/jobs/JobLog` follows any job's log; the TopBar status badge opens
  `JobDetailsPopover` (steps + deploy/build logs).
  Capture: `features/capture` (StartCaptureDialog from edge/device menus and the
  inspector, CaptureView = live windowed packet table over the capture
  WebSocket, pcap download, "Open in Wireshark" curl commands). Traffic:
  `features/traffic` (flow form, flows saved in `topology.traffic.flows`, live
  charts via `ui/charts/TimeSeriesChart` on uPlot with `--chart-N` tokens, run
  summary + environment). `features/runs/RunsSheet` lists captures and runs.
  The canvas badges captured links / busy nodes from the `activity` slice via
  `project({… activity})`.
- **Data model** (`types/topology.ts`) is frontend-owned; keep the index
  signatures so unknown backend fields round-trip. All REST/WS calls go through
  `api/client.ts`.
- **Tests:** vitest + Testing Library (`src/test/setup.ts` mocks ResizeObserver
  etc. for React Flow). Pure logic (store, projection, layout, validation) has
  unit tests; add one when touching `projection.ts` or a slice.

### API surface (`/api/v1`, see `backend/openapi.json`)
- `topologies` — CRUD (+`version`), `import-json`, `validate` (body or stored),
  `plan`, `export?format=labspec|kathara|containerlab`, `runtime`, `events`,
  `context` (everything in one call: record, diagnostics, plan, runtime, events).
- `topologies/{id}/deploy|destroy` → 202 with a job; `jobs/{id}`,
  `jobs/{id}/log?offset=`, `jobs/{id}/cancel`, `jobs/{id}/stop`,
  `jobs/{id}/artifacts[/{name}]`; `topologies/{id}/jobs`, `topologies/{id}/interfaces`;
  WebSocket `topologies/ws/{id}/exec/{container}`.
- `topologies/{id}/captures`, `captures/{id}`, `captures/{id}/pcap?follow=`
  (whole-record pcap, live for `curl … | wireshark -k -i -`), `captures/{id}/packets`;
  `topologies/{id}/traffic/runs`, `traffic/runs/{id}[/samples|/export]`;
  WebSockets `topologies/ws/{id}/captures/{job}` and `…/traffic/{job}`
  (under the WS prefix so nginx/vite upgrade them; handlers race every wait
  against client disconnect, see `api/live_ws.py`).
- `images?topology_id=` (build support, sources, per-image status),
  `images/builds` (202 + build jobs), `sources/{name}/sync` (202 + a job).
- `system` — `health`, `labs` (reconcile report), `environment`, `reconcile`,
  `labs/{hash}/purge`.
- `catalog`, `presets` as before.

## Auth
**Opt-in, and off by default.** There is no sign-in screen. `AE3GIS_INSTRUCTOR_TOKEN`
unset or empty (the compose default) leaves the API open — fine for a local lab,
unsafe on a shared or reachable host, since the API creates and destroys
containers. Setting it re-enables the bearer check on every REST route and on the
exec WebSocket (which takes the token as `?token=`); the frontend then needs a
matching `VITE_INSTRUCTOR_TOKEN` at build time (a compose build arg). `auth.py`
reads the token from `app.state.settings`, so a test app carries its own.
Student/classroom auth is still deferred.

## Deferred (rebuild on the engine abstraction later)
Firewall editor, scenarios/scripts, classroom mode, web-UI proxy, AI assistant,
more traffic generators (Locust, Modbus) and comparison views. Keep the `DeploymentEngine` seam and the catalog when adding them back.
