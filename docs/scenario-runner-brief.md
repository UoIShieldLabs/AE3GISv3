# Implementation brief: the scenario runner (classroom step-through)

**Status:** implemented. Backend: `engine.exec_stream` (base/kathara/fake),
`services/scenario.py` (kind `scenario`, subject `scenario:<topology>`,
stoppable), `api/scenario.py` (run step/phase → 202 + job, runs list, samples,
export, live WS). Frontend: store CRUD for phases/steps (undo-tracked) and a
`features/scenario` dock panel (author + Run step / Run phase + live output).
See `docs/ARCHITECTURE.md` §5.7a. The notes below are the original design brief,
kept for rationale; two decisions landed differently (confirmed with the user):
execution **streams** output rather than one-shot capture, and the existing
type names (`AttackPhase`/`ScriptExecution`) and JSON keys were **kept** (no
rename), so old data round-trips unchanged.

## What it is and why

AE3GIS is a teaching platform for networking and security courses. Labs run
**fully isolated** inside Kathará (Docker, unprivileged, no bridge to any real or
external network). Instructors use it to demonstrate how networks behave and how
the Purdue/IT-OT boundary works, including walking a class through a documented
historical incident at the level of technique.

Today an instructor drives a multi-step walkthrough by hand: open a terminal on a
node (the `exec` WebSocket), type a command, switch nodes, repeat. That works but
isn't repeatable or easy to follow from the back of a lecture hall. **The
scenario runner turns a saved, ordered list of steps into something you click
through, with each step's command and output shown inline**, so the whole
workflow is visible and reproducible for a class. It is a general lab-automation
aid — equally useful for "bring up the services, then show routing converge" as
for "step through an incident" — not tied to any one lesson.

Every step is an **ordinary administrative or client command** run inside a lab
container (start a daemon, set a route, send a protocol request with a standard
client, read a log). There is no exploit code and no real malware; the teaching
point of the ICS lessons is precisely that legacy OT protocols need no exploit.
Keep the existing containment: a step that models destruction writes only to a
container's own scratch space, never a host mount or shared directory.

## What already exists (build on these)

- **Frontend types** (`frontend/src/types/topology.ts`), stored in
  `topology.data.scenarios`, round-tripped, and counted in
  `backend/api/presets.py` — but never executed:
  `Scenario { id, name, description?, phases }`,
  `AttackPhase { id, name, description?, executions }`,
  `ScriptExecution { containerId, script, args? }`.
  Consider renaming `AttackPhase` → `Phase` and `ScriptExecution` → `Step` for a
  neutral, general vocabulary; keep the index signature so old data round-trips.
- **The exec bridge**: `backend/engine/terminal.py::bridge_terminal`, exposed at
  `POST/WS /api/v1/topologies/ws/{id}/exec/{container}`; it resolves the
  container by Docker labels (not Kathará's user prefix). This is the mechanism
  for running commands on a node.
- **Jobs** (`services/jobs.py`, one per subject), **per-job live WebSocket
  fan-out** (`api/live_ws.py`), and **joblogs** — reuse for a phase that runs
  several steps and streams output.
- **Dock tabs** (`frontend/src/store/slices/dockSlice.ts`: terminal | capture |
  traffic | monitor) and the lazy-mounted dock bodies — add a `scenario` tab the
  same way.
- **Fake engine** (`engine/fake.py`, `AE3GIS_ENGINE=fake`) — must simulate the
  new run method so tests and Docker-less UI work keep passing.

## Suggested shape

**Backend**
- Add an engine method to run a command non-interactively and capture it, e.g.
  `exec_capture(node, argv, timeout) -> {exit_code, stdout, stderr}` on
  `DeploymentEngine` (base + `engine/kathara` via the Docker SDK `exec_run` after
  `resolve_container`, + `engine/fake`). This is the one new engine capability;
  everything else composes existing pieces.
- `services/scenario.py`: run a single step, and run a whole phase as a
  **job** (subject `scenario:<topology_id>`, `stoppable`) that executes its steps
  in order and streams `{step, command, output, exit}` events over the live WS.
- API under `/api/v1`, one error envelope: run one step
  (`POST /topologies/{id}/scenario/steps/run`, body = a step or a reference into
  the stored scenario) and run a phase (`POST …/scenario/phases/{phaseId}/run`,
  202 + job). The scenario definition is read from the stored
  `topology.data.scenarios` (frontend-owned; **no backend topology schema** — do
  not add a Pydantic mirror). Only the run request/response envelope is new:
  regenerate `openapi.json` and the frontend API types.

**Frontend**
- Scenario authoring lives in the store with the rest of the topology mutations
  (scenarios are part of `topology.data`): add/edit/remove phases and steps, a
  node picker (reuse `ui/MultiSelect` / the device list), command + args fields.
  Track it in undo like the other topology edits.
- A **Scenario** dock tab (`features/scenario/`): phases → steps, a **Run step**
  and **Run phase** button per row, each step showing its command and streamed
  output; deploy-gated (needs a running lab). Mirror the capture/traffic panels
  for live output over the WS.

## Principles to hold
- Engine-agnostic (fake engine simulates); `topology.data.scenarios` stays
  frontend-owned and round-trips; steps are plain commands via the exec path;
  output is always visible; multi-step phases are jobs; keep it a **general**
  teaching primitive, not special-cased to one lesson.

## Verify
- Backend: `cd backend && python -m pytest && ruff check . && ruff format --check .`
  — fake-engine step/phase run, output capture, stop mid-phase.
- Frontend: `cd frontend && npm run build && npm run test && npm run lint`
  — store CRUD for phases/steps, the dock panel.
- End to end on the fake engine, then a real Kathará lab: deploy a small
  topology, run a phase, confirm each step's output shows and a destructive step
  touches only the container's scratch space.
