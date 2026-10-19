# Benchmark: m4-macbook-air · burst-limits · 550 hosts · round 9

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `e2d8d34a0813` · bench
- **Environment fingerprint:** `036273b48a56817c3973529837184fdad38a1fb3b176fea81eb0198dd7e57ee8`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 17 cells on one deployment of 550 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1009.3 of 16746.1 MB used (6.0%) · host CPU 0.8% · Docker processes 281.9 MB · Docker's disk 78.1% used
- **Outcome:** 17 of 17 cells passed · 2026-10-13T06:52:35 → 2026-10-13T07:46:01

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 550 | 1 | 583 | 582 | 118.4 | 6.51 | 102.0 | 13.2 | 15.9 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 17 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 98.2% | – | 97.9% | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 73.7% | – | 64.1% | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 235.5 | – | 228.7 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 20776 | – | 30155 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 82.1 | – | 81.8 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 5.97 | – | 6.06 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.9% | – | – | – | – |
| 100K | – | 100.0% | – | – | 102.1% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.5% | – | – | – | – |
| 100K | – | 99.9% | – | – | 96.7% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 1.19 | – | – | – | – |
| 100K | – | 0.66 | – | – | 0.37 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.28 | – | – | – | – |
| 100K | – | 0.00 | – | – | 0.00 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 43.5 | – | – | – | – |
| 100K | – | 48.7 | – | – | 33.7 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 2.88 | – | – | – | – |
| 100K | – | 3.27 | – | – | 2.37 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.1% | 100.4% | 100.3% | 101.4% | 103.2% |
| 100K | – | – | – | 101.6% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.1% | 100.4% | 98.7% | 97.8% | 96.7% |
| 100K | – | – | – | 98.3% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 1.4 | 0.9 | 1.2 | 1.3 | 1.8 |
| 100K | – | – | – | 3.2 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 66 | 4762 | 1957 | 536 | 498 |
| 100K | – | – | – | 1793 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 69.5 | 39.9 | 38.1 | 26.9 | 25.8 |
| 100K | – | – | – | 48.5 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.53 | 2.67 | 2.62 | 1.89 | 1.78 |
| 100K | – | – | – | 3.35 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.2% | 100.4% | – | – | 102.8% |
| 100K | 100.1% | – | – | 101.5% | 102.8% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.1% | 100.4% | – | – | 96.7% |
| 100K | 99.7% | – | – | 98.3% | 96.5% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.89 | 0.17 | – | – | 0.18 |
| 100K | 0.24 | – | – | 0.17 | 0.14 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | – | – | 0.00 |
| 100K | 0.00 | – | – | 0.00 | 0.00 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 38.8 | 27.6 | – | – | 15.7 |
| 100K | 37.3 | – | – | 24.9 | 25.7 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 2.34 | 1.75 | – | – | 1.17 |
| 100K | 2.18 | – | – | 1.78 | 1.71 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·50K·500ms` | 1100 | 55.00 | 100.3% | 98.7% | 1.2 | – | – | 5.3 → 43.4 | 2.62 | ok |
| 2 | `mesh·udp·50K·2000ms` | 1100 | 55.00 | 102.8% | 96.7% | – | 0.18 | 0.00 | 4.6 → 20.3 | 1.17 | ok |
| 3 | `cs·udp·100K·2000ms` | 550 | 55.00 | 102.1% | 96.7% | – | 0.37 | 0.00 | 3.9 → 37.6 | 2.37 | ok |
| 4 | `mesh·tcp·50K·250ms` | 1100 | 55.00 | 100.4% | 100.4% | 0.9 | – | – | 5.0 → 45.0 | 2.67 | ok |
| 5 | `mesh·tcp·50K·100ms` | 1100 | 55.00 | 100.1% | 99.1% | 1.4 | – | – | 4.3 → 73.8 | 4.53 | ok |
| 6 | `mesh·udp·50K·100ms` | 1100 | 55.00 | 100.2% | 100.1% | – | 0.89 | 0.00 | 4.7 → 43.5 | 2.34 | ok |
| 7 | `mesh·udp·100K·1000ms` | 1100 | 110.00 | 101.5% | 98.3% | – | 0.17 | 0.00 | 5.3 → 30.1 | 1.78 | ok |
| 8 | `cs·udp·100K·250ms` | 550 | 55.00 | 100.0% | 99.9% | – | 0.66 | 0.00 | 4.3 → 53.0 | 3.27 | ok |
| 9 | `mesh·udp·100K·2000ms` | 1100 | 110.00 | 102.8% | 96.5% | – | 0.14 | 0.00 | 4.1 → 29.8 | 1.71 | ok |
| 10 | `cs·udp·50K·100ms` | 550 | 27.50 | 99.9% | 99.5% | – | 1.19 | 0.28 | 4.8 → 48.3 | 2.88 | ok |
| 11 | `cs·tcp·100K·500ms` | 550 | 55.00 | 97.9% | 64.1% | 228.7 | – | – | 4.5 → 86.4 | 6.06 | ok |
| 12 | `mesh·udp·50K·250ms` | 1100 | 55.00 | 100.4% | 100.4% | – | 0.17 | 0.00 | 4.0 → 31.5 | 1.75 | ok |
| 13 | `mesh·tcp·100K·1000ms` | 1100 | 110.00 | 101.6% | 98.3% | 3.2 | – | – | 4.6 → 53.0 | 3.35 | ok |
| 14 | `mesh·tcp·50K·1000ms` | 1100 | 55.00 | 101.4% | 97.8% | 1.3 | – | – | 4.3 → 31.2 | 1.89 | ok |
| 15 | `cs·tcp·100K·100ms` | 550 | 55.00 | 98.2% | 73.7% | 235.5 | – | – | 4.9 → 87.0 | 5.97 | ok |
| 16 | `mesh·tcp·50K·2000ms` | 1100 | 55.00 | 103.2% | 96.7% | 1.8 | – | – | 4.7 → 30.5 | 1.78 | ok |
| 17 | `mesh·udp·100K·100ms` | 1100 | 110.00 | 100.1% | 99.7% | – | 0.24 | 0.00 | 4.2 → 41.5 | 2.18 | ok |

Per image at 550 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 579 | 1.2 | 98.7% | – |
| `kathara/frr` | 4 | 2.3 | 1.3% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
