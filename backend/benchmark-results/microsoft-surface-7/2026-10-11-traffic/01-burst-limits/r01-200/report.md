# Benchmark: microsoft-surface-7 · burst-limits · 200 hosts · round 1

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `20c8b9e23b2c` · bench
- **Environment fingerprint:** `a02b71cc44f28564a30fb3a1573607c1e92ebc5eb806ee5b1065b52b94a52663`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 200 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1030.1 of 16605.5 MB used (6.2%) · host CPU 9.3% · Docker processes 370.5 MB · Docker's disk 13.3% used
- **Outcome:** 0 of 10 cells passed (10 degraded) · 2026-10-11T11:18:15 → 2026-10-11T11:55:57

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 200 | 1 | 213 | 212 | 428.9 | 7.58 | 239.3 | 24.4 | 32.6 | 1.1 / 1.1 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 80.8% | 80.2% | 77.5% | 77.5% | 93.8% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 25.5% | 32.9% | 22.0% | 18.0% | 26.0% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 9309.8 | 9216.8 | 9192.2 | 8475.1 | 5636.7 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 1721 | 1640 | 2760 | 3280 | 2965 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 86.7 | 86.2 | 86.8 | 84.9 | 87.4 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 6.21 | 6.38 | 6.44 | 6.34 | 6.52 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 67.5% | 64.8% | 71.8% | 73.5% | 74.9% |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 39.7% | 31.6% | 0.0% | 21.6% | 0.0% |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 33.49 | 30.84 | 25.76 | 26.96 | 24.27 |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 11.06 | 13.31 | 10.37 | 9.18 | 7.34 |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 86.5 | 88.1 | 88.5 | 88.6 | 87.3 |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 6.29 | 6.47 | 6.53 | 6.57 | 6.48 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·500K·1000ms` | 400 | 200.00 | 77.5% | 18.0% | 8475.1 | – | – | 9.1 → 94.0 | 6.34 | degraded: delivered 77.5% of what was asked (< 95%) |
| 2 | `mesh·tcp·500K·500ms` | 400 | 200.00 | 77.5% | 22.0% | 9192.2 | – | – | 8.5 → 95.3 | 6.44 | degraded: delivered 77.5% of what was asked (< 95%) |
| 3 | `mesh·udp·1M·250ms` | 400 | 400.00 | 64.8% | 31.6% | – | 30.84 | 13.31 | 8.2 → 96.3 | 6.47 | degraded: delivered 64.8% of what was asked (< 95%) |
| 4 | `mesh·tcp·500K·250ms` | 400 | 200.00 | 80.2% | 32.9% | 9216.8 | – | – | 8.8 → 95.0 | 6.38 | degraded: delivered 80.2% of what was asked (< 95%) |
| 5 | `mesh·udp·1M·2000ms` | 400 | 400.00 | 74.9% | 0.0% | – | 24.27 | 7.34 | 8.2 → 95.5 | 6.48 | degraded: delivered 74.9% of what was asked (< 95%) |
| 6 | `mesh·udp·1M·100ms` | 400 | 400.00 | 67.5% | 39.7% | – | 33.49 | 11.06 | 8.4 → 94.8 | 6.29 | degraded: delivered 67.5% of what was asked (< 95%) |
| 7 | `mesh·udp·1M·1000ms` | 400 | 400.00 | 73.5% | 21.6% | – | 26.96 | 9.18 | 8.0 → 96.7 | 6.57 | degraded: delivered 73.5% of what was asked (< 95%) |
| 8 | `mesh·tcp·500K·100ms` | 400 | 200.00 | 80.8% | 25.5% | 9309.8 | – | – | 8.0 → 94.7 | 6.21 | degraded: delivered 80.8% of what was asked (< 95%) |
| 9 | `mesh·tcp·500K·2000ms` | 400 | 200.00 | 93.8% | 26.0% | 5636.7 | – | – | 8.2 → 95.6 | 6.52 | degraded: delivered 93.8% of what was asked (< 95%) |
| 10 | `mesh·udp·1M·500ms` | 400 | 400.00 | 71.8% | 0.0% | – | 25.76 | 10.37 | 7.9 → 96.4 | 6.53 | degraded: delivered 71.8% of what was asked (< 95%) |

Per image at 200 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 211 | 1.1 | 95.8% | – |
| `kathara/frr` | 2 | 5.0 | 4.2% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
