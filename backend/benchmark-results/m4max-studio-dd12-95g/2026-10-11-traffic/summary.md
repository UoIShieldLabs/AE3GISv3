# Benchmark suite `traffic` on `m4max-studio-dd12-95g`

- **Suite:** The burst limits: for each of 100 traffic cells (5 rates × 5 burst intervals × TCP/UDP × clients → servers / mesh), the most hosts it comfortably supports and where it starts to fail, 50 hosts apart. Docker's kernel gets room for 16384 neighbour (ARP) entries (default 1024 for all nodes together, which cut off hosts past ~250 in mesh and ~500 clients → servers under traffic). (sha `e8c5f0bf8e36`)
- **AE3GIS:** `ab6c03795ae5`
- **Docker restart before each benchmark:** docker desktop restart
- **Kernel (set after every restart):** `net.ipv4.neigh.default.gc_thresh1=4096`, `net.ipv4.neigh.default.gc_thresh2=8192`, `net.ipv4.neigh.default.gc_thresh3=16384`, `net.ipv6.neigh.default.gc_thresh1=4096`, `net.ipv6.neigh.default.gc_thresh2=8192`, `net.ipv6.neigh.default.gc_thresh3=16384`
- **When:** 2026-10-11T14:08:53 → 2026-10-15T20:04:42 UTC

| # | Run | Status | Outcome | Memory used at rest | Report |
|---|---|---|---|---:|---|
| 01 | `burst-limits` | done | 100 of 100 cells' limits found, in 137 probes | – | – |

## Traffic limits: `burst-limits`

Hosts each cell comfortably supports / the size where it first fell below the threshold (50 hosts apart, the comfortable size passed twice). `mem` marks a host limit (memory, disk…) rather than traffic; `≥ N`: it never degraded up to N.

**cs · tcp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | ≥ 1000 | ≥ 1000 | ≥ 1000 | ≥ 1000 | ≥ 1000 |
| 100K | 950 / 1000 | 850 / 900 | 950 / 1000 | 950 / 1000 | 950 / 1000 |
| 250K | 400 / 450 mem | 400 / 450 | 400 / 450 | 400 / 450 | 400 / 450 |
| 500K | 200 / 250 | 200 / 250 | 200 / 250 | 200 / 250 | 200 / 250 |
| 1M | 100 / 150 | 100 / 150 | 100 / 150 | 100 / 150 | 100 / 150 |

**cs · udp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | ≥ 1000 | ≥ 1000 | ≥ 1000 | ≥ 1000 | ≥ 1000 |
| 100K | 950 / 1000 | ≥ 1000 | 950 / 1000 | ≥ 1000 | ≥ 1000 |
| 250K | 550 / 600 | 600 / 650 | 650 / 700 | 700 / 750 | 700 / 750 |
| 500K | 300 / 350 | 350 / 400 | 350 / 400 | 350 / 400 | 350 / 400 |
| 1M | 150 / 200 | 150 / 200 | 150 / 200 | 150 / 200 | 150 / 200 |

**mesh · tcp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 900 / 950 | 900 / 950 | 900 / 950 | 950 / 1000 | ≥ 1000 |
| 100K | 850 / 900 | 900 / 950 | 900 / 950 | 950 / 1000 | 950 / 1000 |
| 250K | 900 / 950 | 850 / 900 | 900 / 950 | 900 / 950 | 800 / 850 |
| 500K | 500 / 550 | 450 / 500 | 600 / 650 | 600 / 650 | 600 / 650 |
| 1M | 300 / 350 | 300 / 350 | 300 / 350 | 300 / 350 | 350 / 400 |

**mesh · udp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 900 / 950 | 900 / 950 | 950 / 1000 | 950 / 1000 | ≥ 1000 |
| 100K | 900 / 950 | 900 / 950 | 950 / 1000 | 950 / 1000 | 950 / 1000 |
| 250K | 850 / 900 | 900 / 950 | 900 / 950 | 950 / 1000 | ≥ 1000 |
| 500K | 800 / 850 | 850 / 900 | 900 / 950 | 900 / 950 | 950 / 1000 |
| 1M | 450 / 500 | 500 / 550 | 500 / 550 | 450 / 500 | 500 / 550 |
