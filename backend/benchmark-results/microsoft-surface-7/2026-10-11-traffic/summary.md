# Benchmark suite `traffic` on `microsoft-surface-7`

- **Suite:** The burst limits: for each of 100 traffic cells (5 rates × 5 burst intervals × TCP/UDP × clients → servers / mesh), the most hosts it comfortably supports and where it starts to fail, 50 hosts apart. Docker's kernel gets room for 16384 neighbour (ARP) entries (default 1024 for all nodes together, which cut off hosts past ~250 in mesh and ~500 clients → servers under traffic). (sha `e8c5f0bf8e36`)
- **AE3GIS:** `f6638a8abd99`
- **Docker restart before each benchmark:** docker desktop restart
- **Kernel (set after every restart):** `net.ipv4.neigh.default.gc_thresh1=4096`, `net.ipv4.neigh.default.gc_thresh2=8192`, `net.ipv4.neigh.default.gc_thresh3=16384`, `net.ipv6.neigh.default.gc_thresh1=4096`, `net.ipv6.neigh.default.gc_thresh2=8192`, `net.ipv6.neigh.default.gc_thresh3=16384`
- **When:** 2026-10-11T10:09:20 → 2026-10-14T01:31:40 UTC

| # | Run | Status | Outcome | Memory used at rest | Report |
|---|---|---|---|---:|---|
| 01 | `burst-limits` | done | 100 of 100 cells' limits found, in 59 probes | – | – |

## Traffic limits: `burst-limits`

Hosts each cell comfortably supports / the size where it first fell below the threshold (50 hosts apart, the comfortable size passed twice). `mem` marks a host limit (memory, disk…) rather than traffic; `≥ N`: it never degraded up to N.

**cs · tcp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem |
| 100K | 300 / 350 | 300 / 350 | 250 / 300 | 350 / 400 | 350 / 400 |
| 250K | 150 / 200 | 150 / 200 | 150 / 200 | 150 / 200 | 150 / 200 |
| 500K | 100 / 150 | 100 / 150 | 50 / 100 | 100 / 150 | 100 / 150 |
| 1M | 50 / 100 | 50 / 100 | 50 / 100 | 50 / 100 | 50 / 100 |

**cs · udp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 350 / 400 | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem |
| 100K | 350 / 400 | 300 / 350 | 350 / 400 | 350 / 400 | 400 / 450 mem |
| 250K | 100 / 150 | 200 / 250 | 200 / 250 | 200 / 250 | 100 / 150 |
| 500K | 100 / 150 | 100 / 150 | 100 / 150 | 50 / 100 | 100 / 150 |
| 1M | 50 / 100 | 50 / 100 | 50 / 100 | 50 / 100 | 50 / 100 |

**mesh · tcp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem |
| 100K | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem |
| 250K | 250 / 300 | 250 / 300 | 300 / 350 | 250 / 300 | 300 / 350 |
| 500K | 150 / 200 | 150 / 200 | 150 / 200 | 150 / 200 | 150 / 200 |
| 1M | 100 / 150 | 50 / 100 | 50 / 100 | 100 / 150 | 100 / 150 |

**mesh · udp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem |
| 100K | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem |
| 250K | 300 / 350 | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem | 400 / 450 mem |
| 500K | 200 / 250 | 250 / 300 | 250 / 300 | 250 / 300 | 250 / 300 |
| 1M | 100 / 150 | 150 / 200 | 150 / 200 | 150 / 200 | 150 / 200 |

## Notes for this run (Surface, Docker Desktop on WSL2: 8 CPUs, 15.8 GiB)

- **The 450-host ceiling is deploy time, not memory or traffic.** Every probe of 450 hosts or more (479–690 nodes) stopped at deploy, after 1876–3604 s; none reached its cells. So `400 / 450 mem` means "the most this host deploys in time", for cells that never degraded up to 400.
- **Quiet wait shortened mid-run.** `quiet_timeout_s` was 1200 s up to round 3's 100-host probe, and 180 s from round 4 on (suite override, commit f6638a8). With fans, the host settled within 2 minutes after deploys and cells. At 260+ hosts its CPU floor stays above the 10% threshold, so the longer wait only added idle time; the 60 s idle gap before each cell is unchanged.
- **Interruptions.** Docker's VM hung (out of memory, no log after 23:01 UTC on 10-12) while tearing down the 500-host probe in round 4. It was stopped and restarted, the leftover lab destroyed, and the suite resumed at 04:52 UTC on 10-13; the interrupted probe's cells were asked again in round 5. One backend connection reset at 650 hosts was retried without loss.
