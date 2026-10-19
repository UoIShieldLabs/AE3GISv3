# Benchmark: microsoft-surface-7 · burst-limits · 150 hosts · round 2

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `20c8b9e23b2c` · bench
- **Environment fingerprint:** `a02b71cc44f28564a30fb3a1573607c1e92ebc5eb806ee5b1065b52b94a52663`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 14 cells on one deployment of 150 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1102.3 of 16605.5 MB used (6.6%) · host CPU 12.1% · Docker processes 411.3 MB · Docker's disk 13.4% used
- **Outcome:** 9 of 14 cells passed (5 degraded) · 2026-10-11T21:57:07 → 2026-10-11T22:38:20

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 150 | 1 | 161 | 160 | 296.9 | 6.56 | 145.2 | 23.7 | 31.8 | 1.1 / 1.1 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 14 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 99.6% | 98.6% | 100.2% | 99.6% | 100.0% |
| 1M | 55.1% | – | 56.5% | 51.5% | 60.2% |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 96.0% | 91.5% | 100.0% | 96.0% | 100.0% |
| 1M | 13.8% | – | 6.0% | 10.0% | 17.0% |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 539.0 | 462.9 | 174.6 | 167.9 | 68.8 |
| 1M | 8712.1 | – | 8448.6 | 10052.2 | 8328.0 |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 4285 | 4537 | 1199 | 565 | 96 |
| 1M | 16388 | – | 15702 | 10219 | 15643 |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 86.6 | 83.3 | 81.6 | 81.4 | 78.4 |
| 1M | 91.3 | – | 91.0 | 90.7 | 91.5 |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 6.26 | 6.08 | 6.00 | 5.98 | 5.78 |
| 1M | 6.66 | – | 6.75 | 6.69 | 6.77 |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 94.4% | 96.7% | 99.6% | 99.2% | 99.5% |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 58.2% | 47.9% | 93.3% | 61.5% | 0.0% |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 24.90 | 21.49 | 13.54 | 16.68 | 3.81 |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.79 | 0.28 | 0.05 | 0.52 | 0.16 |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 89.5 | 90.1 | 89.0 | 87.3 | 88.2 |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 6.46 | 6.63 | 6.56 | 6.57 | 6.49 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·udp·1M·1000ms` | 300 | 300.00 | 99.2% | 61.5% | – | 16.68 | 0.52 | 8.2 → 95.5 | 6.57 | ok |
| 2 | `mesh·tcp·1M·500ms` | 300 | 300.00 | 56.5% | 6.0% | 8448.6 | – | – | 7.1 → 98.1 | 6.75 | degraded: delivered 56.5% of what was asked (< 95%) |
| 3 | `mesh·tcp·500K·1000ms` | 300 | 150.00 | 99.6% | 96.0% | 167.9 | – | – | 6.8 → 88.2 | 5.98 | ok |
| 4 | `mesh·udp·1M·100ms` | 300 | 300.00 | 94.4% | 58.2% | – | 24.90 | 0.79 | 6.5 → 96.0 | 6.46 | degraded: delivered 94.4% of what was asked (< 95%) |
| 5 | `mesh·tcp·1M·100ms` | 300 | 300.00 | 55.1% | 13.8% | 8712.1 | – | – | 6.5 → 97.9 | 6.66 | degraded: delivered 55.1% of what was asked (< 95%) |
| 6 | `mesh·udp·1M·2000ms` | 300 | 300.00 | 99.5% | 0.0% | – | 3.81 | 0.16 | 6.5 → 94.7 | 6.49 | ok |
| 7 | `mesh·udp·1M·250ms` | 300 | 300.00 | 96.7% | 47.9% | – | 21.49 | 0.28 | 6.8 → 97.0 | 6.63 | ok |
| 8 | `mesh·tcp·500K·500ms` | 300 | 150.00 | 100.2% | 100.0% | 174.6 | – | – | 6.7 → 88.3 | 6.00 | ok |
| 9 | `mesh·tcp·500K·250ms` | 300 | 150.00 | 98.6% | 91.5% | 462.9 | – | – | 6.6 → 89.9 | 6.08 | ok |
| 10 | `mesh·tcp·1M·2000ms` | 300 | 300.00 | 60.2% | 17.0% | 8328.0 | – | – | 6.6 → 98.1 | 6.77 | degraded: delivered 60.2% of what was asked (< 95%) |
| 11 | `mesh·tcp·500K·100ms` | 300 | 150.00 | 99.6% | 96.0% | 539.0 | – | – | 7.5 → 94.1 | 6.26 | ok |
| 12 | `mesh·tcp·500K·2000ms` | 300 | 150.00 | 100.0% | 100.0% | 68.8 | – | – | 7.1 → 85.5 | 5.78 | ok |
| 13 | `mesh·tcp·1M·1000ms` | 300 | 300.00 | 51.5% | 10.0% | 10052.2 | – | – | 6.5 → 97.3 | 6.69 | degraded: delivered 51.5% of what was asked (< 95%) |
| 14 | `mesh·udp·1M·500ms` | 300 | 300.00 | 99.6% | 93.3% | – | 13.54 | 0.05 | 6.7 → 95.7 | 6.56 | ok |

Per image at 150 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 159 | 1.1 | 94.6% | – |
| `kathara/frr` | 2 | 5.0 | 5.4% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
