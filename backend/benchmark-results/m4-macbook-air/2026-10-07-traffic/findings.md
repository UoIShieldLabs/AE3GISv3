# Traffic limits on the M4 MacBook Air: final results

> **Update, 2026-10-19 (re-measure in progress, paused):** a third re-check rule (`stalls`) dropped 30 old-driver results measured during the old driver's memory stalls. That re-opened 13 cells: the 5 ⚠ cells below, plus 8 mesh cells and one clients → servers cell whose failures were recorded under stalls. 10 of them are still being searched, so 90 of 100 cells are final; `summary.md` has the grids as they stand. Several re-opened cells already pass well above the limits below (mesh UDP 100K at 250 and 500 ms: ≥ 750, was 500/550; mesh TCP 100K at 500 ms: 800/1000, was 650/700). This page will be updated when the search finishes.

**Status:** complete. All 100 cells have a limit, from 165 probes over 20 rounds (2026-10-07 23:41 → 2026-10-16 08:04 UTC, with pauses).

- **Traffic driver:** fixed on 2026-10-12. The 54 cells measured with partial load before the fix were searched again with the fixed driver; the other 46 kept their results after a spot check reproduced 4 of them.
- **Caveat:** 5 mesh UDP cells still rest on a stop the old driver caused (see "Open caveat" below).
- **Raw grids:** the runner's own grids are in `summary.md`, and every probe's data is in `01-burst-limits/`.

## Setup

- **Machine:** M4 MacBook Air 15" (fanless), Docker Desktop VM with 8 CPUs and 16.7 GB, Kathará.
  - Neighbour (ARP) table raised to 16384 entries.
  - AE3GIS `e2d8d34a` (`feat/bench-suites`; the same code is `5911c166` on `feat/registry-images`).
- **Lab:** a generated campus of workstation hosts (`kathara/base`): 200 per subnet, 48 per switch, one server per 50 hosts, routers and a core.
- **Traffic:** iperf3 paced bursts (every interval, each flow sends *rate × interval* bytes at once).
  - **cs (clients → servers):** one flow per host, north–south through the routers and the core.
  - **mesh:** every host sends to its next two neighbours inside its LAN (2 flows per host).
- **Each cell:**
  1. Wait for a quiet host (up to 20 min), then idle 60 s.
  2. Start the traffic, with clients spread over 5 s.
  3. Measure 50 s, **from the moment every client is running** (fixed driver).
  - **Pass:** at least 95% delivered, and UDP loss ≤ 1%.
  - **Host limits:** memory > 90%, memory stalls > 10% or disk > 90% stop a cell as a host limit (`mem`).
- **Search:** grow by 25% while passing, then bisect to 50 hosts. The comfortable size must pass twice, and Docker is restarted before every size.

## Limits: comfortable / fails at (hosts)

`mem` marks a host limit (memory), not traffic.

**cs · tcp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 800 / 850 | 750 / 800 | 700 / 750 | 750 / 800 | 850 / 900 |
| 100K | 550 / 600 | 500 / 550 | 550 / 600 | 500 / 550 | 550 / 600 |
| 250K | 250 / 300 | 250 / 300 | 250 / 300 | 250 / 300 | 250 / 300 |
| 500K | 150 / 200 | 150 / 200 | 150 / 200 | 150 / 200 | 150 / 200 |
| 1M | 50 / 100 | 50 / 100 | 50 / 100 | 50 / 100 | 50 / 100 |

**cs · udp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 600 / 650 | 650 / 700 | 700 / 750 | 900 / 950 | 750 / 800 |
| 100K | 600 / 650 | 550 / 600 | 600 / 650 | 600 / 650 | 650 / 700 |
| 250K | 300 / 350 | 300 / 350 | 350 / 400 | 350 / 400 | 350 / 400 |
| 500K | 200 / 250 | 200 / 250 | 150 / 200 | 200 / 250 | 200 / 250 |
| 1M | 100 / 150 | 100 / 150 | 100 / 150 | 100 / 150 | 100 / 150 |

**mesh · tcp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 750 / 800 | 750 / 800 | 700 / 750 | 800 / 850 mem | 700 / 750 |
| 100K | 650 / 700 | 750 / 800 | 650 / 700 | 750 / 800 | 750 / 800 |
| 250K | 350 / 400 | 300 / 350 | 300 / 350 | 350 / 400 | 350 / 400 |
| 500K | 200 / 250 | 200 / 250 | 200 / 250 | 200 / 250 | 200 / 250 |
| 1M | 100 / 150 | 100 / 150 | 100 / 150 | 100 / 150 | 100 / 150 |

**mesh · udp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 700 / 750 | 800 / 850 mem | 650 / 700 mem ⚠ | 800 / 850 mem | 700 / 750 mem ⚠ |
| 100K | 750 / 800 | 500 / 550 mem ⚠ | 500 / 550 mem ⚠ | 750 / 800 | 800 / 850 mem |
| 250K | 400 / 450 | 500 / 550 | 500 / 550 mem ⚠ | 600 / 650 | 650 / 700 |
| 500K | 250 / 300 | 250 / 300 | 350 / 400 | 300 / 350 | 300 / 350 |
| 1M | 150 / 200 | 150 / 200 | 200 / 250 | 150 / 200 | 200 / 250 |

⚠ These cells rest on a stop the old driver caused; they're probably understated (see "Open caveat").

## Findings

1. **From 250 kb/s per host up, the limit is a throughput budget.** Hosts × rate stays roughly constant, so halving the rate about doubles the hosts.

   Traffic carried at the comfortable size (Mb/s offered, range over the five intervals):

   | scenario | 1M | 500K | 250K | 100K | 50K |
   |---|---:|---:|---:|---:|---:|
   | cs · tcp | 50 | 75 | 62 | 50–55 | 35–42 |
   | cs · udp | 100 | 75–100 | 75–88 | 55–65 | 30–45 |
   | mesh · tcp | 200 | 200 | 150–175 | 130–150 | 70–80 |
   | mesh · udp | 300–400 | 250–350 | 200–325 | 100–160 | 65–80 |

2. **At high rates the Mac runs out of CPU.**
   - At the failing size, host CPU is 85–90% for cs TCP, 68–90% for cs UDP (it starts losing packets before the CPU saturates), 98–100% for mesh TCP and 72–100% for mesh UDP.
   - Memory stays under ~50% there.
3. **North–south traffic costs about 3× more than east–west.**
   - A cs byte crosses switch → router → core → router → switch, about 6 node hops; a mesh byte crosses about 2.
   - The lab's CPU per 100 Mb/s delivered: about 7.5 cores for cs TCP, 4.3 for cs UDP, 2.6 for mesh TCP and 1.8 for mesh UDP.
4. **UDP holds 1.5–2× the hosts of TCP at high rates.**
   - cs: 100 vs 50 at 1M, 200 vs 150 at 500K, 300–350 vs 250 at 250K.
   - mesh: 150–200 vs 100 at 1M, 250–350 vs 200 at 500K.
5. **The burst interval matters for UDP at mid rates, not for TCP.**
   - TCP rows are flat across intervals from 250K up.
   - mesh UDP at 250K holds 400 hosts at 100 ms, 500 at 250 ms, 600 at 1 s and 650 at 2 s; cs UDP at 250K holds 300 at ≤ 250 ms and 350 at ≥ 500 ms.
   - At 50K and 100K the rows are noisy, within about 100 hosts, with no clear direction.
6. **Below about 100 kb/s per host, limits are 550–900 hosts**, and the Mac is near its limits on two fronts:
   - cs fails on CPU (83–90% at failure), with RTT and loss rising;
   - mesh TCP fails at 100% CPU;
   - several mesh cells reach 90% memory at 800–850 hosts (an idle lab of that size already uses about 12–13 GB of the 16.7).
7. **TCP latency degrades well before delivery fails.** RTT p95 at the comfortable size is:
   - 6–13 ms for cs TCP at 1M, 3–10 ms for mesh TCP at 1M;
   - but up to 200–320 ms for cs TCP at ≤ 500K, and up to 0.7–1.3 s for mesh TCP at 250K and 100K.
   - The 95%-delivered threshold is generous for latency-sensitive traffic.
8. **Near the top, results vary between passes.** Cells at 700–900 hosts sometimes passed and failed at the same size on different passes. For example, cs TCP 50K at 1 s passed once at 800 and 900 but failed at 800–1000 on other passes. The search keeps the conservative result, so treat limits above ~700 hosts as ±50–100 hosts.
9. **The high-rate limits reproduce.**
   - 35 of 37 high-rate cells matched the earlier default-kernel attempt exactly.
   - The spot check on the fixed driver reproduced all 4 kept cells at both of their sizes.

## What the driver fix changed

The old driver started about 40 processes a second, and the measured window began 5 s after the traffic was requested. In labs of 500+ hosts the clients were still starting through much of the window: mesh labs of 700+ hosts never ran at full load inside it. The fixed driver starts about 2000 processes a second, and the window waits for every client:
- **Start-up:** a median of 9.5 s and at most 44 s.
- **Unstarted clients:** only 2 of 240 cell runs had any client not started in time, and no limit is set by the tool.

Of the 54 cells searched again, 33 moved; the mean change was −17 hosts:
- **cs at 50K/100K: down 50–200 hosts.** The old passes at 800–950 ran at partial load.
- **mesh at 50K/100K: mostly up 50–200 hosts.** The old failures counted clients that never started.
- **mesh TCP 250K and mesh UDP 500K: down one step (50).**

## Open caveat: 5 cells from an old-driver artefact

Under the old driver, mesh labs of 500–800 hosts showed heavy memory stalls, with memory only ~61% used:

| Mesh, 500–800 hosts | Memory stalls (median / p90) | Memory used (median) |
|---|---:|---:|
| Old driver (95 runs) | 25 / 84 | 61% |
| New driver (99 runs) | 0 / 0 | 75% |

The old driver forked its own Python process for every start, and that, not the lab, caused the stalls. The fixed driver stops on memory only when memory actually reaches 90%.

Five final cells still rest on an old-driver stop of that kind: the ⚠ cells above. The re-check after the fix only re-opened traffic failures, so these stayed. They are mesh UDP 50K at 500 ms (650/700), 50K at 2 s (700/750), 100K at 250 ms and 500 ms (500/550), and 250K at 500 ms (500/550).
- **What it means:** their neighbours reach 650–800, so these limits are probably understated.
- **The fix:** re-measuring them on the fixed driver would take about 4–6 h.

## Files

- **This folder:**
  - `summary.md`: the runner's grids.
  - `limits-burst-limits.json`: every cell's result.
  - `manifest.json`: every probe, and the results dropped on 2026-10-13 under `reopened`.
  - `01-burst-limits/rNN-<hosts>/`: each probe's report, `benchmark.json` and export.
- **Log:** `../traffic-limits.log`.
- **Superseded:** `summary-partial.md` (2026-10-09, before the fix).
