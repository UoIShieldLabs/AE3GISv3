# AE3GIS vs GNS3 on the M4 Max Mac Studio

Run on 2026-11-06, 12:17 to 18:40. Values are **AE3GIS / GNS3**, the mean over the
runs that completed. Every step completed (46 of 46).

## Key results

- **Memory:** a lab adds 1.12× (50 hosts) to 1.81× (800 hosts) less host memory on
  AE3GIS. At 25 hosts AE3GIS adds 10% more. Both platforms ran 800 hosts.
- **Speed:** a lab is usable 1.9–4.0× sooner on AE3GIS, and its VM starts in
  9.3 s vs 72.0 s.
- **CPU at rest:** higher on AE3GIS, 0.83 vs 0.26 host cores with 400 hosts deployed.
  Docker Desktop never went quiet within E3's 20 min limit, so this still includes the
  deploy's aftermath (see E3).
- **Network:** GNS3 has 3.9–15× lower latency and 18–45× more single-flow throughput.
  It carries up to 5× more load per flow (the same in mesh UDP), and it uses 2.7–6.9×
  less CPU for the same traffic.

## Setup

**Host:** Mac Studio, Apple M4 Max (16 cores), 128 GiB, macOS 15 (Darwin 24.6.0).
Only one platform's VM runs at a time.

| | AE3GIS | GNS3 |
|---|---|---|
| **Platform** | AE3GIS 3.1.0 with Kathara | GNS3 2.2.54, Docker nodes |
| **VM** | Docker Desktop (Apple's Virtualization framework) | GNS3 VM in VMware Fusion 13.6.4 |
| **Inside the VM** | Docker 29.8.2, Linux 7.0.14, cgroup v2 | Ubuntu 20.04, Docker 28.1.1, Linux 5.15, cgroup v1 |
| **VM resources** | 12 CPUs, 60 GiB | 12 CPUs, 60 GiB |
| **Links** | Kathara's VDE plugin (a userspace switch per link) | ubridge (one process per node) |
| **Driven through** | AE3GIS's REST API: import, deploy, destroy | GNS3's REST API: 16 parallel calls for nodes, links, start and stop |

**VM memory:** this host's other benchmarks gave Docker Desktop 95 GiB, but the GNS3
VM would not boot in Fusion with that much: it stopped with a hypervisor error
(`ulm.c:378`). Both VMs got 60 GiB instead, hence the results folder's name.

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
| Host memory (VM + the platform's host processes) | 3.81 GiB | 3.35 GiB |
| Host CPU | 0.058 cores | 0.032 cores |
| Memory used inside the VM | 1.13 GiB | 1.02 GiB |
| VM start | 9.3 s | 72.0 s |

## E1: lab lifecycle and scale

**What it measures:**
- how long a lab takes to deploy, become usable and tear down;
- how much memory and CPU it adds, from 25 to 800 hosts.

**How:** every size runs in 3 rounds, with sizes ascending in each round. GNS3 went
first in rounds 1 and 3, AE3GIS in round 2. Each step:
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
| 25 | 3.3 / 6.2 | 1.9× | 2.1 / 7.1 |
| 50 | 4.4 / 11.5 | 2.6× | 3.1 / 8.4 |
| 100 | 8.6 / 34.3 | 4.0× | 5.1 / 9.9 |
| 200 | 17.8 / 55.5 | 3.1× | 11.8 / 23.1 |
| 400 | 43.8 / 161.0 | 3.7× | 38.5 / 23.0 |
| 800 | 142.1 / 482.4 | 3.4× | 249.3 / 50.7 |

**800 hosts:**
- **AE3GIS's teardown mean is skewed by one round:** 469 s in round 1, then 139 s in
  rounds 2 and 3. Its deploys were steady (137–141 s).
- **GNS3's deploy is mostly link creation:** about 310 s of its 480 s went to the 845
  links, 45 s to the 846 nodes and 113 s to starting them.

### Resources

| hosts | host memory added, GiB | GNS3 ÷ AE3GIS | VM memory per node, MiB | host CPU while deploying, cores |
|---|---|---|---|---|
| 25 | 0.84 / 0.76 | 0.90× | 22.9 / 19.6 | 6.0 / 1.7 |
| 50 | 1.20 / 1.34 | 1.12× | 19.5 / 19.8 | 7.3 / 1.9 |
| 100 | 1.84 / 2.52 | 1.37× | 17.3 / 19.5 | 8.0 / 1.5 |
| 200 | 3.46 / 4.91 | 1.42× | 16.9 / 19.7 | 9.1 / 1.8 |
| 400 | 6.59 / 10.68 | 1.62× | 15.6 / 20.6 | 9.3 / 1.3 |
| 800 | 13.06 / 23.64 | 1.81× | 15.2 / 22.7 | 9.1 / 1.3 |

**800 hosts** fit on both, in all 3 rounds, using about 23% (AE3GIS) and 34% (GNS3)
of the VM's memory.

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
| same LAN | 4.12 / 0.27 | 6.43 / 1.12 |
| cross-core | 6.97 / 1.42 | 9.66 / 2.50 |

### Flat-out TCP

| path | Gb/s |
|---|---|
| same LAN | 0.12 / 5.53 |
| cross-core | 0.12 / 2.23 |

### Load ladder

| pattern | flows | highest rate passed, per flow | total traffic at that rate | first failure: AE3GIS / GNS3 |
|---|---|---|---|---|
| cs / TCP | 100 | 1M / 5M | 100 / 500 Mb/s | 2M: 63% delivered / none |
| cs / UDP | 100 | 1M / 2M | 100 / 200 Mb/s | 2M: 6% loss / 5M: 25% loss |
| mesh / TCP | 200 | 2M / 5M | 400 / 1000 Mb/s | 5M: 65% delivered / none |
| mesh / UDP | 200 | 2M / 2M | 400 / 400 Mb/s | 5M: 5% loss / 5M: 3% loss |

GNS3 passed every TCP rate up to 5M, the top of the ladder. Unlike on the MacBook Air,
both platforms failed UDP at 5M here.

### CPU for the same traffic

Host cores per 100 Mb/s delivered, at the highest rate both passed:

| pattern | rate per flow | host cores per 100 Mb/s | GNS3 uses |
|---|---|---|---|
| cs / TCP | 1M | 7.55 / 1.11 | 6.8× less |
| cs / UDP | 1M | 6.51 / 1.69 | 3.8× less |
| mesh / TCP | 2M | 2.22 / 0.32 | 6.9× less |
| mesh / UDP | 2M | 2.13 / 0.79 | 2.7× less |

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
| Time from the deploy until the VM is quiet | 1244 s (hit the 20 min limit) | 82 s |
| Host CPU 30 s after ready (E1's hold) | 5.28 cores | 0.35 cores |
| Host CPU at rest (E3's hold) | 0.83 cores | 0.26 cores |
| VM CPU at rest | 0.43 cores | 0.18 cores |
| `dockerd`, `containerd` and co. at rest | 0.34 cores | 0.09 cores |

**AE3GIS never went quiet:** its VM's CPU stayed above 10% for the whole 20 min, so
its hold started at the limit. Its "at rest" figures still include Docker Desktop's
aftermath: most of the VM's CPU is `dockerd`, `containerd` and co., while the lab's own
containers use 0.003 cores. On the MacBook Air, the same step went quiet after 337 s,
and both platforms were equal at rest. `summary.md` prints this row as
"1244 / 82 (capped)"; the capped side is AE3GIS.

## Data

This folder holds the rest of the data:
- `summary.md`: every table;
- `summary.json`: the numbers;
- `ae3gis/` and `gns3/`: one JSON file per step;
- `manifest.json`: the run's plan and commit.

The log is `../2026-11-06-compare.log`, and the charts are in
`analysis/platforms.ipynb`.

The run used commit `c7defa6` with one local change (the probe image's build context
written as a plain tar), which came in later as part of `f49a32b`. It changes nothing
that is measured.
