# AE3GIS vs GNS3 on the Surface Laptop 7

Run on 2026-11-06 and 2026-11-07. Values are **AE3GIS / GNS3**, the mean over the
runs that completed.

## Key results

- **Memory:** a lab adds 1.40× (25 hosts) to 2.25× (400 hosts) less host memory on
  AE3GIS. 800 hosts fit on AE3GIS but not on GNS3.
- **Speed:** a lab is usable 3.3–5.0× sooner on AE3GIS, and its VM starts in
  11.7 s vs 70.0 s.
- **CPU at rest:** lower on AE3GIS, 0.18 vs 0.89 host cores with 400 hosts deployed.
- **Network:**
  - **AE3GIS** has 1.2–5.4× lower latency. On the load ladder it passes the same or a
    higher rate on every pattern, up to 5× higher per flow.
  - **GNS3** has 1.6–23× more single-flow throughput, and it uses 1.3–3.0× less host
    CPU for the same traffic.

## Setup

**Host:** Microsoft Surface Laptop 7, Intel Core Ultra 7 268V (8 cores), 32 GB,
Windows 11. Only one platform's VM runs at a time.

| | AE3GIS | GNS3 |
|---|---|---|
| **Platform** | AE3GIS 3.1.0 with Kathara | GNS3 2.2.56.1, Docker nodes |
| **VM** | Docker Desktop on WSL 2 | GNS3 VM in VirtualBox 7.1.12 (on Hyper-V) |
| **Inside the VM** | Docker 29.9.2, Linux 6.6.87 (WSL 2), cgroup v2 | Ubuntu 20.04, Docker 28.1.1, Linux 5.15, cgroup v1 |
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
| Host memory (VM + the platform's host processes) | 2.92 GiB | 2.25 GiB |
| Host CPU | 0.028 cores | 0.187 cores |
| Memory used inside the VM | 0.78 GiB | 0.72 GiB |
| VM start | 11.7 s | 70.0 s |

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
- **host memory added:** the most host memory the VM and the platform's host
  processes used during the step, minus the step's reference. WSL 2 hands freed memory
  back to Windows and VirtualBox doesn't, so the peak is the figure that compares like
  for like;
- **VM memory per node:** memory used inside the VM during the hold, minus the
  reference, divided by the number of nodes;
- **host CPU while deploying:** mean host cores used during the deploy.

### Time

| hosts | usable lab, s | GNS3 ÷ AE3GIS | teardown, s |
|---|---|---|---|
| 25 | 9.9 / 32.4 | 3.3× | 6.2 / 15.7 |
| 50 | 16.4 / 61.2 | 3.7× | 11.3 / 31.3 |
| 100 | 29.7 / 127.8 | 4.3× | 21.4 / 58.7 |
| 200 | 62.9 / 297.1 | 4.7× | 44.0 / 116.7 |
| 400 | 152.1 / 762.5 | 5.0× | 108.6 / 239.4 |
| 800 | 443.0 / – | – | 430.9 / – |

### Resources

| hosts | host memory added, GiB | GNS3 ÷ AE3GIS | VM memory per node, MiB | host CPU while deploying, cores |
|---|---|---|---|---|
| 25 | 0.49 / 0.69 | 1.40× | 9.7 / 19.4 | 3.1 / 2.7 |
| 50 | 0.75 / 1.24 | 1.65× | 9.1 / 19.6 | 3.4 / 2.7 |
| 100 | 1.26 / 2.32 | 1.85× | 8.8 / 19.3 | 3.9 / 2.5 |
| 200 | 2.25 / 4.63 | 2.06× | 8.7 / 19.6 | 4.2 / 2.3 |
| 400 | 4.25 / 9.58 | 2.25× | 8.6 / 19.8 | 5.1 / 2.2 |
| 800 | 8.45 / – | – | 8.7 / – | 5.8 / – |

**800 hosts:**
- **AE3GIS** ran it in all 3 rounds, using 51% of the VM's memory.
- **GNS3 did not fit:** its projection from 400 hosts was 17.1 GiB, more than all of
  the VM's memory (15.6 GiB usable inside the VM).

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
| same LAN | 1.22 / 1.47 | 3.14 / 15.06 |
| cross-core | 2.54 / 13.60 | 4.97 / 34.08 |

### Flat-out TCP

| path | Gb/s |
|---|---|
| same LAN | 0.02 / 0.48 |
| cross-core | 0.05 / 0.08 |

### Load ladder

| pattern | flows | highest rate passed, per flow | total traffic at that rate | first failure: AE3GIS / GNS3 |
|---|---|---|---|---|
| cs / TCP | 100 | 500K / 100K | 50 / 10 Mb/s | 1M: 49% delivered / 250K: 91% delivered |
| cs / UDP | 100 | 500K / 100K | 50 / 10 Mb/s | 1M: 32% loss / 250K: 27% loss |
| mesh / TCP | 200 | 500K / 500K | 100 / 100 Mb/s | 1M: 88% delivered / 1M: 85% delivered |
| mesh / UDP | 200 | 1M / 250K | 200 / 50 Mb/s | 2M: 42% loss / 500K: 11% loss |

### CPU for the same traffic

Host cores per 100 Mb/s delivered, at the highest rate both passed:

| pattern | rate per flow | host cores per 100 Mb/s | GNS3 uses |
|---|---|---|---|
| cs / TCP | 100K | 29.55 / 18.10 | 1.6× less |
| cs / UDP | 100K | 23.23 / 17.59 | 1.3× less |
| mesh / TCP | 500K | 5.78 / 1.95 | 3.0× less |
| mesh / UDP | 250K | 7.53 / 3.52 | 2.1× less |

## E3: a large lab at rest

**What it measures:** the idle CPU of a 400-host lab once the deploy's aftermath is
over. A platform can stay busy for minutes after a large deploy; on Docker Desktop for
Mac, for example, the UI re-lists every container after each container event. E1's
hold starts 30 s after the network is ready, so it still includes that work.

**How:** one E1 step at 400 hosts per platform, after E2.
1. After the settle, wait until the VM's CPU has stayed under 10% for 30 s (at most
   20 min).
2. Hold for 2 min.

| | AE3GIS | GNS3 |
|---|---|---|
| Time from the deploy until the VM is quiet | 66 s (already quiet at the first check) | 446 s |
| Host CPU 30 s after ready (E1's hold) | 0.19 cores | 0.90 cores |
| Host CPU at rest (E3's hold) | 0.18 cores | 0.89 cores |
| VM CPU at rest | 0.12 cores | 0.54 cores |

## Data

This folder holds the rest of the data:
- `summary.md`: every table;
- `summary.json`: the numbers;
- `ae3gis/` and `gns3/`: one JSON file per step;
- `attempts/`: the first try of AE3GIS's 800-host round 2;
- `manifest.json`: the run's plan and commit.

The log is `../2026-11-06-compare.log`, notes on how the run went are in
`../NOTES.md`, and the charts are in `analysis/platforms.ipynb`.
