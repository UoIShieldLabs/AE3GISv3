# Benchmark: m4-macbook-air · burst-limits · 100 hosts · round 2

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 5 cells on one deployment of 100 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 935.0 of 16746.1 MB used (5.6%) · host CPU 0.8% · Docker processes 266.2 MB · Docker's disk 69.7% used
- **Outcome:** 0 of 5 cells passed (5 degraded) · 2026-10-08T04:37:33 → 2026-10-08T04:50:13

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | 1 | 109 | 108 | 13.7 | 0.81 | 7.7 | 15.4 | 15.9 | 1.3 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 5 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 81.0% | 81.0% | 81.5% | 81.9% | 82.0% |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 56.1% | 61.5% | 57.0% | 64.1% | 56.6% |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 211.2 | 226.9 | 206.2 | 205.5 | 240.1 |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 7819 | 9083 | 8897 | 9839 | 8125 |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 88.8 | 87.9 | 89.1 | 88.0 | 88.3 |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 6.45 | 6.39 | 6.48 | 6.41 | 6.43 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·1M·250ms` | 100 | 100.00 | 81.0% | 61.5% | 226.9 | – | – | 0.8 → 88.7 | 6.39 | degraded: delivered 81.0% of what was asked (< 95%) |
| 2 | `cs·tcp·1M·2000ms` | 100 | 100.00 | 82.0% | 56.6% | 240.1 | – | – | 0.8 → 89.0 | 6.43 | degraded: delivered 82.0% of what was asked (< 95%) |
| 3 | `cs·tcp·1M·100ms` | 100 | 100.00 | 81.0% | 56.1% | 211.2 | – | – | 0.8 → 89.6 | 6.45 | degraded: delivered 81.0% of what was asked (< 95%) |
| 4 | `cs·tcp·1M·500ms` | 100 | 100.00 | 81.5% | 57.0% | 206.2 | – | – | 0.8 → 89.9 | 6.48 | degraded: delivered 81.5% of what was asked (< 95%) |
| 5 | `cs·tcp·1M·1000ms` | 100 | 100.00 | 81.9% | 64.1% | 205.5 | – | – | 0.8 → 88.8 | 6.41 | degraded: delivered 81.9% of what was asked (< 95%) |

Per image at 100 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 107 | 1.3 | 95.4% | – |
| `kathara/frr` | 2 | 3.2 | 4.6% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
