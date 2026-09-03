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

- **Frontend** — React + TypeScript + Vite, React Flow canvas, Immer reducer.
- **Backend** — FastAPI. A `DeploymentEngine` abstraction isolates the
  orchestrator; the only implementation today is `KatharaEngine`.
- **Deployment** — Kathara talks to the Docker daemon via its SDK and models
  each link as a Docker bridge network. No `sudo`, no host network namespace,
  no privileged container.
- **Node catalog** — `backend/catalog/node_types.json` is the single source of
  truth for node types, their default images, colours, labels, and icons.
  Images are **data**, served to the frontend at `GET /api/catalog`. Change the
  image set by editing that file — no code changes.

```
backend/
  catalog/node_types.json   # node types + images (single source of truth)
  engine/
    base.py                 # DeploymentEngine interface
    networking.py           # topology -> engine-agnostic lab plan (pure, tested)
    terminal.py             # PTY <-> WebSocket bridge
    kathara/                # Kathara implementation of the engine
  routers/                  # topologies (CRUD), deployment, catalog, presets
  tests/                    # pytest
frontend/src/
  types/topology.ts         # shared domain types
  catalog/                  # fetches + exposes the node catalog
  api/client.ts             # all REST + WebSocket calls
  hooks/                    # deployment, status polling, terminal sessions
  components/               # editor views, dialogs, nodes
```

## Prerequisites

- [Docker](https://www.docker.com/) (Desktop on macOS/Windows, or Engine on Linux)

That is all for running the stack. Node and Python are only needed for local
development outside Docker.

## Run

```bash
./start.sh          # builds and starts frontend (:3000) and backend (:8000)
```

Open http://localhost:3000. The default instructor token is `test` (override
with `AE3GIS_INSTRUCTOR_TOKEN`). Tear down with `docker compose down`.

## Develop

```bash
# Frontend
cd frontend && npm install && npm run dev      # :5173
npm run build     # typecheck + production build
npm run test      # vitest (reducer + IP/CIDR utils)

# Backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest                                # networking + catalog + API tests
python -m uvicorn main:app --reload --port 8000
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
