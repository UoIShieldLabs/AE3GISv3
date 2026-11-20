# AE3GIS v3

Interactive network-topology editor and deployment platform. Design multi-site
topologies through a three-level drill-down (Network → Site → Subnet) and
deploy them as live containers via **Kathara**.

> **New here?** Read the [Architecture Guide](docs/ARCHITECTURE.md) — a
> quickstart, the system's three core contracts, and how a drawing becomes
> running containers.

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
  each link as a network of its plugin (`kathara/katharanp_vde` by default: a
  userspace VDE switch per link). No `sudo`, no host network namespace, no
  privileged container.
- **Capture & traffic** — capture packets on any deployed link or interface
  (live packet list in the browser, pcap download, or stream straight into
  Wireshark with `curl -N …/pcap?follow=true | wireshark -k -i -`), and run
  iperf3 traffic between nodes with live throughput and per-node CPU, memory
  and interface charts. Both run as sidecar containers in a node's network
  namespace, so they work with any node image. Every run records its
  environment for before/after comparisons (`backend/scripts/run_baseline.py`,
  `docs/baselines/`).
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
  app/                      # routes (login, library, editor), providers, theme registry
  canvas/                   # TopologyCanvas, projection.ts (pure), layout/, nodes/, edges/
  shell/                    # top bar, sidebar (palette/explorer), inspector, status bar, ⌘K
  features/                 # topology dialogs, deployment actions, terminal dock, purdue, auth, class
  store/                    # zustand slices + undo (zundo) + normalize.ts
  ui/                       # design-system primitives (Tailwind + Radix)
  styles/                   # themes/ (one token file per theme), index.css, reactflow.css
  catalog/  api/  types/    # catalog lookups + icon styles, REST/WS client, frontend-owned types
```

## Prerequisites

- [Docker](https://www.docker.com/) (Desktop on macOS/Windows, or Engine on Linux)

That is all for running the stack. Node and Python are only needed for local
development outside Docker.

## Run

```bash
./start.sh          # builds and starts frontend (:3000) and backend (:8000)
```

Open http://localhost:3000. By default there is no sign-in: the API is open
and everyone is an admin, which suits a lab on your own machine. Tear down with
`docker compose down`.

### Accounts (classes, several instructors)

To run classes from your machine, set the first admin's password:

```bash
AE3GIS_ADMIN_PASSWORD='choose-one' ./start.sh
```

- You sign in as `admin` (`AE3GIS_ADMIN_USERNAME` to change it) with full
  access. In the library's **Staff** section, add the other **admins** (full
  access too) and **instructors**: each gets a temporary password, shown once,
  and chooses their own at their first sign-in.
- Every admin and instructor has their own **class**: in the library's
  **Students** section, turn sign-up on and share its join code; students open
  `http://<your-ip>:3000/login` → **Join class**, and the code puts them in
  that class. Instructors see their own topologies and their students';
  admins see every class and topology.
- **Publish** a topology from the library: its tutorials and scenarios go with
  it. Your students see it under *Lessons*; opening it gives each student their
  own copy to deploy and edit (and to reset when you update it). Unpublishing
  or deleting it removes those copies (running labs are destroyed);
  republishing starts students afresh. Students keep what they *Duplicate to
  My topologies*.
- Students also create, import and export their own topologies. They run
  tutorials and scenarios but don't author them, and can't manage images, the
  host's labs or a class. Instructors build images; registries, the host's
  labs, benchmarks and the staff are the admins'.
- Removing an instructor hands their topologies (running labs keep running)
  and their students to another admin or instructor; nothing is destroyed.
- Every lab runs on **your** Docker. `AE3GIS_STUDENT_MAX_LABS` (default 1)
  caps how many each student can run at once; Students and Running list and
  destroy them.
- `AE3GIS_ADMIN_TOKEN` is an optional static admin bearer for scripts
  (`./bench.sh --token`). The older `AE3GIS_INSTRUCTOR_PASSWORD`,
  `_USERNAME` and `_TOKEN` still work when the `AE3GIS_ADMIN_*` ones are
  unset; upgrading such an instance makes its instructor the admin, with the
  same username, students and join code.

Plain HTTP on a LAN carries passwords in the clear: fine for a classroom
network, not for the internet.

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
