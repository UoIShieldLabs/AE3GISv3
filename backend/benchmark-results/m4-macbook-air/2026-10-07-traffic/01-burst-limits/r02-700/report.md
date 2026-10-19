# Benchmark: m4-macbook-air · burst-limits · 700 hosts · round 2

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 14 cells on one deployment of 700 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 952.3 of 16746.1 MB used (5.7%) · host CPU 0.8% · Docker processes 270.9 MB · Docker's disk 70.5% used
- **Outcome:** 11 of 13 cells passed (1 degraded, 1 stopped) · 2026-10-08T08:38:30 → 2026-10-08T09:34:04

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 700 | 1 | 742 | 741 | 199.6 | 8.12 | 199.3 | 13.2 | 15.7 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 13 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 105.0% | – |
| 100K | 95.7% | 98.5% | 100.4% | 100.8% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 82.0% | – |
| 100K | 0.0% | 0.0% | 84.9% | 86.7% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 7.6 | – |
| 100K | 729.5 | 872.5 | 376.7 | 596.5 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 808 | – |
| 100K | 841 | 10384 | 10054 | 7431 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 39.9 | – |
| 100K | 64.5 | 68.1 | 63.3 | 60.3 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 1.80 | – |
| 100K | 3.37 | 3.79 | 3.67 | 3.29 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.4% | 101.2% | 70.9% | 104.5% | – |
| 100K | 100.4% | – | – | 104.4% | – |
| 250K | – | – | – | 69.9% | 106.7% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 98.7% | 99.0% | 0.0% | 96.2% | – |
| 100K | 97.6% | – | – | 96.4% | – |
| 250K | – | – | – | 0.0% | 0.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 2.14 | 0.90 | 4.96 | 0.42 | – |
| 100K | 4.24 | – | – | 0.29 | – |
| 250K | – | – | – | 109.95 | 61.62 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | 0.00 | 0.00 | – |
| 100K | 0.00 | – | – | 0.00 | – |
| 250K | – | – | – | 1.92 | 0.01 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 49.3 | 40.9 | 34.8 | 29.8 | – |
| 100K | 47.8 | – | – | 38.0 | – |
| 250K | – | – | – | 70.5 | 67.8 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 2.18 | 1.86 | 1.28 | 1.17 | – |
| 100K | 2.13 | – | – | 1.69 | – |
| 250K | – | – | – | 4.11 | 3.87 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·udp·250K·1000ms` | 1400 | 350.00 | 69.9% | 0.0% | – | 109.95 | 1.92 | 5.9 → 76.4 | 4.11 | degraded: delivered 69.9% of what was asked (< 95%) |
| 2 | `mesh·udp·50K·250ms` | 1400 | 70.00 | 101.2% | 99.0% | – | 0.90 | 0.00 | 6.3 → 47.2 | 1.86 | ok |
| 3 | `mesh·tcp·100K·500ms` | 1400 | 140.00 | 100.4% | 84.9% | 376.7 | – | – | 3.6 → 66.9 | 3.67 | ok |
| 4 | `mesh·udp·100K·100ms` | 1400 | 140.00 | 100.4% | 97.6% | – | 4.24 | 0.00 | 3.9 → 51.7 | 2.13 | ok |
| 5 | `mesh·udp·50K·100ms` | 1400 | 70.00 | 100.4% | 98.7% | – | 2.14 | 0.00 | 3.6 → 52.9 | 2.18 | ok |
| 6 | `mesh·udp·250K·2000ms` | 1400 | 350.00 | 106.7% | 0.0% | – | 61.62 | 0.01 | 4.0 → 71.8 | 3.87 | ok |
| 7 | `mesh·udp·100K·1000ms` | 1400 | 140.00 | 104.4% | 96.4% | – | 0.29 | 0.00 | 4.2 → 42.2 | 1.69 | ok |
| 8 | `mesh·tcp·100K·250ms` | 1400 | 140.00 | 98.5% | 0.0% | 872.5 | – | – | 4.0 → 72.0 | 3.79 | ok |
| 9 | `mesh·tcp·100K·100ms` | 1400 | 140.00 | 95.7% | 0.0% | 729.5 | – | – | 4.2 → 68.7 | 3.37 | ok |
| 10 | `mesh·udp·50K·1000ms` | 1400 | 70.00 | 104.5% | 96.2% | – | 0.42 | 0.00 | 4.0 → 33.7 | 1.17 | ok |
| 11 | `mesh·tcp·50K·1000ms` | 1400 | 70.00 | 105.0% | 82.0% | 7.6 | – | – | 4.3 → 44.1 | 1.80 | ok |
| 12 | `mesh·tcp·100K·1000ms` | 1400 | 140.00 | 100.8% | 86.7% | 596.5 | – | – | 4.2 → 64.5 | 3.29 | ok |
| 13 | `mesh·udp·50K·500ms` | 1400 | 70.00 | 70.9% | 0.0% | – | 4.96 | 0.00 | 4.4 → 39.2 | 1.28 | stopped: memory stalls 23.1% > 10.0% for 3 sweeps |

Per image at 700 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 737 | 1.2 | 99.3% | – |
| `kathara/frr` | 5 | 1.3 | 0.7% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
