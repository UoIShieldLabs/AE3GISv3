# Benchmark: microsoft-surface-7 · burst-limits · 100 hosts · round 1

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `20c8b9e23b2c` · bench
- **Environment fingerprint:** `80bcc0f7cf6416d6093c854bced92b36fd9c47bcd0cf66b50bbcf2bab60c304b`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 100 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1029.1 of 16605.5 MB used (6.2%) · host CPU 10.6% · Docker processes 372.6 MB · Docker's disk 13.3% used
- **Outcome:** 4 of 10 cells passed (6 degraded) · 2026-10-11T10:27:35 → 2026-10-11T10:54:39

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | 1 | 109 | 108 | 142.7 | 4.79 | 65.4 | 31.5 | 39.4 | 1.2 / 1.1 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 73.3% | 71.7% | 75.8% | 67.6% | 74.1% |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 6.51 | 3.38 | 3.26 | 1.85 | 1.15 |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 23.92 | 21.67 | 22.42 | 25.38 | 24.24 |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 79.7 | 77.8 | 79.7 | 78.8 | 77.6 |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 5.90 | 5.80 | 5.95 | 5.90 | 5.81 |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 97.0% | 91.5% | 97.9% | 96.8% | 99.7% |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 50.4% | 42.0% | 36.0% | 41.0% | 84.0% |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 3183.6 | 3382.6 | 4299.9 | 3164.1 | 721.1 |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 1351 | 1815 | 2652 | 8362 | 563 |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 92.5 | 93.5 | 92.8 | 93.3 | 93.1 |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 6.71 | 6.79 | 6.78 | 6.86 | 6.79 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·udp·1M·1000ms` | 100 | 100.00 | 67.6% | 0.0% | – | 1.85 | 25.38 | 5.0 → 83.8 | 5.90 | degraded: delivered 67.6% of what was asked (< 95%) |
| 2 | `cs·udp·1M·500ms` | 100 | 100.00 | 75.8% | 0.0% | – | 3.26 | 22.42 | 4.9 → 84.6 | 5.95 | degraded: delivered 75.8% of what was asked (< 95%) |
| 3 | `mesh·tcp·1M·250ms` | 200 | 200.00 | 91.5% | 42.0% | 3382.6 | – | – | 4.8 → 98.2 | 6.79 | degraded: delivered 91.5% of what was asked (< 95%) |
| 4 | `cs·udp·1M·250ms` | 100 | 100.00 | 71.7% | 0.0% | – | 3.38 | 21.67 | 4.8 → 82.7 | 5.80 | degraded: delivered 71.7% of what was asked (< 95%) |
| 5 | `mesh·tcp·1M·2000ms` | 200 | 200.00 | 99.7% | 84.0% | 721.1 | – | – | 4.8 → 97.9 | 6.79 | ok |
| 6 | `mesh·tcp·1M·100ms` | 200 | 200.00 | 97.0% | 50.4% | 3183.6 | – | – | 5.2 → 97.7 | 6.71 | ok |
| 7 | `mesh·tcp·1M·1000ms` | 200 | 200.00 | 96.8% | 41.0% | 3164.1 | – | – | 4.9 → 98.2 | 6.86 | ok |
| 8 | `cs·udp·1M·100ms` | 100 | 100.00 | 73.3% | 0.0% | – | 6.51 | 23.92 | 4.9 → 84.6 | 5.90 | degraded: delivered 73.3% of what was asked (< 95%) |
| 9 | `cs·udp·1M·2000ms` | 100 | 100.00 | 74.1% | 0.0% | – | 1.15 | 24.24 | 5.0 → 82.6 | 5.81 | degraded: delivered 74.1% of what was asked (< 95%) |
| 10 | `mesh·tcp·1M·500ms` | 200 | 200.00 | 97.9% | 36.0% | 4299.9 | – | – | 4.9 → 97.7 | 6.78 | ok |

Per image at 100 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 107 | 1.1 | 92.3% | – |
| `kathara/frr` | 2 | 5.0 | 7.7% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
