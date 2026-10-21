# Benchmark: microsoft-surface-7 · burst-limits · 150 hosts · round 4

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `f6638a8abd99` · bench
- **Environment fingerprint:** `0b6ea01f7920c75dc4dae05dd5654af47479ee38b005cc61413deac517c9e66d`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 19 cells on one deployment of 150 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1110.9 of 16605.5 MB used (6.7%) · host CPU 16.7% · Docker processes 467.4 MB · Docker's disk 13.4% used
- **Outcome:** 14 of 19 cells passed (5 degraded) · 2026-10-12T16:47:45 → 2026-10-12T17:40:15

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 150 | 1 | 161 | 160 | 346.0 | 7.62 | 131.6 | 26.6 | 34.7 | 1.1 / 1.1 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 19 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 98.6% | 100.3% | 99.6% | 100.0% | 100.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 96.4% | 97.0% | 94.0% | 100.0% | 100.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 383.6 | 361.9 | 137.1 | 174.7 | 116.0 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 3795 | 3042 | 2087 | 1287 | 16 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 76.7 | 70.2 | 65.7 | 66.3 | 67.9 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 5.63 | 5.27 | 5.08 | 5.07 | 5.16 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 88.4% | 90.9% | 91.3% | 85.6% | 87.7% |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 10.72 | 9.60 | 5.46 | 1.66 | 2.10 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 8.25 | 5.86 | 4.51 | 6.34 | 9.69 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 76.1 | 73.4 | 71.3 | 71.0 | 70.2 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 5.69 | 5.56 | 5.47 | 5.47 | 5.41 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 97.6% | 99.9% | 99.9% | 100.0% | 100.0% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 66.4% | 98.0% | 97.0% | 96.0% | 100.0% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 3791.3 | 251.5 | 150.0 | 237.9 | 80.8 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 1397 | 5174 | 1133 | 477 | 51 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 88.6 | 80.9 | 81.3 | 81.5 | 79.3 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 6.34 | 6.02 | 5.98 | 6.04 | 5.85 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | 98.8% | 100.6% | 99.8% | 99.4% |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | 66.0% | 94.8% | 94.5% | 0.0% |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | 19.02 | 15.80 | 6.47 | 3.70 |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | 0.16 | 0.19 | 0.05 | 0.21 |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | 87.6 | 89.2 | 85.4 | 88.4 |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | 6.54 | 6.61 | 6.43 | 6.57 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·250K·2000ms` | 150 | 37.50 | 100.0% | 100.0% | 116.0 | – | – | 7.3 → 75.2 | 5.16 | ok |
| 2 | `cs·udp·500K·250ms` | 150 | 75.00 | 90.9% | 0.0% | – | 9.60 | 5.86 | 7.4 → 80.8 | 5.56 | degraded: delivered 90.9% of what was asked (< 95%) |
| 3 | `mesh·tcp·500K·100ms` | 300 | 150.00 | 97.6% | 66.4% | 3791.3 | – | – | 6.8 → 95.4 | 6.34 | ok |
| 4 | `mesh·tcp·500K·1000ms` | 300 | 150.00 | 100.0% | 96.0% | 237.9 | – | – | 7.4 → 88.9 | 6.04 | ok |
| 5 | `cs·udp·500K·500ms` | 150 | 75.00 | 91.3% | 0.0% | – | 5.46 | 4.51 | 7.6 → 78.9 | 5.47 | degraded: delivered 91.3% of what was asked (< 95%) |
| 6 | `mesh·udp·1M·2000ms` | 300 | 300.00 | 99.4% | 0.0% | – | 3.70 | 0.21 | 7.1 → 95.5 | 6.57 | ok |
| 7 | `cs·tcp·250K·250ms` | 150 | 37.50 | 100.3% | 97.0% | 361.9 | – | – | 7.0 → 77.2 | 5.27 | ok |
| 8 | `mesh·udp·1M·1000ms` | 300 | 300.00 | 99.8% | 94.5% | – | 6.47 | 0.05 | 8.3 → 93.7 | 6.43 | ok |
| 9 | `cs·udp·500K·100ms` | 150 | 75.00 | 88.4% | 0.0% | – | 10.72 | 8.25 | 7.0 → 83.1 | 5.69 | degraded: delivered 88.4% of what was asked (< 95%) |
| 10 | `cs·tcp·250K·1000ms` | 150 | 37.50 | 100.0% | 100.0% | 174.7 | – | – | 8.1 → 74.3 | 5.07 | ok |
| 11 | `mesh·tcp·500K·250ms` | 300 | 150.00 | 99.9% | 98.0% | 251.5 | – | – | 7.6 → 88.5 | 6.02 | ok |
| 12 | `mesh·tcp·500K·500ms` | 300 | 150.00 | 99.9% | 97.0% | 150.0 | – | – | 7.1 → 88.3 | 5.98 | ok |
| 13 | `cs·udp·500K·1000ms` | 150 | 75.00 | 85.6% | 0.0% | – | 1.66 | 6.34 | 7.8 → 78.8 | 5.47 | degraded: delivered 85.6% of what was asked (< 95%) |
| 14 | `mesh·udp·1M·500ms` | 300 | 300.00 | 100.6% | 94.8% | – | 15.80 | 0.19 | 6.9 → 96.1 | 6.61 | ok |
| 15 | `mesh·udp·1M·250ms` | 300 | 300.00 | 98.8% | 66.0% | – | 19.02 | 0.16 | 8.0 → 95.6 | 6.54 | ok |
| 16 | `cs·tcp·250K·500ms` | 150 | 37.50 | 99.6% | 94.0% | 137.1 | – | – | 8.2 → 73.9 | 5.08 | ok |
| 17 | `cs·tcp·250K·100ms` | 150 | 37.50 | 98.6% | 96.4% | 383.6 | – | – | 7.1 → 83.8 | 5.63 | ok |
| 18 | `cs·udp·500K·2000ms` | 150 | 75.00 | 87.7% | 0.0% | – | 2.10 | 9.69 | 7.0 → 77.3 | 5.41 | degraded: delivered 87.7% of what was asked (< 95%) |
| 19 | `mesh·tcp·500K·2000ms` | 300 | 150.00 | 100.0% | 100.0% | 80.8 | – | – | 7.3 → 86.6 | 5.85 | ok |

Per image at 150 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 159 | 1.1 | 94.6% | – |
| `kathara/frr` | 2 | 5.0 | 5.4% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
