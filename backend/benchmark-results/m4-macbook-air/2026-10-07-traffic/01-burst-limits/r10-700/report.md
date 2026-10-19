# Benchmark: m4-macbook-air · burst-limits · 700 hosts · round 10

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `e2d8d34a0813` · bench
- **Environment fingerprint:** `036273b48a56817c3973529837184fdad38a1fb3b176fea81eb0198dd7e57ee8`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 11 cells on one deployment of 700 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 997.6 of 16746.1 MB used (6.0%) · host CPU 0.8% · Docker processes 268.5 MB · Docker's disk 79.6% used
- **Outcome:** 10 of 11 cells passed (1 degraded) · 2026-10-13T12:20:49 → 2026-10-13T13:12:22

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 700 | 1 | 742 | 741 | 193.4 | 8.20 | 185.8 | 13.0 | 16.0 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 11 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | 89.7% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | 0.0% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | 0.87 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | 0.66 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | 43.7 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | 3.24 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.1% | 100.1% | 100.8% | 100.3% | – |
| 100K | – | – | – | 101.3% | 100.9% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 97.8% | 96.0% | 99.2% | 97.8% | – |
| 100K | – | – | – | 98.3% | 96.6% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 64.8 | 34.0 | 2.7 | 4.9 | – |
| 100K | – | – | – | 8.3 | 15.4 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 1296 | 23225 | 7701 | 5044 | – |
| 100K | – | – | – | 10831 | 1862 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 87.9 | 68.5 | 43.3 | 39.5 | – |
| 100K | – | – | – | 66.4 | 69.7 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 6.15 | 4.75 | 3.04 | 2.95 | – |
| 100K | – | – | – | 4.85 | 5.12 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 100.4% | – | – | – |
| 100K | 100.2% | – | – | 101.6% | 103.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 100.4% | – | – | – |
| 100K | 99.8% | – | – | 98.3% | 96.7% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.30 | – | – | – |
| 100K | 0.43 | – | – | 0.21 | 0.18 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.00 | – | – | – |
| 100K | 0.00 | – | – | 0.00 | 0.00 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 31.9 | – | – | – |
| 100K | 47.2 | – | – | 30.5 | 29.1 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 2.16 | – | – | – |
| 100K | 2.87 | – | – | 2.18 | 2.13 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·50K·250ms` | 1400 | 70.00 | 100.1% | 96.0% | 34.0 | – | – | 6.5 → 75.0 | 4.75 | ok |
| 2 | `mesh·tcp·100K·1000ms` | 1400 | 140.00 | 101.3% | 98.3% | 8.3 | – | – | 6.9 → 73.3 | 4.85 | ok |
| 3 | `mesh·tcp·50K·500ms` | 1400 | 70.00 | 100.8% | 99.2% | 2.7 | – | – | 6.7 → 50.0 | 3.04 | ok |
| 4 | `mesh·tcp·100K·2000ms` | 1400 | 140.00 | 100.9% | 96.6% | 15.4 | – | – | 6.7 → 76.5 | 5.12 | ok |
| 5 | `mesh·udp·100K·1000ms` | 1400 | 140.00 | 101.6% | 98.3% | – | 0.21 | 0.00 | 6.7 → 37.2 | 2.18 | ok |
| 6 | `mesh·udp·100K·100ms` | 1400 | 140.00 | 100.2% | 99.8% | – | 0.43 | 0.00 | 6.7 → 53.9 | 2.87 | ok |
| 7 | `mesh·udp·100K·2000ms` | 1400 | 140.00 | 103.0% | 96.7% | – | 0.18 | 0.00 | 7.1 → 36.2 | 2.13 | ok |
| 8 | `mesh·tcp·50K·100ms` | 1400 | 70.00 | 100.1% | 97.8% | 64.8 | – | – | 6.9 → 94.8 | 6.15 | ok |
| 9 | `cs·udp·100K·1000ms` | 700 | 70.00 | 89.7% | 0.0% | – | 0.87 | 0.66 | 6.9 → 50.6 | 3.24 | degraded: delivered 89.7% of what was asked (< 95%) |
| 10 | `mesh·tcp·50K·1000ms` | 1400 | 70.00 | 100.3% | 97.8% | 4.9 | – | – | 7.1 → 46.6 | 2.95 | ok |
| 11 | `mesh·udp·50K·250ms` | 1400 | 70.00 | 100.4% | 100.4% | – | 0.30 | 0.00 | 6.8 → 38.6 | 2.16 | ok |

Per image at 700 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 737 | 1.2 | 99.3% | – |
| `kathara/frr` | 5 | 1.3 | 0.7% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
