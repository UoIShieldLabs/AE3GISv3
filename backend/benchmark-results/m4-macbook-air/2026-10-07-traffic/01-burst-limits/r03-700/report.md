# Benchmark: m4-macbook-air · burst-limits · 700 hosts · round 3

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 12 cells on one deployment of 700 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 965.9 of 16746.1 MB used (5.8%) · host CPU 0.8% · Docker processes 263.8 MB · Docker's disk 72.0% used
- **Outcome:** 9 of 12 cells passed (3 degraded) · 2026-10-08T15:21:54 → 2026-10-08T16:28:34

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 700 | 1 | 742 | 741 | 186.6 | 8.72 | 190.7 | 13.2 | 15.7 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 12 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.2% | – | – | – | – |
| 100K | 98.7% | – | 98.7% | 100.3% | 101.9% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.7% | – | – | – | – |
| 100K | 0.0% | – | 93.8% | 96.0% | 96.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.97 | – | – | – | – |
| 100K | 21.01 | – | 3.95 | 3.37 | 0.50 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | – | – | – | – |
| 100K | 1.12 | – | 2.18 | 0.81 | 0.00 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 60.2 | – | – | – | – |
| 100K | 65.2 | – | 56.6 | 45.8 | 44.5 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 3.82 | – | – | – | – |
| 100K | 4.20 | – | 3.92 | 3.23 | 3.17 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 79.9% | 100.1% | 101.3% | – | 107.7% |
| 100K | – | – | – | – | 104.7% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.0% | 92.4% | 88.2% | – | 93.0% |
| 100K | – | – | – | – | 94.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 79.4 | 99.4 | 42.0 | – | 3.4 |
| 100K | – | – | – | – | 203.9 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 74 | 17658 | 8405 | – | 465 |
| 100K | – | – | – | – | 3440 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 64.0 | 61.0 | 53.0 | – | 36.9 |
| 100K | – | – | – | – | 61.2 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 3.65 | 3.57 | 2.83 | – | 1.75 |
| 100K | – | – | – | – | 3.67 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 107.2% |
| 100K | – | – | – | – | 106.6% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 92.8% |
| 100K | – | – | – | – | 92.6% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 0.22 |
| 100K | – | – | – | – | 18.71 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 0.00 |
| 100K | – | – | – | – | 0.00 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 29.3 |
| 100K | – | – | – | – | 34.6 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 1.18 |
| 100K | – | – | – | – | 1.68 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·udp·100K·500ms` | 700 | 70.00 | 98.7% | 93.8% | – | 3.95 | 2.18 | 6.9 → 63.6 | 3.92 | degraded: UDP loss 2.18% > 1.0% |
| 2 | `mesh·tcp·50K·100ms` | 1400 | 70.00 | 79.9% | 0.0% | 79.4 | – | – | 7.0 → 71.0 | 3.65 | degraded: delivered 79.9% of what was asked (< 95%) |
| 3 | `cs·udp·100K·1000ms` | 700 | 70.00 | 100.3% | 96.0% | – | 3.37 | 0.81 | 7.1 → 52.9 | 3.23 | ok |
| 4 | `mesh·tcp·50K·250ms` | 1400 | 70.00 | 100.1% | 92.4% | 99.4 | – | – | 7.0 → 67.9 | 3.57 | ok |
| 5 | `mesh·tcp·100K·2000ms` | 1400 | 140.00 | 104.7% | 94.0% | 203.9 | – | – | 4.6 → 65.9 | 3.67 | ok |
| 6 | `mesh·tcp·50K·2000ms` | 1400 | 70.00 | 107.7% | 93.0% | 3.4 | – | – | 5.4 → 42.2 | 1.75 | ok |
| 7 | `mesh·udp·50K·2000ms` | 1400 | 70.00 | 107.2% | 92.8% | – | 0.22 | 0.00 | 4.4 → 33.7 | 1.18 | ok |
| 8 | `cs·udp·100K·100ms` | 700 | 70.00 | 98.7% | 0.0% | – | 21.01 | 1.12 | 5.7 → 70.8 | 4.20 | degraded: UDP loss 1.12% > 1.0% |
| 9 | `cs·udp·50K·100ms` | 700 | 35.00 | 100.2% | 99.7% | – | 4.97 | 0.00 | 5.1 → 65.3 | 3.82 | ok |
| 10 | `cs·udp·100K·2000ms` | 700 | 70.00 | 101.9% | 96.0% | – | 0.50 | 0.00 | 6.7 → 51.2 | 3.17 | ok |
| 11 | `mesh·tcp·50K·500ms` | 1400 | 70.00 | 101.3% | 88.2% | 42.0 | – | – | 6.5 → 59.6 | 2.83 | ok |
| 12 | `mesh·udp·100K·2000ms` | 1400 | 140.00 | 106.6% | 92.6% | – | 18.71 | 0.00 | 6.8 → 41.4 | 1.68 | ok |

Per image at 700 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 737 | 1.2 | 99.3% | – |
| `kathara/frr` | 5 | 1.3 | 0.7% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
