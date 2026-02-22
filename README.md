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

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

The frontend proxies `/api/*` and WebSocket paths to the backend at `http://localhost:8000`.

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
├── App.tsx                     # Root component, view routing & state
├── api/client.ts               # REST/WebSocket client
├── data/sampleTopology.ts      # Type definitions & sample data
├── store/                      # Immer-based state management
├── components/
│   ├── GeographicView.tsx      # Top-level site map
│   ├── SubnetView.tsx          # Subnet graph for a site
│   ├── LanView.tsx             # Device-level LAN graph
│   ├── TerminalOverlay.tsx     # Multi-tab resizable terminal panel
│   ├── NodeInfoPanel.tsx       # Detail panel for selected nodes
│   ├── ControlBar.tsx          # Save/deploy/destroy controls
│   ├── TopologyBrowser.tsx     # Load/manage saved topologies
│   ├── LoginScreen.tsx         # Authentication gate
│   ├── ClassroomPanel.tsx      # Instructor classroom management
│   ├── Breadcrumb.tsx          # Navigation breadcrumb
│   ├── Toolbar.tsx             # Per-view toolbar
│   ├── dialogs/                # CRUD modal dialogs
│   ├── nodes/                  # Custom ReactFlow node types
│   ├── edges/                  # Custom ReactFlow edge types
│   └── ui/                     # Reusable UI primitives
└── utils/                      # Layout, validation, ID generation

backend/
├── main.py                     # FastAPI entry point
├── auth.py                     # JWT authentication
├── models.py                   # SQLAlchemy ORM models
├── schemas.py                  # Pydantic request/response schemas
├── database.py                 # SQLite database setup
├── routers/
│   ├── topologies.py           # Topology CRUD endpoints
│   ├── containerlab.py         # Deploy/destroy/status/exec/WebSocket
│   └── classroom.py            # Classroom mode endpoints
└── services/
    ├── clab_generator.py       # Topology JSON → ContainerLab YAML
    └── clab_manager.py         # ContainerLab lifecycle management
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
