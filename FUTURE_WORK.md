# Future work

The v3 foundation ships the core (editor + Kathara deploy/destroy/status +
terminal), plus packet capture (live pcap, Wireshark streaming), resource
monitors, iperf3 traffic runs (flows and patterns) and scale benchmarks, all
with recorded environments (see ARCHITECTURE §5.7–5.8, docs/benchmarks/).
Re-home these deferred features onto the `DeploymentEngine` abstraction,
roughly in order of independence:

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

Traffic:
- **More generators** behind `services/traffic_generators.py`: Locust (HTTP user
  behaviour; the Cardinal locustfiles are a starting point), Modbus/TCP polling
  (HMI → PLC), pcap replay, the benign-client scripts as background traffic.
- **Scenarios**: phased background + attack traffic with a ground-truth
  timeline (e.g. the windfarm exercise).

## Performance: improve, then benchmark each step

The benchmark tooling exists to measure every improvement against a baseline.
The baseline is AE3GIS as merged in `f32a1967` on each platform's default
setup; every improvement changes one thing and is re-measured with the same
specs (`backend/benchmarks/specs/`), the same host label and the same VM size,
then compared on: ceiling (hosts), marginal memory per node, deploy and
destroy seconds per node, time to network ready, CPU per Mb/s of traffic,
delivered/asked, Docker's own CPU.

### Benchmarking tasks
- **Complete the baseline** on macOS (Docker Desktop), Linux (Docker Engine)
  and Windows (Docker Desktop, WSL2): the idle, clients → servers and mesh
  sweeps with `repetitions: 3`.
- **Compare benchmarks**: a report (and a view) over exported benchmark
  bundles, per metric and scale; fingerprints say what differs.
- **Time until the host is quiet after a deploy or destroy**, as a metric:
  engines keep working after their jobs end (on Docker Desktop its UI
  re-lists every container after each container event, minutes of work at a
  few hundred nodes).
- **Sweep variables beyond node count**: traffic rate per host at a fixed
  node count; path length (hops per flow); nodes per subnet.

### Improvements to try
Engine and host:
- **Docker engine without Docker Desktop**: Colima (macOS), Docker Engine
  (Linux), dockerd inside WSL2 (Windows).
- **Image store**: the classic store vs the containerd image store (Docker 29's
  default on fresh installs), where every container listing looks up each
  container's image.
- **Container runtime**: crun instead of runc (smaller per-container footprint,
  faster start).
- **Log driver** `none` or `local` for lab nodes (dockerd keeps log copiers per
  container).
- **VM sizing and virtualization settings** (CPUs, memory, Apple
  Virtualization.framework) where a VM hosts the engine.

Network model (traffic is bound by userspace VDE switching, which costs CPU
per packet at every link a flow crosses):
- **Kathará's kernel-bridge plugin** (`kathara/katharanp`) instead of VDE.
- **Shared LAN per subnet**: one collision domain per subnet instead of a link
  per host, so fewer switches, networks and hops.
- **MTU and offload tuning.**

Nodes (a node's own processes are ~1 MB of the ~11 MB it costs the host; the
rest is per-container runtime overhead):
- **Fewer containers**: switches as plain collision domains (no container),
  simple hosts as bare network namespaces where a full container isn't needed.
- **Lightweight node images** (Alpine/BusyBox): expect disk and start-up gains
  more than memory.
- **Memory deduplication** (KSM): likely small, since node processes are small
  and image pages are already shared through overlay layers; worth one
  measurement.
- **Per-node CPU/memory limits** for predictable capacity.

Orchestration and tooling:
- **Deploy/destroy speed**: Kathará lists containers once per node while
  creating them (costly with the containerd image store); tune its pool size,
  batch network creation.
- **Cheaper runtime status**: share one container listing between status
  pollers, or push status over the live stream (see Live telemetry above).
- **A lighter traffic generator**: one process with many sockets instead of
  two iperf3 processes per flow.
- **Kernel limits** for thousands of nodes (neighbour tables, pids, inotify,
  file handles).
- **Scale-out**: Kathará's Kubernetes backend (Megalos) past one host's ceiling.

Other:
- Live per-link utilisation on the canvas; capture extras (ring files, `-i any`,
  a packet detail pane, feeding pcaps to Zeek/Suricata).
- **Before hosting v3**: a production compose (no source mount, no `--reload`,
  token required, real CORS origin) and auth in front of the host (the token
  is baked into the frontend bundle).
