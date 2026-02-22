# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AE3GIS v2 is an interactive multi-scale network topology visualizer built with React 19, TypeScript, and ReactFlow (@xyflow/react). It provides drill-down views across three hierarchical scales: Geographic (sites) → Subnet (network segments) → LAN (containers/devices).

## Commands

```bash
npm run dev       # Start Vite dev server (http://localhost:5173)
npm run build     # Type-check (tsc) + production build
npm run lint      # ESLint on all .ts/.tsx files
npm run preview   # Serve production build locally
```

There are no tests configured in this project.

## Architecture

### State Management

Global topology state uses an **Immer-based reducer** (`src/store/topologyReducer.ts`) exposed via React Context (`src/store/TopologyContext.ts`). The reducer handles all CRUD actions for sites, subnets, containers, and connections at every level. State shape:

```
TopologyData
├── sites[] (each with position, location)
│   ├── subnets[] (each with CIDR)
│   │   ├── containers[] (devices with type, IP, status)
│   │   └── connections[] (container-to-container)
│   └── subnetConnections[] (inter-subnet within site)
└── siteConnections[] (between sites)
```

### Navigation & View Hierarchy

`App.tsx` manages a `NavigationState` with `scale` ('geographic' | 'subnet' | 'lan'), `siteId`, and `subnetId`. It conditionally renders one of three view components, each wrapping a `<ReactFlow>` canvas:

- **GeographicView** → `SiteNode` custom nodes
- **SubnetView** → `SubnetCloudNode` custom nodes
- **LanView** → `DeviceNode` custom nodes

Double-clicking a node drills down to the next level. Breadcrumb provides back navigation.

### View Component Pattern

All three views (`GeographicView`, `SubnetView`, `LanView`) follow the same structure:

1. ReactFlow `useNodesState`/`useEdgesState` for canvas state
2. `useEffect` hooks to sync nodes/edges with topology data
3. Context menu handlers for right-click CRUD
4. Toolbar with layout mode selection
5. Dialog components for add/edit/delete operations

### Layout System

`src/utils/autoLayout.ts` provides three graph layout algorithms: **Dagre** (hierarchical, default), **Circle** (hub-and-spoke), and **Grid**. Each view's Toolbar triggers layout recalculation.

### Custom ReactFlow Elements

- **Nodes** (`src/components/nodes/`): `SiteNode`, `SubnetCloudNode`, `DeviceNode` — each with distinct visual styling and drill-down behavior
- **Edges** (`src/components/edges/NeonEdge.tsx`): `NeonEdge` (curved) and `NeonEdgeStraight` with color props for connection type differentiation

### Dialog Pattern

Dialogs in `src/components/dialogs/` use an Inner/Outer pattern: an inner component manages form state, wrapped by an outer component handling open/close. Bulk variants exist for containers and connections.

### Data Types

All types are defined in `src/data/sampleTopology.ts`. Key types: `Site`, `Subnet`, `Container` (with `ContainerType`: web-server, file-server, plc, firewall, switch, router, workstation), `Connection`, `TopologyData`.

### Utilities

- `src/utils/validation.ts` — IP/CIDR validation, subnet capacity calculation, next available IP generation
- `src/utils/idGenerator.ts` — Wraps `crypto.randomUUID()`

## Styling

Cyberpunk/neon theme using CSS variables in `src/index.css`. Fonts: Orbitron (display), Share Tech Mono (mono), Rajdhani (UI). Color coding: green (primary), cyan (secondary), magenta (routers), amber (switches/PLCs), red (firewalls), blue (workstations). No UI framework — all custom CSS.
