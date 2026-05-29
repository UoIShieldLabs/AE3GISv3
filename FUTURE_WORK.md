# Future Work: Docker SDK Migration, IEC 61850, and Power Systems Co-Simulation

Reference document capturing design discussion for three potential future directions for the AE3GIS platform. Each section is self-contained — read the one you're working on.

---

## 1. Migration from ContainerLab to Docker SDK + pyroute2

### Motivation

- **Mac compatibility:** ContainerLab requires direct access to Linux kernel networking primitives (veth pairs, netns). On macOS this only works through a Linux VM with awkward setup. Docker Desktop already provides a transparent Linux VM, so calling the Docker API directly works seamlessly on Mac.
- **Reduced external dependency:** Removes the `containerlab` binary and `sudo` requirement from the deployment path.
- **More control:** Owning the deploy logic enables custom parallelism, finer error handling, and easier future extensions (e.g. power-sim sidecars).

### What replaces ContainerLab

| ContainerLab responsibility | Replacement |
|---|---|
| Container lifecycle (`docker run/stop`) | Docker SDK for Python (`docker` package) |
| veth pair creation, bridge attachment | `pyroute2` (Python netlink bindings) |
| Network namespace management | `pyroute2.NetNS` |
| Static route / IP assignment inside containers | `docker exec` via Docker SDK |
| Management network creation | Docker SDK `networks.create()` |

### Files that would change

- `backend/services/clab_manager.py` → `backend/services/deployment_manager.py`
  - Replace `sudo containerlab deploy/destroy` calls with Docker SDK + pyroute2
  - Keep public surface (`deploy()`, `destroy()`, `deployment_name()`) identical so the router layer is untouched
- `backend/services/clab_generator.py` → `backend/services/topology_planner.py`
  - Stops emitting YAML; instead emits a Python data structure consumed directly by `deployment_manager.py`
  - All the existing logic (gateway detection, interface assignment, /30 PtP links, static routes) is reusable as-is

### Performance

Effectively identical to ContainerLab at classroom scale. Same kernel primitives underneath. Slight win on deploy time because we can parallelize container starts in asyncio rather than waiting on the clab binary's sequential flow.

### Effort

Roughly 2–3 weeks. Self-contained change — the API layer, frontend, and database schema are all untouched.

### Risks

- pyroute2 requires `CAP_NET_ADMIN` — already have it via `privileged: true`
- Need to carefully handle cleanup on partial-failure deploys (ContainerLab handles this for us today)
- Mac users still run Docker Desktop, so very large topologies (1000+ containers) may be limited by Docker Desktop's VM memory allocation

---

## 2. IEC 61850 / SCD Support

### Goal

Allow instructors to upload a Substation Configuration Description (SCD) file and have the platform automatically generate a deployable topology with IEC 61850–compatible containers.

### Two parts

#### A. SCD parser (easy)

SCD files are XML with a published schema. A new `backend/services/scd_importer.py` mirrors the existing `clab_importer.py`.

Mapping from SCD concepts to AE3GIS data model:

| SCD element | AE3GIS concept |
|---|---|
| `<Substation>` | Site |
| `<VoltageLevel>` or `<Bay>` | Subnet |
| `<IED>` | Container (new type: `ied`) |
| `<Communication>` → `<ConnectedAP>` | IP assignments |
| `<SubNetwork>` | Connection topology |

Effort: 1–2 days for a working parser.

#### B. IEC 61850 containers (harder)

Need container images that implement the IEC 61850 protocol stack.

**Recommended library:** [libiec61850](https://github.com/mz-automation/libiec61850) (MZ Automation, MIT/GPL dual license, actively maintained).

**Container images to build:**

- `ae3gis/ied-server` — generic IED with MMS server + GOOSE publisher. Configuration loaded from a mounted SCD at runtime via libiec61850's dynamic model API.
- `ae3gis/scada-client` — MMS client for HMI/SCADA workstations. Could extend the existing ScadaBR container or be a separate purpose-built one.

**Protocol coverage:**

| Protocol | Difficulty | Notes |
|---|---|---|
| MMS (client/server, TCP/102) | Easy | Works over any Docker bridge network |
| GOOSE (Layer 2 multicast) | Hard | Requires bridge multicast forwarding, bypasses IP routing |
| Sampled Values | Hard | Same Layer 2 multicast issue as GOOSE |

**GOOSE/SV challenge:** ContainerLab's veth + Linux bridge stack does not forward Layer 2 multicast between containers by default. Options:
1. Enable IGMP snooping on bridges (partial fix)
2. Use `macvlan` or `ipvlan` networks instead of bridges for IED interfaces
3. Restrict the initial scope to MMS-only — sufficient for most classroom scenarios

**Recommendation:** Start MMS-only. Add GOOSE/SV in a second phase once the basic flow is working.

Effort: 1–2 weeks for the importer + MMS-capable IED container. Another 1–2 weeks for GOOSE/SV.

---

## 3. Power Systems Co-Simulation (HELICS + OpenDSS)

### Goal

Run a real power systems model alongside the cyber network so that IEC 61850 control commands have real physical effects, and IEDs receive real measurements. Cyber attacks have measurable, visible physical consequences.

### Architecture

Per-student federation — each deployed topology gets its own HELICS federation. Aligns with the existing classroom isolation model (deep-copy per student).

#### Containers added per topology

| Container | Purpose | RAM |
|---|---|---|
| `helics-broker` | Message router, time synchronization between federates | ~50MB |
| `opendss-federate` | Runs the power model (`.dss` file generated from SCD), publishes measurements, receives control actions | ~400MB |
| `ied-federate` (one per IED) | Existing IED container, extended with HELICS Python bindings — physics on one side, IEC 61850 on the other | ~150MB |

Existing routers/workstations/switches are unchanged.

#### Compute estimate

- Per topology overhead: ~1.2GB RAM, ~0.3 CPU cores
- 30-student classroom: ~36GB RAM, ~9 cores additional load
- Comfortable on a server with 64GB / 16 cores

#### Time stepping

HELICS handles time synchronization. 1-second time steps are sufficient for training scenarios — OpenDSS solves a typical substation model in milliseconds, so real-time simulation is easily achievable.

### SCD → OpenDSS `.dss` conversion

Need a second converter alongside `scd_importer.py` that produces an OpenDSS script.

**Element mapping:**

| SCD concept | OpenDSS element |
|---|---|
| Voltage level | bus + `voltagebases` |
| Power transformer | `Transformer` |
| Lines / conductors | `Line` |
| Breaker / switch | `Line ... switch=yes` |
| Load / motor | `Load` |
| Generator | `Generator` |
| Capacitor bank | `Capacitor` |
| Measurement point | `Monitor` |

**What the SCD does NOT contain:**

The SCD describes the substation configuration and communications, not the electrical parameters. Missing values include:
- Line impedance (resistance, reactance per unit length)
- Transformer reactance
- Load power demand
- Generator capacity
- Fault current ratings

**Three ways to fill in the gaps:**

1. **Sensible defaults by equipment type** — e.g. a 138kV transmission line gets a standard impedance per mile. Easiest, good enough for training where students care about behavior more than fidelity.
2. **Companion parameters file** — accept a JSON/YAML alongside the SCD that fills in the missing electrical values.
3. **Preset library** — match SCD patterns to a library of pre-built substation models.

Recommend starting with option 1.

### Wiring IEDs to the simulation

Each IED container becomes dual-faced:

```
   Cyber side (IEC 61850)          Physics side (HELICS)
   ┌─────────────────┐             ┌──────────────────┐
   │ libiec61850     │             │ helics-py        │
   │ - MMS server    │  ◄──IED──►  │ - subscribe bus  │
   │ - GOOSE pub     │             │   measurements   │
   │ - protection    │             │ - publish trips  │
   │   logic         │             │                  │
   └─────────────────┘             └──────────────────┘
            ▲                                ▲
            │                                │
       ┌────┴─────┐                  ┌───────┴────────┐
       │ Cyber    │                  │ HELICS broker  │
       │ network  │                  │ ────────────►  │
       └──────────┘                  │ OpenDSS        │
                                     └────────────────┘
```

Protection logic runs inside the IED container, reads measurements published by OpenDSS via HELICS, and sends GOOSE/MMS trip messages over the cyber network. When OpenDSS receives a trip command (from a breaker IED), it updates its model and the resulting voltage/current change propagates back to all subscribed IEDs.

### What this enables for training

- Real voltage, current, frequency values visible in the HMI
- Stuxnet-style attack scenarios with genuinely physical consequences
- Protection coordination exercises (does the right breaker trip first?)
- Visible cascading failures from cyber attacks

### Effort

Significant. Roughly:
- HELICS broker container: 1 day
- OpenDSS federate container with HELICS bindings: 1 week
- SCD → DSS converter: 1–2 weeks
- IED container extension (dual-faced libiec61850 + HELICS): 2–3 weeks
- Integration and testing: 1–2 weeks

Total: 6–10 weeks of focused work for a working prototype.

---

## Suggested ordering

1. **Docker SDK migration** first — unlocks Mac compatibility and gives clean foundation for the next two
2. **SCD parser + basic IED container (MMS only)** — gets IEC 61850 topologies deploying
3. **HELICS + OpenDSS co-simulation** — the research-grade payoff that distinguishes this platform from other ICS training tools

Each step builds on the previous one without forcing redesign of earlier components.

---

## Key references

- libiec61850: https://github.com/mz-automation/libiec61850
- HELICS: https://helics.readthedocs.io
- OpenDSS: https://www.epri.com/pages/sa/opendss
- py-dss-interface: https://github.com/PauloRadatz/py_dss_interface
- pyroute2: https://github.com/svinota/pyroute2
- Docker SDK for Python: https://docker-py.readthedocs.io
