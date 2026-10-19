# Benchmark: microsoft-surface-7 · burst-limits · 400 hosts · round 2

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `20c8b9e23b2c` · bench
- **Environment fingerprint:** `80bcc0f7cf6416d6093c854bced92b36fd9c47bcd0cf66b50bbcf2bab60c304b`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 25 cells on one deployment of 400 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1045.1 of 16605.5 MB used (6.3%) · host CPU 14.3% · Docker processes 397.2 MB · Docker's disk 13.4% used
- **Outcome:** 24 of 25 cells passed (1 degraded) · 2026-10-12T03:29:37 → 2026-10-12T13:15:56

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 400 | 1 | 424 | 423 | 1333.1 | 22.08 | 750.9 | 26.3 | 34.6 | 1.1 / 1.1 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 25 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.7% | 100.1% | 100.7% | 101.7% | 101.6% |
| 100K | 99.9% | 99.7% | 98.8% | 100.2% | 100.4% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 94.6% | 95.8% | 96.2% | 96.6% | 93.3% |
| 100K | 88.9% | 92.5% | 86.6% | 94.9% | 93.3% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 119.5 | 73.4 | 15.5 | 9.3 | 11.6 |
| 100K | 254.3 | 319.1 | 155.8 | 253.0 | 86.6 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 284 | 13452 | 5912 | 2135 | 1071 |
| 100K | 789 | 9596 | 9324 | 5090 | 468 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 66.3 | 59.1 | 55.8 | 50.0 | 47.7 |
| 100K | 66.7 | 65.3 | 64.1 | 59.2 | 60.2 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.81 | 4.51 | 4.30 | 4.02 | 3.91 |
| 100K | 4.87 | 4.92 | 4.89 | 4.80 | 4.64 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.2% | 100.5% | 99.9% | 102.2% | 102.6% |
| 100K | 100.2% | 100.0% | 101.0% | 101.2% | 101.4% |
| 250K | 82.8% | 100.2% | 100.1% | 103.2% | 100.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 96.7% | 99.0% | 98.3% | 96.6% | 93.3% |
| 100K | 98.3% | 97.5% | 98.2% | 96.6% | 93.3% |
| 250K | 10.3% | 91.6% | 93.3% | 89.1% | 95.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 10.32 | 2.98 | 2.10 | 1.35 | 1.24 |
| 100K | 27.17 | 6.18 | 3.60 | 1.46 | 1.43 |
| 250K | 81.42 | 27.50 | 21.12 | 13.34 | 7.38 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 100K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 250K | 0.46 | 0.00 | 0.00 | 0.01 | 0.00 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 57.2 | 48.8 | 44.5 | 42.4 | 38.7 |
| 100K | 53.1 | 56.1 | 51.9 | 48.5 | 49.2 |
| 250K | 72.4 | 66.6 | 62.3 | 69.2 | 68.7 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.12 | 3.80 | 3.59 | 3.48 | 3.16 |
| 100K | 4.04 | 4.26 | 4.06 | 3.93 | 3.86 |
| 250K | 5.29 | 5.02 | 4.96 | 5.29 | 5.32 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·100K·1000ms` | 800 | 80.00 | 100.2% | 94.9% | 253.0 | – | – | 18.4 → 77.6 | 4.80 | ok |
| 2 | `mesh·udp·100K·2000ms` | 800 | 80.00 | 101.4% | 93.3% | – | 1.43 | 0.00 | 14.2 → 63.5 | 3.86 | ok |
| 3 | `mesh·udp·50K·500ms` | 800 | 40.00 | 99.9% | 98.3% | – | 2.10 | 0.00 | 15.5 → 60.0 | 3.59 | ok |
| 4 | `mesh·udp·250K·250ms` | 800 | 200.00 | 100.2% | 91.6% | – | 27.50 | 0.00 | 15.2 → 81.8 | 5.02 | ok |
| 5 | `mesh·tcp·100K·500ms` | 800 | 80.00 | 98.8% | 86.6% | 155.8 | – | – | 15.3 → 79.4 | 4.89 | ok |
| 6 | `mesh·udp·50K·250ms` | 800 | 40.00 | 100.5% | 99.0% | – | 2.98 | 0.00 | 16.0 → 64.8 | 3.80 | ok |
| 7 | `mesh·udp·250K·2000ms` | 800 | 200.00 | 100.0% | 95.0% | – | 7.38 | 0.00 | 15.2 → 83.9 | 5.32 | ok |
| 8 | `mesh·udp·250K·1000ms` | 800 | 200.00 | 103.2% | 89.1% | – | 13.34 | 0.01 | 14.8 → 84.1 | 5.29 | ok |
| 9 | `mesh·udp·50K·100ms` | 800 | 40.00 | 100.2% | 96.7% | – | 10.32 | 0.00 | 15.1 → 72.3 | 4.12 | ok |
| 10 | `mesh·udp·250K·100ms` | 800 | 200.00 | 82.8% | 10.3% | – | 81.42 | 0.46 | 14.3 → 86.7 | 5.29 | degraded: delivered 82.8% of what was asked (< 95%) |
| 11 | `mesh·udp·100K·100ms` | 800 | 80.00 | 100.2% | 98.3% | – | 27.17 | 0.00 | 16.7 → 69.9 | 4.04 | ok |
| 12 | `mesh·udp·100K·1000ms` | 800 | 80.00 | 101.2% | 96.6% | – | 1.46 | 0.00 | 15.1 → 63.6 | 3.93 | ok |
| 13 | `mesh·udp·50K·1000ms` | 800 | 40.00 | 102.2% | 96.6% | – | 1.35 | 0.00 | 15.6 → 58.1 | 3.48 | ok |
| 14 | `mesh·tcp·50K·1000ms` | 800 | 40.00 | 101.7% | 96.6% | 9.3 | – | – | 16.4 → 66.3 | 4.02 | ok |
| 15 | `mesh·tcp·100K·100ms` | 800 | 80.00 | 99.9% | 88.9% | 254.3 | – | – | 15.4 → 82.1 | 4.87 | ok |
| 16 | `mesh·tcp·100K·250ms` | 800 | 80.00 | 99.7% | 92.5% | 319.1 | – | – | 15.6 → 80.9 | 4.92 | ok |
| 17 | `mesh·udp·100K·250ms` | 800 | 80.00 | 100.0% | 97.5% | – | 6.18 | 0.00 | 15.5 → 71.7 | 4.26 | ok |
| 18 | `mesh·tcp·50K·250ms` | 800 | 40.00 | 100.1% | 95.8% | 73.4 | – | – | 16.1 → 75.2 | 4.51 | ok |
| 19 | `mesh·tcp·50K·2000ms` | 800 | 40.00 | 101.6% | 93.3% | 11.6 | – | – | 17.3 → 65.0 | 3.91 | ok |
| 20 | `mesh·tcp·50K·500ms` | 800 | 40.00 | 100.7% | 96.2% | 15.5 | – | – | 15.2 → 71.0 | 4.30 | ok |
| 21 | `mesh·udp·100K·500ms` | 800 | 80.00 | 101.0% | 98.2% | – | 3.60 | 0.00 | 15.2 → 67.1 | 4.06 | ok |
| 22 | `mesh·tcp·50K·100ms` | 800 | 40.00 | 99.7% | 94.6% | 119.5 | – | – | 15.2 → 81.5 | 4.81 | ok |
| 23 | `mesh·tcp·100K·2000ms` | 800 | 80.00 | 100.4% | 93.3% | 86.6 | – | – | 15.1 → 75.2 | 4.64 | ok |
| 24 | `mesh·udp·50K·2000ms` | 800 | 40.00 | 102.6% | 93.3% | – | 1.24 | 0.00 | 14.5 → 53.2 | 3.16 | ok |
| 25 | `mesh·udp·250K·500ms` | 800 | 200.00 | 100.1% | 93.3% | – | 21.12 | 0.00 | 16.3 → 78.7 | 4.96 | ok |

Per image at 400 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 421 | 1.1 | 97.6% | – |
| `kathara/frr` | 3 | 3.7 | 2.4% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
