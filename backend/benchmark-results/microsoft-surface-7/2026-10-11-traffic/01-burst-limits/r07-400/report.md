# Benchmark: microsoft-surface-7 · burst-limits · 400 hosts · round 7

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `f6638a8abd99` · bench
- **Environment fingerprint:** `35ffbf9e79e8826491c22ff6c473b23bcd00e104d4b9f8bb6fd617afa3d87d28`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 24 cells on one deployment of 400 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1090.8 of 16605.5 MB used (6.6%) · host CPU 24.5% · Docker processes 444.9 MB · Docker's disk 13.5% used
- **Outcome:** 24 of 24 cells passed · 2026-10-13T19:51:06 → 2026-10-13T22:34:17

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 400 | 1 | 424 | 423 | 1654.8 | 24.08 | 817.4 | – | – | – / – | – | – | – | – | – | – | – | ok |

Traffic matrix: 24 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.9% | 100.3% | 100.8% | 102.1% | 103.1% |
| 100K | 99.4% | 98.1% | 99.9% | 100.2% | 100.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 95.3% | 90.8% | 96.6% | 96.5% | 90.0% |
| 100K | 92.3% | 74.9% | 88.3% | 96.6% | 86.7% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 92.0 | 58.9 | 7.3 | 7.1 | 9.6 |
| 100K | 280.4 | 286.7 | 65.7 | 48.4 | 47.1 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 167 | 6934 | 3284 | 1482 | 500 |
| 100K | 961 | 5500 | 5389 | 4129 | 288 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 59.3 | 53.8 | 48.5 | 42.3 | 43.2 |
| 100K | 64.4 | 59.9 | 49.0 | 60.1 | 53.2 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.69 | 4.26 | 4.10 | 3.81 | 3.83 |
| 100K | 4.80 | 4.65 | 4.41 | 4.78 | 4.55 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.2% | 100.6% | 100.5% | 102.6% | 103.6% |
| 100K | 100.1% | 99.7% | 101.2% | 101.7% | 102.3% |
| 250K | – | 98.9% | 99.5% | 99.8% | 100.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 98.2% | 99.0% | 98.0% | 96.6% | 93.3% |
| 100K | 75.2% | 97.6% | 98.2% | 96.6% | 93.3% |
| 250K | – | 82.0% | 91.1% | 96.5% | 93.3% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 14.40 | 5.50 | 2.61 | 0.99 | 0.89 |
| 100K | 15.67 | 13.53 | 2.09 | 1.58 | 1.30 |
| 250K | – | 52.91 | 33.56 | 13.31 | 7.42 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 100K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 250K | – | 0.00 | 0.00 | 0.00 | 0.01 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 49.3 | 46.9 | 41.1 | 38.7 | 38.1 |
| 100K | 49.9 | 50.0 | 50.5 | 45.6 | 44.5 |
| 250K | – | 55.1 | 61.1 | 55.3 | 59.4 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.10 | 3.74 | 3.64 | 3.23 | 3.30 |
| 100K | 4.08 | 4.31 | 4.03 | 3.86 | 3.72 |
| 250K | – | 4.72 | 4.83 | 4.87 | 4.82 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·100K·1000ms` | 800 | 80.00 | 100.2% | 96.6% | 48.4 | – | – | 16.9 → 77.0 | 4.78 | ok |
| 2 | `mesh·udp·100K·1000ms` | 800 | 80.00 | 101.7% | 96.6% | – | 1.58 | 0.00 | 17.4 → 63.0 | 3.86 | ok |
| 3 | `mesh·udp·50K·500ms` | 800 | 40.00 | 100.5% | 98.0% | – | 2.61 | 0.00 | 19.9 → 61.0 | 3.64 | ok |
| 4 | `mesh·udp·250K·250ms` | 800 | 200.00 | 98.9% | 82.0% | – | 52.91 | 0.00 | 21.7 → 76.8 | 4.72 | ok |
| 5 | `mesh·tcp·100K·500ms` | 800 | 80.00 | 99.9% | 88.3% | 65.7 | – | – | 23.5 → 72.5 | 4.41 | ok |
| 6 | `mesh·udp·50K·250ms` | 800 | 40.00 | 100.6% | 99.0% | – | 5.50 | 0.00 | 16.9 → 63.8 | 3.74 | ok |
| 7 | `mesh·udp·250K·500ms` | 800 | 200.00 | 99.5% | 91.1% | – | 33.56 | 0.00 | 17.0 → 78.1 | 4.83 | ok |
| 8 | `mesh·udp·250K·2000ms` | 800 | 200.00 | 100.0% | 93.3% | – | 7.42 | 0.01 | 17.2 → 76.6 | 4.82 | ok |
| 9 | `mesh·udp·50K·100ms` | 800 | 40.00 | 100.2% | 98.2% | – | 14.40 | 0.00 | 20.8 → 70.1 | 4.10 | ok |
| 10 | `mesh·udp·100K·250ms` | 800 | 80.00 | 99.7% | 97.6% | – | 13.53 | 0.00 | 21.2 → 71.2 | 4.31 | ok |
| 11 | `mesh·udp·100K·100ms` | 800 | 80.00 | 100.1% | 75.2% | – | 15.67 | 0.00 | 19.9 → 69.8 | 4.08 | ok |
| 12 | `mesh·udp·100K·2000ms` | 800 | 80.00 | 102.3% | 93.3% | – | 1.30 | 0.00 | 16.3 → 60.9 | 3.72 | ok |
| 13 | `mesh·udp·50K·1000ms` | 800 | 40.00 | 102.6% | 96.6% | – | 0.99 | 0.00 | 16.8 → 55.5 | 3.23 | ok |
| 14 | `mesh·tcp·50K·1000ms` | 800 | 40.00 | 102.1% | 96.5% | 7.1 | – | – | 21.5 → 63.8 | 3.81 | ok |
| 15 | `mesh·tcp·100K·100ms` | 800 | 80.00 | 99.4% | 92.3% | 280.4 | – | – | 17.5 → 82.0 | 4.80 | ok |
| 16 | `mesh·tcp·100K·250ms` | 800 | 80.00 | 98.1% | 74.9% | 286.7 | – | – | 18.2 → 78.1 | 4.65 | ok |
| 17 | `mesh·tcp·50K·250ms` | 800 | 40.00 | 100.3% | 90.8% | 58.9 | – | – | 17.4 → 71.2 | 4.26 | ok |
| 18 | `mesh·tcp·50K·2000ms` | 800 | 40.00 | 103.1% | 90.0% | 9.6 | – | – | 19.9 → 63.1 | 3.83 | ok |
| 19 | `mesh·tcp·50K·500ms` | 800 | 40.00 | 100.8% | 96.6% | 7.3 | – | – | 18.9 → 67.5 | 4.10 | ok |
| 20 | `mesh·udp·100K·500ms` | 800 | 80.00 | 101.2% | 98.2% | – | 2.09 | 0.00 | 16.6 → 67.0 | 4.03 | ok |
| 21 | `mesh·tcp·50K·100ms` | 800 | 40.00 | 99.9% | 95.3% | 92.0 | – | – | 20.7 → 80.0 | 4.69 | ok |
| 22 | `mesh·tcp·100K·2000ms` | 800 | 80.00 | 100.0% | 86.7% | 47.1 | – | – | 20.4 → 73.7 | 4.55 | ok |
| 23 | `mesh·udp·50K·2000ms` | 800 | 40.00 | 103.6% | 93.3% | – | 0.89 | 0.00 | 16.4 → 54.5 | 3.30 | ok |
| 24 | `mesh·udp·250K·1000ms` | 800 | 200.00 | 99.8% | 96.5% | – | 13.31 | 0.00 | 21.7 → 77.0 | 4.87 | ok |

Per image at 400 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | – | – | – | – |
| `kathara/frr` | – | – | – | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
