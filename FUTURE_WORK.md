# Future work

The v3 foundation ships the core (editor + Kathara deploy/destroy/status +
terminal), plus packet capture (live pcap, Wireshark streaming) and iperf3
traffic runs with telemetry and recorded environments (see ARCHITECTURE §5.7). Re-home these deferred features onto the `DeploymentEngine`
abstraction, roughly in order of independence:

1. **Classroom mode** — sessions + student slots + join-code auth. Mostly
   engine-independent; quickest to restore. Reintroduces student read-only UI.
2. **Attack scenarios & scripts** — per-phase script execution and the
   instructor→student pushed-terminal flow, as an engine method.
3. **Firewall editor** — per-node rules via the engine's exec path (nftables).
4. **Container web-UI proxy** — reverse-proxy to a node's service port.
5. **AI assistant** — decoupled from the orchestrator; catalog-aware.

Backend services designed for but not built yet (seams exist in
`engine/base.py`, `services/`, and the `events` table):
- **Node exec / script runner** — exec by Docker label (as the sidecars do;
  Kathara's own `exec` filters by its user prefix); run a catalogued script
  (`backend/scripts/catalog.json`) on a node, capture output, record an event.
  Building block for scenario phases.
- **Live telemetry stream** — SSE/WebSocket over the events table plus
  container stats, replacing `/runtime` polling.
- **Agent orchestration** — `GET /topologies/{id}/context` already bundles
  record, diagnostics, plan, runtime and events; expose the versioned API as
  agent tools and rely on `version`/409 for safe concurrent edits.

Cross-cutting:
- Prebuilt node images: CI in `ae3gis-containers` builds multi-arch images and
  pushes them to GHCR tagged by fingerprint; image resolution becomes "local
  image with a matching fingerprint → pull the prebuilt one → build locally"
  (the fingerprint labels AE3GIS already stamps make this a drop-in).
- Make the catalog env-overridable so image sets ship without editing the repo.

Traffic and performance (after the first baseline, `docs/baselines/`):
- **More generators** behind `services/traffic_generators.py`: Locust (HTTP user
  behaviour; the Cardinal locustfiles are a starting point), Modbus/TCP polling
  (HMI → PLC), pcap replay, the benign-client scripts as background traffic.
- **Scenarios**: phased background + attack traffic with a ground-truth
  timeline (e.g. the windfarm exercise).
- **Comparisons**: sweeps over image variants, per-node `cpus`/`mem` limits
  (Kathara machine meta) and hosts; a compare view over runs; a runs index
  table (or DuckDB over the ndjson samples) once cross-run queries are needed.
- **The "after" optimisations**: Kathara's kernel-bridge plugin
  (`kathara/katharanp`) instead of userspace VDE switches, CPU pinning,
  MTU/offload tuning. Record each with a new baseline.
- Live per-link utilisation on the canvas; capture extras (ring files, `-i any`,
  a packet detail pane, feeding pcaps to Zeek/Suricata).
- **Before hosting v3**: a production compose (no source mount, no `--reload`,
  token required, real CORS origin) and auth in front of the host (the token
  is baked into the frontend bundle).
