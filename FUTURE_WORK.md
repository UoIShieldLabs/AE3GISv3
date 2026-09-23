# Future work

The v3 foundation ships the core (editor + Kathara deploy/destroy/status +
terminal). Re-home these deferred features onto the `DeploymentEngine`
abstraction, roughly in order of independence:

1. **Classroom mode** — sessions + student slots + join-code auth. Mostly
   engine-independent; quickest to restore. Reintroduces student read-only UI.
2. **Attack scenarios & scripts** — per-phase script execution and the
   instructor→student pushed-terminal flow, as an engine method.
3. **Firewall editor** — per-node rules via the engine's exec path (nftables).
4. **Wireshark capture** — a sidecar sharing a machine's network namespace,
   resolved through the engine.
5. **Container web-UI proxy** — reverse-proxy to a node's service port.
6. **AI assistant** — decoupled from the orchestrator; catalog-aware.

Backend services designed for but not built yet (seams exist in
`engine/base.py`, `services/`, and the `events` table):
- **Node exec / script runner** — Kathara's native `exec`; run a catalogued
  script (`backend/scripts/catalog.json`) on a node, capture output, record an
  event. Building block for scenario phases.
- **Packet capture** — `tcpdump -w` in a node (or a sidecar in its netns),
  download the pcap for Wireshark; live streaming later.
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
- CI: run backend pytest + frontend build/test/lint before deploy.
