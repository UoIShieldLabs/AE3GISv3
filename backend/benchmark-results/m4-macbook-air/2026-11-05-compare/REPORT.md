# AE3GIS vs GNS3 on the M4 MacBook Air

Run on 2026-11-05 and 2026-11-06. Values are **AE3GIS / GNS3**, the mean over the
runs that completed.

## Key results

- **Memory:** a lab adds 1.07× (25 hosts) to 1.68× (400 hosts) less host memory on
  AE3GIS. 800 hosts fit on AE3GIS but not on GNS3.
- **Speed:** a lab is usable 2.3–4.1× sooner on AE3GIS, and its VM starts in
  6.8 s vs 42.8 s.
- **CPU at rest:** the same on both, 0.24 vs 0.26 host cores with 400 hosts deployed.
- **Network:** GNS3 has 3.5–4.9× lower latency and 20–36× more single-flow throughput.
  It carries at least 5–10× more load per flow, and it uses 4.4–5.1× less CPU for the
  same traffic.

## Setup

**Host:** MacBook Air, Apple M4 (10 cores), 32 GiB, macOS 26.7.2. Only one platform's
VM runs at a time.

| | AE3GIS | GNS3 |
|---|---|---|
| **Platform** | AE3GIS 3.1.0 with Kathara | GNS3 2.2.54, Docker nodes |
| **VM** | Docker Desktop (Apple's Virtualization framework) | GNS3 VM in VMware Fusion |
| **Inside the VM** | Docker 29.9.2, Linux 7.0.14, cgroup v2 | Ubuntu 20.04, Docker 28.1.1, Linux 5.15, cgroup v1 |
| **VM resources** | 8 CPUs, 16 GiB | 8 CPUs, 16 GiB |
| **Links** | Kathara's VDE plugin (a userspace switch per link) | ubridge (one process per node) |
| **Driven through** | AE3GIS's REST API: import, deploy, destroy | GNS3's REST API: 16 parallel calls for nodes, links, start and stop |

**The lab** is a campus network, generated once and used unchanged on both platforms.
- **Server LAN:** a core router, one switch and the servers.
- **Client LANs:** up to 200 hosts each, behind their own router, with a distribution
  switch and access switches of up to 48 hosts.

| hosts | servers | routers | switches | nodes |
|---|---|---|---|---|
| 25 | 1 | 2 | 2 | 30 |
| 50 | 1 | 2 | 4 | 57 |
| 100 | 2 | 2 | 5 | 109 |
| 200 | 4 | 2 | 7 | 213 |
| 400 | 8 | 3 | 13 | 424 |
| 800 | 16 | 5 | 25 | 846 |

The images are pinned by digest:

| Role | Image |
|---|---|
| hosts | `tollan/benign-client:v0.10` |
| servers (1 per 50 hosts) | `tollan/nginx-server:v0.3` |
| routers | `tollan/iptables:v0.6` |
| switches | `kathara/base` |

## E0: platform at rest

**What it measures:** what each platform costs with no lab running.

**How:**
1. Restart the platform's VM and time how long until its API and Docker respond.
2. Leave it idle for 5 min.
3. Average the last 3 min.

This runs 3 times.

| | AE3GIS | GNS3 |
|---|---|---|
| Host memory (VM + the platform's host processes) | 2.09 GiB | 2.25 GiB |
| Host CPU | 0.045 cores | 0.033 cores |
| Memory used inside the VM | 0.78 GiB | 0.57 GiB |
| VM start | 6.8 s | 42.8 s |

## E1: lab lifecycle and scale

**What it measures:**
- how long a lab takes to deploy, become usable and tear down;
- how much memory and CPU it adds, from 25 to 800 hosts.

**How:** every size runs in 3 rounds, with sizes ascending in each round. Each step:
1. Restart the VM.
2. Wait for it to go quiet (CPU under 10%).
3. Record a 30 s reference.
4. Deploy the lab.
5. Wait until the network is ready: every host and server pings its gateway and an
   address across the core.
6. Settle for 30 s.
7. Hold the lab idle for 60 s; this is where memory is measured.
8. Tear the lab down.

800 hosts run only if the projection from that round's 400-host step stays under 85%
of the VM's memory.

**Measures:**
- **usable:** deploy time plus the time until the network is ready;
- **host memory added:** the host memory of the VM and the platform's host processes
  during the hold, minus the step's reference;
- **VM memory per node:** memory used inside the VM during the hold, minus the
  reference, divided by the number of nodes;
- **host CPU while deploying:** mean host cores used during the deploy.

### Time

| hosts | usable lab, s | GNS3 ÷ AE3GIS | teardown, s |
|---|---|---|---|
| 25 | 4.8 / 17.0 | 3.6× | 2.4 / 7.0 |
| 50 | 7.2 / 21.5 | 3.0× | 4.9 / 8.4 |
| 100 | 13.2 / 53.6 | 4.1× | 7.8 / 10.2 |
| 200 | 30.7 / 70.3 | 2.3× | 23.4 / 18.0 |
| 400 | 90.6 / 209.6 | 2.3× | 73.8 / 74.1 |
| 800 | 275.2 / – | – | 300.9 / – |

### Resources

| hosts | host memory added, GiB | GNS3 ÷ AE3GIS | VM memory per node, MiB | host CPU while deploying, cores |
|---|---|---|---|---|
| 25 | 0.71 / 0.76 | 1.07× | 17.7 / 19.7 | 5.5 / 1.2 |
| 50 | 1.12 / 1.34 | 1.20× | 15.9 / 19.6 | 5.9 / 1.4 |
| 100 | 1.90 / 2.49 | 1.31× | 15.4 / 19.2 | 6.4 / 0.9 |
| 200 | 3.41 / 4.89 | 1.43× | 14.7 / 19.4 | 6.4 / 1.5 |
| 400 | 6.39 / 10.76 | 1.68× | 14.1 / 20.4 | 6.4 / 1.3 |
| 800 | 12.40 / – | – | 13.6 / – | 6.5 / – |

**800 hosts:**
- **AE3GIS** ran it in all 3 rounds, using 77% of the VM's memory.
- **GNS3 did not fit:** its projection from 400 hosts was about 17.5 GiB, more than
  all of the VM's memory (15.6 GiB usable inside the VM).

## E2: network performance

**What it measures:** latency, throughput, the most traffic each platform carries,
and the CPU that traffic costs.

**How:** one 100-host lab is deployed once after a VM restart, and three tests run on
it:

- **Ping:** 20 pings, 0.2 s apart, on each of two sets of 10 pairs:
  - **same LAN:** two hosts in the same LAN;
  - **cross-core:** a host and a server, through the client LAN's router and the core
    router.
- **Flat-out TCP:** one iperf3 TCP flow with no rate limit, 10 s, 3 trials. It runs
  once on the same LAN and once across the core.
- **Load ladder:** every flow sends at a constant rate, which steps up 100K → 250K →
  500K → 1M → 2M → 5M bit/s.
  - **Patterns:**
    - **clients → servers (cs):** 100 flows, one per host, to the servers across the
      core;
    - **mesh:** 200 flows, each host to its next two neighbours on the same LAN.
  - Each pattern runs in TCP and in UDP.
  - **Each rate:** a 60 s window once every client has started.
  - **Pass:** at least 95% delivered and at most 1% loss.
  - **Stop:** at the first rate that fails. The last pass and the first failure are
    repeated.

### Latency

| pairs | p50, ms | p95, ms |
|---|---|---|
| same LAN | 1.52 / 0.44 | 3.48 / 0.89 |
| cross-core | 6.55 / 1.35 | 9.15 / 1.74 |

### Flat-out TCP

| path | Gb/s |
|---|---|
| same LAN | 0.13 / 4.65 |
| cross-core | 0.08 / 1.59 |

### Load ladder

| pattern | flows | highest rate passed, per flow | total traffic at that rate | AE3GIS's first failure |
|---|---|---|---|---|
| cs / TCP | 100 | 500K / 5M | 50 / 500 Mb/s | 1M: 73% delivered |
| cs / UDP | 100 | 1M / 5M | 100 / 500 Mb/s | 2M: 45% delivered, 55% loss |
| mesh / TCP | 200 | 1M / 5M | 200 / 1000 Mb/s | 2M: 54% delivered |
| mesh / UDP | 200 | 1M / 5M | 200 / 1000 Mb/s | 2M: 86% delivered, 10% loss |

GNS3 passed every rate up to 5M, the top of the ladder.

### CPU for the same traffic

Host cores per 100 Mb/s delivered, at the highest rate both passed:

| pattern | rate per flow | host cores per 100 Mb/s | GNS3 uses |
|---|---|---|---|
| cs / TCP | 500K | 8.77 / 1.81 | 4.9× less |
| cs / UDP | 1M | 6.07 / 1.38 | 4.4× less |
| mesh / TCP | 1M | 3.05 / 0.60 | 5.1× less |
| mesh / UDP | 1M | 2.52 / 0.57 | 4.4× less |

## E3: a large lab at rest

**What it measures:** the idle CPU of a 400-host lab once the deploy's aftermath is
over. After a large deploy, Docker Desktop's UI re-lists every container after each
container event, which keeps `dockerd` and `containerd` busy for minutes. E1's hold
starts 30 s after the network is ready, so it still includes that work.

**How:** one E1 step at 400 hosts per platform, after E2.
1. After the settle, wait until the VM's CPU has stayed under 10% for 30 s (at most
   20 min).
2. Hold for 2 min.

| | AE3GIS | GNS3 |
|---|---|---|
| Time from the deploy until the VM is quiet | 337 s | 79 s (already quiet at the first check) |
| Host CPU 30 s after ready (E1's hold) | 4.20 cores | 0.41 cores |
| Host CPU at rest (E3's hold) | 0.24 cores | 0.26 cores |
| VM CPU at rest | 0.13 cores | 0.19 cores |

## Data

This folder holds the rest of the data:
- `summary.md`: every table;
- `summary.json`: the numbers;
- `ae3gis/` and `gns3/`: one JSON file per step;
- `manifest.json`: the run's plan and commit.

The log is `../2026-11-05-compare.log`, and the charts are in
`analysis/platforms.ipynb`.
