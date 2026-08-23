# AE3GIS v2

Interactive network topology visualization and deployment platform. Design multi-site network topologies through a three-level drill-down view (Geographic → Subnet → LAN) and deploy them as Docker-based simulations via ContainerLab.

## Features

- **Three-level topology editor** — Sites → Subnets → LAN devices, each with an interactive graph canvas
- **ContainerLab deployment** — Generate YAML and deploy/destroy topologies as Docker containers
- **Multi-tab terminal** — Open interactive shells into running containers with a resizable, tabbed terminal panel
- **Live container status** — WebSocket-driven status indicators on every device node
- **Firewall rule management** — View and edit iptables rules on firewall containers
- **Classroom mode** — Instructor/student roles with read-only student views and topology assignment
- **Auto-layout** — Dagre, circle, and grid layout modes with drag-to-reposition

## Prerequisites

- [Node.js](https://nodejs.org/) v18+
- [Python](https://www.python.org/) 3.10+
- [Docker](https://www.docker.com/)
- [ContainerLab](https://containerlab.dev/) (for deployment)

## Getting Started

Assumes all prerequisites are already installed on this machine.

### 1. Clone this repository



```bash
git clone https://github.com/Blake-Mayers/working.git
cd working
```
### 2. One-time sudoers setup

The backend needs to run `containerlab deploy`/`destroy` without a password
prompt. Run the setup script once per machine:

```bash
chmod +x scripts/setup-sudoers.sh
sudo ./scripts/setup-sudoers.sh
```

It writes `/etc/sudoers.d/ae3gis-containerlab` for your current user and
verifies it at the end — you should see the containerlab version print with
no password prompt. Safe to re-run any time (e.g. if `containerlab`'s install
path ever changes).

### 3: Verify Configuration

To verify the sudoers configuration works, test these commands without entering a password:

```bash
# This should list containerlab help without asking for password
sudo containerlab version

# This should succeed without asking for password (creates an empty file then deletes it)
touch /tmp/test_sudoers.txt && sudo rm /tmp/test_sudoers.txt
```
### 4: Deploying the stack

After installing all of the prerequisites, make the startup script executable by running the following in the root level of the directory. You will only need to do this once.
```bash
chmod +x start.sh
```

Then, to start AE3GIS, in the root level of the directory, run 
```bash
./start.sh
```
To tear down AE3GIS, first destroy all active topologies through the UI (if you don't, you will have hanging containers from the deployed topologies), then run the following in the root level of the directory
```bash
docker compose down
```
If you run `docker compose down` before you destroy the topologies you have deployed through AE3GIS, run the following to get rid of all hanging containers left over
```bash
docker rm -f $(docker ps -a --filter "name=clab-ae3gis-*" -q)
```

### Notes:

`test` is the default `AE3GIS_INSTRUCTOR_TOKEN`


## Available Scripts

### Frontend

| Command           | Description                               |
| ----------------- | ----------------------------------------- |
| `npm run dev`     | Start Vite dev server with HMR            |
| `npm run build`   | Type-check and produce a production build |
| `npm run preview` | Serve the production build locally        |
| `npm run lint`    | Run ESLint                                |

## Project Structure

```
frontend/src/
├── App.tsx                          # Root component, view routing & state
├── main.tsx                         # Bootstraps React and mounts App into the root element
├── api/client.ts                    # REST/WebSocket client
├── data/sampleTopology.ts           # Type definitions & sample data
├── store/                           # Immer-based state management
├── components/
│   ├── GeographicView.tsx           # Top-level site map
│   ├── SubnetView.tsx               # Subnet graph for a site
│   ├── LanView.tsx                  # Device-level LAN graph
│   ├── TerminalOverlay.tsx          # Multi-tab resizable terminal panel
│   ├── NodeInfoPanel.tsx            # Detail panel for selected nodes
│   ├── ControlBar.tsx               # Save/deploy/destroy controls
│   ├── TopologyBrowser.tsx          # Load/manage saved topologies
│   ├── LoginScreen.tsx              # Authentication gate
│   ├── ClassroomPanel.tsx           # Instructor classroom management
│   ├── Breadcrumb.tsx               # Navigation breadcrumb
│   ├── Toolbar.tsx                  # Per-view toolbar
│   ├── ContainerAspects.tsx         # Container types and GUI aspects
│   ├── dynamicFrontendGenerator.py  # Dynamically populates ContainerAspects.tsx
│   ├── PurdueView.tsx               # View of topology from Purdue Model
│   ├── WiresharkOverlay.tsx         # Container connected Wireshark panel
│   ├── dialogs/                     # CRUD modal dialogs
│   ├── nodes/                       # Custom ReactFlow node types
│   ├── edges/                       # Custom ReactFlow edge types
│   └── ui/                          # Reusable UI primitives
└── utils/                           # Layout, validation, ID generation

backend/
├── main.py                          # FastAPI entry point
├── auth.py                          # JWT authentication
├── models.py                        # SQLAlchemy ORM models
├── schemas.py                       # Pydantic request/response schemas
├── database.py                      # SQLite database setup
├── config.py                        # Loads env configuration for DB, workdir, auth, and LLM
├── routers/
│   ├── topologies.py                # Topology CRUD endpoints
│   ├── containerlab.py              # Deploy/destroy/status/exec/WebSocket
│   └── classroom.py                 # Classroom mode endpoints
└── services/
    ├── clab_generator.py            # Topology JSON → ContainerLab YAML
    ├── clab_manager.py              # ContainerLab lifecycle management
    ├── ansible_manager.py           # Ansible configuration provisioning
    ├── capture_manager.py           # Wireshark sidecar containers
    └── clab_importer.py             # Parses clab YAML into site/subnet topology model
```

## Tech Stack

**Frontend:**
- React 19 + TypeScript + Vite 7
- @xyflow/react (ReactFlow) for interactive graph rendering
- dagre for automatic graph layout
- Immer / use-immer for immutable state management

**Backend:**
- FastAPI + Uvicorn
- SQLAlchemy + SQLite
- ContainerLab + Docker
- Ansible
