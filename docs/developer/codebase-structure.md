# AE3GIS Codebase Structure

**Audience:** engineers working on AE3GIS v3.

See the root `README.md` for the tree and `CLAUDE.md` for architecture rules.
This doc focuses on the one non-obvious flow: how a topology becomes a running
network.

## Deployment pipeline

```
TopologyData (JSON in DB)
        │  engine/networking.build_lab_plan()   ← pure, unit-tested
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

### networking.py (the domain logic)
Pure functions, no Kathara import, fully unit-tested (`tests/test_networking.py`):

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
- `naming.py` — deterministic `lab_name(topology_id, data)` and
  `machine_name(node_id)` so status/exec/destroy work statelessly by rebuilding
  the plan.
- `lab_builder.py` — one `get_or_new_link` per collision domain,
  `connect_machine_to_link(node, cd, iface_index)`, image from the catalog, and
  the node's startup commands written to `/ae3gis-init.sh` (run via the machine
  `exec` meta, since `add_meta('exec', …)` overwrites).
- `engine.py` — wraps the Kathara singleton; all blocking calls run in a worker
  thread. `resolve_container` returns the real Docker container name (via
  `get_machine_api_object`) for the terminal bridge.

### Adding a deployment engine
Implement `engine/base.DeploymentEngine` and swap the singleton in
`routers/deployment.py`. Nothing else changes.

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
