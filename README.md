# AE3GIS v3

Interactive network-topology editor and deployment platform. Design multi-site
topologies through a three-level drill-down (Geographic → Subnet → LAN) and
deploy them as live containers via **Kathara**.

> **v3 foundation.** This is a ground-up rebuild. ContainerLab has been removed
> and deployment re-implemented on Kathara, which runs unprivileged and
> multi-arch — including Apple silicon. This pass ships the clean **core**
> (editor + deploy/destroy/status + interactive terminal); several v2 features
> are intentionally deferred (see [Deferred](#deferred-features)).

## Architecture

- **Frontend** — React + TypeScript + Vite, Tailwind v4 + Radix UI, Zustand
  store with undo/redo, react-router URLs for the drill-down scope, one React Flow
  canvas that projects the topology at any depth (sites/subnets can be expanded in
  place). Light and dark themes.
- **Backend** — FastAPI under `/api/v1` with a service layer, Alembic
  migrations, persisted deploy/destroy jobs with step-by-step progress, backend
  validation (diagnostics), a computed lab plan, lab export (JSON spec, Kathara
  lab, ContainerLab topology) and reconcile/purge of labs on the host. A
  `DeploymentEngine` abstraction isolates the orchestrator; `KatharaEngine`
  is the real one, `FakeEngine` runs the UI without Docker.
- **Deployment** — Kathara talks to the Docker daemon via its SDK and models
  each link as a Docker bridge network. No `sudo`, no host network namespace,
  no privileged container.
- **Node catalog** — `backend/catalog/node_types.json` is the single source of
  truth for node types, their default images, colours, labels, and icons.
  Images are **data**, served to the frontend at `GET /api/catalog`. Change the
  image set by editing that file — no code changes.

```
backend/
  main.py                   # create_app() factory (uvicorn --factory)
  api/                      # /api/v1 routers, schemas, error envelope
  services/                 # topologies, deployment jobs, reconcile, events
  domain/                   # validation, lab plan, exporters (pure, tested)
  engine/                   # DeploymentEngine seam, Kathara + fake engines, terminal bridge
  db/                       # models + Alembic migrations
  catalog/node_types.json   # node types + images (single source of truth)
  openapi.json              # generated API spec (frontend types come from it)
  tests/                    # pytest (fake engine)
frontend/src/
  app/                      # routes (login, library, editor), providers, theme
  canvas/                   # TopologyCanvas, projection.ts (pure), layout/, nodes/, edges/
  shell/                    # top bar, sidebar (palette/explorer), inspector, status bar, ⌘K
  features/                 # topology dialogs, deployment actions, terminal dock, purdue, auth
  store/                    # zustand slices + undo (zundo) + normalize.ts
  ui/                       # design-system primitives (Tailwind + Radix)
  styles/                   # tokens.css (light/dark), index.css, reactflow.css
  catalog/  api/  types/    # catalog lookups, REST/WS client, frontend-owned types
```

## Prerequisites

- [Docker](https://www.docker.com/) (Desktop on macOS/Windows, or Engine on Linux)

That is all for running the stack. Node and Python are only needed for local
development outside Docker.

## Run

```bash
./start.sh          # builds and starts frontend (:3000) and backend (:8000)
```

Open http://localhost:3000. There is no sign-in screen: the API is open by
default. Tear down with `docker compose down`.

To require a token instead, set it for both services and rebuild — the frontend
bakes it in at build time:

```bash
AE3GIS_INSTRUCTOR_TOKEN=your-token docker compose up --build
```

## Develop

```bash
# Frontend
cd frontend && npm install && npm run dev      # :5173
npm run build     # typecheck + production build
npm run test      # vitest (store, canvas projection, layout, IP/CIDR utils)
npm run lint      # eslint

# Backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest && ruff check .                # domain, jobs, reconcile, API tests
python -m uvicorn main:create_app --factory --reload --port 8000
AE3GIS_ENGINE=fake python -m uvicorn main:create_app --factory --port 8000   # no Docker needed
```

## Deferred features

Removed from the wired app in this foundation pass, to be re-added on the engine
abstraction later: firewall rule editor, attack scenarios and scripts, classroom
mode (sessions/student slots), Wireshark packet capture, container web-UI proxy,
and the AI assistant. Scenario data still round-trips in saved topologies.

## Deployment images

The catalog ships multi-arch defaults (`kathara/frr` for routers, `kathara/base` for
hosts/switches) that run natively on arm64. Swap in your own images by
editing `backend/catalog/node_types.json`, or per-container from the editor.
