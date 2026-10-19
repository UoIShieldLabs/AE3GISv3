# Benchmark suite `traffic` on `m4-macbook-air`

- **Suite:** The burst limits: for each of 100 traffic cells (5 rates × 5 burst intervals × TCP/UDP × clients → servers / mesh), the most hosts it comfortably supports and where it starts to fail, 50 hosts apart. Docker's kernel gets room for 16384 neighbour (ARP) entries (default 1024 for all nodes together, which cut off hosts past ~250 in mesh and ~500 clients → servers under traffic). (sha `e8c5f0bf8e36`)
- **AE3GIS:** `9517ee6218a2`
- **Docker restart before each benchmark:** docker desktop restart
- **Kernel (set after every restart):** `net.ipv4.neigh.default.gc_thresh1=4096`, `net.ipv4.neigh.default.gc_thresh2=8192`, `net.ipv4.neigh.default.gc_thresh3=16384`, `net.ipv6.neigh.default.gc_thresh1=4096`, `net.ipv6.neigh.default.gc_thresh2=8192`, `net.ipv6.neigh.default.gc_thresh3=16384`
- **When:** 2026-10-07T23:41:31 → 2026-10-16T08:04:39 UTC

| # | Run | Status | Outcome | Memory used at rest | Report |
|---|---|---|---|---:|---|
| 01 | `burst-limits` | running | 90 of 100 cells' limits found, in 182 probes | – | – |

## Traffic limits: `burst-limits`

Hosts each cell comfortably supports / the size where it first fell below the threshold (50 hosts apart, the comfortable size passed twice). `mem` marks a host limit (memory, disk…) rather than traffic, `tool` the traffic tool's (clients not started in time); `≥ N`: it never degraded up to N.

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
| 50K | 750 / 800 | 750 / 800 | 700 / 750 | 800 / 850 mem | 750 / 800 … |
| 100K | 700 / 750 … | 750 / 800 | 800 / 1000 mem … | 750 / 800 | 750 / 850 … |
| 250K | 350 / 400 | 300 / 350 | 300 / 350 | 350 / 400 | 350 / 400 |
| 500K | 200 / 250 | 200 / 250 | 200 / 250 | 200 / 250 | 200 / 250 |
| 1M | 100 / 150 | 100 / 150 | 100 / 150 | 100 / 150 | 100 / 150 |

**mesh · udp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 800 / 900 mem … | 800 / 850 mem | ≥ 800 … | 800 / 850 mem | 700 / 900 mem … |
| 100K | 750 / 800 | ≥ 750 … | ≥ 750 … | 750 / 800 | 800 / 850 mem |
| 250K | 400 / 450 | 550 / 600 | 600 / 700 … | 600 / 650 | 650 / 700 |
| 500K | 250 / 300 | 250 / 300 | 350 / 400 | 300 / 350 | 300 / 350 |
| 1M | 150 / 200 | 150 / 200 | 200 / 250 | 150 / 200 | 200 / 250 |
