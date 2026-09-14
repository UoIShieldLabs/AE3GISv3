# AE3GIS Codebase Structure

**Audience:** engineers working on AE3GIS v3.

See the root `README.md` for the tree and `CLAUDE.md` for architecture rules.
This doc focuses on the one non-obvious flow: how a topology becomes a running
network.

## Deployment pipeline

```
TopologyData (JSON in DB)
        │  domain/validation.validate()         ← errors block deploy
        │  domain/plan.build_lab_plan()         ← pure, unit-tested
        ▼
LabPlan { nodes[], collision domains }
   node = { id, role, image, interfaces[], startup[] }
        │  engine/kathara/lab_builder.build_lab()
        ▼
Kathara Lab  (machines + links + startup script per machine)
        │  KatharaEngine.deploy()  → Kathara.get_instance().deploy_lab(lab)
        ▼
Docker containers on bridge networks (one bridge per collision domain)
```

### domain/plan.py (the domain logic)
Pure functions, no Kathara import, fully unit-tested (`tests/test_plan.py`). The same
`LabPlan` feeds the exporters in `domain/export/` (lab-spec JSON, Kathara `lab.conf`,
ContainerLab `topo.clab.yml`), so what you export is exactly what deploy runs:

1. **Metadata + gateway detection.** Each container membership records its
   subnet/ip/prefix/gateway. If a subnet has no valid gateway, the first
   router/firewall in it is used.
2. **Endpoint resolution.** Connections that reference a subnet or site id are
   resolved to that side's gateway router, so dragging a subnet-to-subnet link
   in the UI wires the right routers automatically.
3. **Interface assignment.** Explicit `eth{N}` names are pre-registered; the
   rest are auto-assigned. Each point-to-point link gets its own collision
   domain (`cd0`, `cd1`, …).
4. **IPs + routes.** Intra-subnet links use the container's real IP; router↔router
   links with no subnet context get a `/30` pair from `10.255.0.0/24`. Static
   routes to every remote subnet are propagated across router links by BFS
   (so multi-hop router chains route end-to-end).
5. **Startup commands per role.** router = `ip_forward` + per-iface IPs +
   static routes; switch = linux bridge `br0` enslaving its interfaces; host =
   IP on the home interface + default route via the gateway. All plain
   iproute2/sysctl, so they are engine- and arch-agnostic.

### Kathara specifics (`engine/kathara/`)
- `naming.py` — `lab_name(topology_id)` (id only, so renaming a topology never
  breaks lookups) and `lab_hash(name)` computed the way Kathara does it.
  Status/exec/destroy use the `EngineState` saved at deploy time and find
  containers by Docker label (`lab_hash`, `name`), independent of Kathara's
  per-user prefix — which is derived from the backend's hostname (pinned in
  compose) and used to change on every container recreation.
- `lab_builder.py` — one `get_or_new_link` per collision domain,
  `connect_machine_to_link(node, cd, iface_index)`, image from the catalog, and
  the node's startup commands written to `/ae3gis-init.sh` (run via the machine
  `exec` meta, since `add_meta('exec', …)` overwrites).
- `engine.py` — deploys/undeploys through the Kathara singleton, observes via
  the Docker SDK; all blocking calls run in a worker thread. `list_labs` and
  `purge(lab_hash)` back the reconcile service; `images_present`/`pull_image`
  back the deploy job's image step.

### Jobs, runtime and reconcile
Deploy and destroy are rows in `jobs` executed by `services/jobs.JobRunner`
(steps: validate → images → plan → deploy → verify). `GET /runtime` returns
status + active job + node states in one call; the UI polls it fast while a
job runs and slowly while deployed. On startup, jobs left running are failed
and `services/reconcile.apply` resets topologies whose lab is gone; orphan labs
are listed under `GET /system/labs` and purged explicitly.

### Adding a deployment engine
Implement `engine/base.DeploymentEngine` and return it from
`engine/fake.make_engine` for a new `AE3GIS_ENGINE` value. Nothing else changes.

## Frontend ↔ backend contract

The frontend is deliberately **decoupled** from the backend's data schema:

- The backend stores and serves topology `data` as **opaque JSON**. `schemas.py`
  types only the API envelope (`TopologyCreate/Update/Record/Summary`, each with
  `data: dict`); it does not model the topology internals and never strips unknown
  fields. Round-trip is proven by `tests/test_topologies_api.py::test_unknown_fields_round_trip`.
- The frontend owns its own view of the data in `src/types/topology.ts` (with an
  index signature so unknown backend fields pass through the editor). Neither side
  needs to change when the other adds a field.
- The only shared contracts are the API envelope and the **node catalog**
  (`GET /api/catalog`). Per-type display metadata — color, label, icon
  (`src/catalog/icons.tsx`), layout rank (`rankFor`), Purdue level — is served by
  the catalog, so adding a node type is ideally a single `node_types.json` edit.
  The deployment engine reads whatever fields it needs from the stored JSON
  defensively, so malformed topologies fail at deploy time (with a clear error)
  rather than being rejected at save time.

## Frontend architecture

```
URL (/t/:id/site/:siteId/subnet/:subnetId)  →  Scope
                                                  │
store.topology + store.expanded + status + selection
                                                  │  canvas/projection.ts  project()   ← pure, unit-tested
                                                  ▼
                         React Flow nodes/edges (site | subnet | device | group)
```

- **Scope** is the drill-down focus and comes only from the URL (`lib/topology.ts`).
  `resolveScope` falls back up the chain when a deep link is stale;
  `defaultScopeFor` auto-opens single-site / single-subnet topologies deeper.
- **Expanded** ids (view slice) are drawn as group nodes with their children
  inside. That is how the same data shows one, two, or three levels: nothing is
  nested in the data model, nesting is a rendering concern. When a group is
  expanded the canvas nudges overlapping siblings; "Apply layout" is aware of
  group sizes.
- **Positions** are stored on the entities (`position`); container positions are
  relative to their subnet so LAN scope and the in-place group share numbers.
  `GroupNodeData.origin` converts rendered (parent-relative) coordinates back to
  stored ones (`toStoredPosition`). Drag-stop writes through `moveNodes`.
- **Mutations** are id-based store actions; `addConnection` decides the kind of
  link from its endpoints (device↔device in a subnet, router↔router across
  subnets/sites, subnet↔subnet, site↔site) and fills `fromContainer/toContainer`
  the engine expects. `deleteItems` cascades and is one undo step.
- **Runtime status** (`document.containerStatus`) is separate from the saved
  topology; the projection merges it into node data for the status dots.
- **Adding a feature panel:** put UI under `features/<name>/`, state in a new
  slice (`store/slices/`), register a sidebar tab / dock tab / inspector section
  in `shell/`, and expose commands in `shell/CommandPalette.tsx`.
