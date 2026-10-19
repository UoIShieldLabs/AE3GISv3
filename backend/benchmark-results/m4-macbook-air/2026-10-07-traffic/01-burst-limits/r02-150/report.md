# Benchmark: m4-macbook-air · burst-limits · 150 hosts · round 2

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 12 cells on one deployment of 150 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 937.8 of 16746.1 MB used (5.6%) · host CPU 0.8% · Docker processes 265.6 MB · Docker's disk 69.7% used
- **Outcome:** 2 of 12 cells passed (10 degraded) · 2026-10-08T04:51:04 → 2026-10-08T05:20:45

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 150 | 1 | 161 | 160 | 21.8 | 1.22 | 13.4 | 13.7 | 15.8 | 1.3 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 12 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 73.3% | 72.0% | 77.3% | 77.7% | 77.7% |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 60.7% | 54.2% | 49.5% | 0.0% | 0.0% |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 4.58 | 2.35 | 1.25 | 0.74 | 0.50 |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 26.16 | 27.86 | 22.51 | 21.63 | 21.57 |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 89.0 | 88.4 | 88.5 | 87.6 | 87.3 |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 6.50 | 6.50 | 6.55 | 6.47 | 6.44 |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 66.9% | 68.5% | 70.5% | 72.7% | 75.9% |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 29.7% | 35.4% | 36.7% | 35.0% | 36.6% |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 9910.9 | 9231.8 | 8847.8 | 7932.1 | 6532.1 |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 8281 | 7524 | 8753 | 14775 | 17300 |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 98.7 | 98.5 | 98.7 | 98.5 | 98.8 |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 7.21 | 7.26 | 7.29 | 7.31 | 7.34 |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 100.2% | 99.9% | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 99.8% | 99.5% | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.48 | 0.34 | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.00 | 0.00 | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 76.3 | 71.3 | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 5.22 | 4.86 | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·udp·1M·500ms` | 150 | 150.00 | 77.3% | 49.5% | – | 1.25 | 22.51 | 1.1 → 89.6 | 6.55 | degraded: delivered 77.3% of what was asked (< 95%) |
| 2 | `mesh·tcp·1M·100ms` | 300 | 300.00 | 66.9% | 29.7% | 9910.9 | – | – | 1.1 → 99.7 | 7.21 | degraded: delivered 66.9% of what was asked (< 95%) |
| 3 | `cs·udp·1M·1000ms` | 150 | 150.00 | 77.7% | 0.0% | – | 0.74 | 21.63 | 1.1 → 88.7 | 6.47 | degraded: delivered 77.7% of what was asked (< 95%) |
| 4 | `mesh·tcp·1M·250ms` | 300 | 300.00 | 68.5% | 35.4% | 9231.8 | – | – | 1.1 → 99.6 | 7.26 | degraded: delivered 68.5% of what was asked (< 95%) |
| 5 | `mesh·tcp·1M·2000ms` | 300 | 300.00 | 75.9% | 36.6% | 6532.1 | – | – | 1.0 → 99.8 | 7.34 | degraded: delivered 75.9% of what was asked (< 95%) |
| 6 | `mesh·tcp·1M·1000ms` | 300 | 300.00 | 72.7% | 35.0% | 7932.1 | – | – | 1.2 → 99.7 | 7.31 | degraded: delivered 72.7% of what was asked (< 95%) |
| 7 | `mesh·udp·1M·100ms` | 300 | 300.00 | 100.2% | 99.8% | – | 0.48 | 0.00 | 1.3 → 77.6 | 5.22 | ok |
| 8 | `cs·udp·1M·250ms` | 150 | 150.00 | 72.0% | 54.2% | – | 2.35 | 27.86 | 1.1 → 89.5 | 6.50 | degraded: delivered 72.0% of what was asked (< 95%) |
| 9 | `cs·udp·1M·100ms` | 150 | 150.00 | 73.3% | 60.7% | – | 4.58 | 26.16 | 1.1 → 90.1 | 6.50 | degraded: delivered 73.3% of what was asked (< 95%) |
| 10 | `cs·udp·1M·2000ms` | 150 | 150.00 | 77.7% | 0.0% | – | 0.50 | 21.57 | 1.0 → 88.3 | 6.44 | degraded: delivered 77.7% of what was asked (< 95%) |
| 11 | `mesh·tcp·1M·500ms` | 300 | 300.00 | 70.5% | 36.7% | 8847.8 | – | – | 1.1 → 99.7 | 7.29 | degraded: delivered 70.5% of what was asked (< 95%) |
| 12 | `mesh·udp·1M·250ms` | 300 | 300.00 | 99.9% | 99.5% | – | 0.34 | 0.00 | 1.0 → 72.3 | 4.86 | ok |

Per image at 150 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 159 | 1.3 | 98.7% | – |
| `kathara/frr` | 2 | 1.4 | 1.3% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
