# AE3GIS Developer Setup

**Audience:** Contributors setting up a local development environment.

---

## 1. Prerequisites

| Tool | Minimum version | Notes |
|------|-----------------|-------|
| Node.js | 18+ | `node --version` |
| npm | 9+ | Bundled with Node |
| Python | 3.10+ | `python3 --version` |
| Docker | 24+ | Required for full-stack testing |
| ContainerLab | 0.54+ | Required for actual topology deploys |
| sudo/ContainerLab access | — | See [deployment guide](../admin/deployment-guide.md#5-sudoers-configuration) |

For just UI/API development without actual topology deploys, Docker and ContainerLab are not strictly required — the backend will error only when deploy/destroy is called.

---

## 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server starts on **port 5173** with hot module replacement. API requests are proxied to `localhost:8000` via `vite.config.ts` — the backend must be running separately.

```bash
# Type-check
npm run build

# Lint
npm run lint
```

---

## 3. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set the minimum required env var:

```bash
export AE3GIS_INSTRUCTOR_TOKEN=dev-token
```

Start the server:

```bash
python -m uvicorn main:app --reload --port 8000
```

The SQLite database is auto-created at `ae3gis.db` in the current directory on first run. No migration step needed.

FastAPI's interactive docs are available at `http://localhost:8000/docs`.

**Optional env vars for local dev:**

```bash
export AE3GIS_DB_PATH=./ae3gis.db          # default
export AE3GIS_CLAB_WORKDIR=./clab-workdir  # created automatically
export AE3GIS_HOST_SCRIPTS_DIR=$(pwd)/scripts  # for script bind-mounts
```

---

## 4. Running Both via Startup Script

```bash
./start.sh
```

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | http://localhost:3000 | Nginx-served production build; no hot-reload |
| Backend | http://localhost:8000 | Source is volume-mounted → `--reload` is active |

Changes to frontend code require a rebuild (`docker compose up --build`). Backend code changes are picked up automatically via `--reload`.

---

## 5. Development Workflow

### Adding a new container type

Add container image to the Docker Hub with appropriate formatting for the description.

The following is how a Docker Hub image repository should be formatted:

- Repository name: Container type (optional base os image is running) 
- Description format: Category type software color label versions #
 
- Category: Options at the moment are server, management, or other. these will change in the future
- Type: What the container is acting as. e.g. dhcp, web, directory, etc\
- Software: The software the container is running to make it act like it's type
- Color: In hex prepended with a hashtag
- Label: An all caps shortened version of the type shown in the UI when the container is part of the topology
- Versions: Add as many as desired separated by spaces. These need to correspond to the tags that are in the repository. This is how it is possible to have multiple versions of the same software in the tags and be able to choose between them in AE3GIS.
- #: This tells the script that it does not need to read any more data from the description. After this hashtag you can put anything in the rest of the description
 
Separate each value in the description with a space. examples of the descriptions are below.
 
Ex: server dhcp isc-dhcp #240177 DHCP 4.4.3 latest #
 
Ex: other workstation ubuntu #4466ff WS latest #
 
Ex: management switch open-vswitch #ffaa00 SW latest #
 

### Adding a new API endpoint

1. **Router file** (`backend/routers/*.py`) — Define the route function with FastAPI decorator
2. **Schema** (`backend/schemas.py`) — Add Pydantic request/response models if needed
3. **Auth dependency** — Add `Depends(require_instructor)` or `Depends(require_any_auth)` as appropriate
4. **`frontend/src/api/client.ts`** — Add a typed wrapper function

### Adding a preset

Drop a JSON file into `backend/presets/`. The file must conform to the preset schema:

```json
{
  "name": "My Preset",
  "description": "Optional description",
  "topology": { ...TopologyData... }
}
```

Scenarios are optional. The `GET /api/presets` endpoint discovers the file automatically.

---

## 6. Code Conventions

**State mutations:** All topology state mutations go through the Immer reducer in `store/topologyReducer.ts`. Never mutate `topology` directly in components.

**API calls:** All fetch calls go through typed wrapper functions in `api/client.ts`. No direct `fetch()` calls in components.

**Dirty flag:** Only `UPDATE_CONTAINER_STATUSES` is exempt from setting `dirty = true`. All other topology-modifying actions must set it. This is enforced by the reducer structure — if you add a new action, assume it sets `dirty` unless it's purely runtime state.

**ID generation:** Use `generateId()` (from `utils/`) for all new entity IDs. Do not use `Math.random()` or `Date.now()` directly.

**Container status initialization:** After loading a topology, always dispatch `CLEAR_CONTAINER_STATUSES` before starting the poll. This sets all containers to `status: 'stopped'` so red dots render immediately instead of being invisible.

**Naming sync:** If you change deployment name or container name logic, update both `frontend/src/utils/deploymentName.ts` and `backend/services/clab_manager.py` together.

---

## 7. Manual Testing Checklist

Run through these steps after non-trivial changes:

- [ ] Create a new topology, add a site, add a subnet, add a container
- [ ] Save topology — dirty indicator clears
- [ ] Reload topology — all data reappears correctly, no blank screen
- [ ] Export topology as JSON, re-import
- [ ] Deploy topology — status pill transitions to `deployed`, containers turn green
- [ ] Open a terminal on a running container — terminal connects and accepts input
- [ ] Destroy topology — containers turn red
- [ ] Create a classroom session with a template topology
- [ ] Instantiate slots — join codes appear
- [ ] Log in as a student using a join code — read-only UI, correct topology shown
- [ ] Execute a scenario phase (single topology)
- [ ] Batch deploy classroom slots
