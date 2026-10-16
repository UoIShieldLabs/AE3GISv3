# Benchmark: m4max-studio-dd12-95g · burst-limits · 800 hosts · round 1

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 45 cells on one deployment of 800 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1970.0 of 101850.2 MB used (1.9%) · host CPU 9.8% · Docker processes 336.9 MB · Docker's disk 8.6% used
- **Outcome:** 42 of 45 cells passed (3 failed) · 2026-10-11T17:51:25 → 2026-10-11T21:00:23

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 800 | 1 | 846 | 845 | 172.0 | 3.32 | 190.6 | 13.2 | 15.9 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 45 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.8% | 100.2% | 100.8% | 101.6% | 103.9% |
| 100K | 99.9% | 99.2% | 99.9% | 101.3% | 102.4% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 97.2% | 96.8% | 97.0% | 96.0% | 96.0% |
| 100K | 97.8% | 77.0% | 94.0% | 97.5% | 95.8% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 86.4 | 72.2 | 2.8 | 2.7 | 2.9 |
| 100K | 98.5 | 140.8 | 128.7 | 58.6 | 6.8 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0 | 21569 | 2654 | 990 | 69 |
| 100K | 4315 | 57861 | 20555 | 8343 | 1 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 59.7 | 48.7 | 41.5 | 35.4 | 30.6 |
| 100K | 58.4 | 60.4 | 56.0 | 53.0 | 51.6 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 5.92 | 4.88 | 4.23 | 3.71 | 3.30 |
| 100K | 5.86 | 6.21 | 5.78 | 5.52 | 5.34 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.2% | 100.4% | 100.0% | 101.8% | 103.3% |
| 100K | 100.2% | 100.0% | 0.0% | 101.8% | 0.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.0% | 99.5% | 99.7% | 97.9% | 96.0% |
| 100K | 99.0% | 99.4% | 0.0% | 98.0% | 0.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.72 | 0.36 | 0.29 | 0.27 | 0.27 |
| 100K | 1.03 | 0.66 | – | 0.31 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 100K | 0.00 | 0.00 | – | 0.00 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 39.9 | 31.3 | 23.5 | 22.0 | 19.0 |
| 100K | 41.0 | 41.8 | -0.1 | 30.6 | -0.0 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 3.87 | 3.24 | 2.56 | 2.45 | 2.20 |
| 100K | 3.91 | 4.21 | 0.75 | 3.25 | 0.75 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.0% | 101.0% | 102.0% | 104.3% | 108.2% |
| 100K | 100.4% | 101.1% | 102.2% | 104.4% | 108.9% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.0% | 99.1% | 98.3% | 96.4% | 93.0% |
| 100K | 98.6% | 98.5% | 97.8% | 96.2% | 93.2% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.7 | 0.7 | 1.0 | 1.4 |
| 100K | 3.0 | 1.2 | 1.3 | 1.8 | 2.0 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0 | 497 | 83 | 41 | 18 |
| 100K | 0 | 3528 | 225 | 89 | 23 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.2 | 33.3 | 24.7 | 25.2 | 20.0 |
| 100K | 37.0 | 40.3 | 35.5 | 33.2 | 32.5 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.76 | 3.04 | 2.26 | 2.40 | 1.90 |
| 100K | 3.16 | 3.77 | 3.38 | 3.17 | 3.15 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.4% | 101.0% | 101.0% | 104.6% | 107.5% |
| 100K | 100.4% | 100.7% | 102.1% | 104.0% | 107.9% |
| 250K | 100.3% | 101.0% | 102.2% | 103.9% | 108.3% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.4% | 99.1% | 97.8% | 96.3% | 93.2% |
| 100K | 99.2% | 98.9% | 98.0% | 96.4% | 93.2% |
| 250K | 96.9% | 98.9% | 97.9% | 96.4% | 93.2% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.20 | 0.12 | 0.13 | 0.15 | 0.13 |
| 100K | 0.16 | 0.16 | 0.15 | 0.13 | 0.12 |
| 250K | 1.03 | 0.22 | 0.20 | 0.15 | 0.10 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 100K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 250K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 28.4 | 21.9 | 18.1 | 20.1 | 15.5 |
| 100K | 27.6 | 29.4 | 23.7 | 20.7 | 20.6 |
| 250K | 45.9 | 36.6 | 39.0 | 34.4 | 33.7 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 2.32 | 1.89 | 1.62 | 1.83 | 1.45 |
| 100K | 2.17 | 2.62 | 2.16 | 1.93 | 1.91 |
| 250K | 4.25 | 3.37 | 3.72 | 3.24 | 3.21 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·50K·100ms` | 1600 | 80.00 | 0.0% | 0.0% | – | – | – | 7.0 → 7.2 | 0.76 | failed: RuntimeError: Not running: h1-19 |
| 2 | `mesh·udp·50K·1000ms` | 1600 | 80.00 | 104.6% | 96.3% | – | 0.15 | 0.00 | 7.0 → 27.1 | 1.83 | ok |
| 3 | `mesh·tcp·100K·100ms` | 1600 | 160.00 | 100.4% | 98.6% | 3.0 | – | – | 7.5 → 44.4 | 3.16 | ok |
| 4 | `mesh·udp·100K·500ms` | 1600 | 160.00 | 102.1% | 98.0% | – | 0.15 | 0.00 | 7.3 → 31.0 | 2.16 | ok |
| 5 | `mesh·udp·250K·2000ms` | 1600 | 400.00 | 108.3% | 93.2% | – | 0.10 | 0.00 | 7.2 → 41.0 | 3.21 | ok |
| 6 | `mesh·udp·100K·1000ms` | 1600 | 160.00 | 104.0% | 96.4% | – | 0.13 | 0.00 | 7.4 → 28.1 | 1.93 | ok |
| 7 | `cs·udp·100K·2000ms` | 800 | 80.00 | 0.0% | 0.0% | – | – | – | 7.1 → 7.0 | 0.75 | failed: RuntimeError: Not running: h3-117, h3-118, h3-121 |
| 8 | `mesh·udp·50K·100ms` | 1600 | 80.00 | 100.4% | 99.4% | – | 0.20 | 0.00 | 7.4 → 35.9 | 2.32 | ok |
| 9 | `cs·udp·100K·250ms` | 800 | 80.00 | 100.0% | 99.4% | – | 0.66 | 0.00 | 7.3 → 49.0 | 4.21 | ok |
| 10 | `cs·udp·100K·500ms` | 800 | 80.00 | 0.0% | 0.0% | – | – | – | 7.3 → 7.2 | 0.75 | failed: RuntimeError: Not running: h2-22, h2-23, h2-25, h2-26, h2-27, h2-28, h2-29, h2-30, h2-31, h2-32 |
| 11 | `mesh·udp·250K·500ms` | 1600 | 400.00 | 102.2% | 97.9% | – | 0.20 | 0.00 | 7.3 → 46.3 | 3.72 | ok |
| 12 | `mesh·udp·50K·250ms` | 1600 | 80.00 | 101.0% | 99.1% | – | 0.12 | 0.00 | 7.2 → 29.1 | 1.89 | ok |
| 13 | `cs·udp·50K·250ms` | 800 | 40.00 | 100.4% | 99.5% | – | 0.36 | 0.00 | 7.3 → 38.6 | 3.24 | ok |
| 14 | `mesh·tcp·50K·1000ms` | 1600 | 80.00 | 104.3% | 96.4% | 1.0 | – | – | 7.5 → 32.7 | 2.40 | ok |
| 15 | `mesh·tcp·50K·2000ms` | 1600 | 80.00 | 108.2% | 93.0% | 1.4 | – | – | 7.4 → 27.5 | 1.90 | ok |
| 16 | `cs·udp·100K·100ms` | 800 | 80.00 | 100.2% | 99.0% | – | 1.03 | 0.00 | 7.3 → 48.3 | 3.91 | ok |
| 17 | `cs·tcp·100K·250ms` | 800 | 80.00 | 99.2% | 77.0% | 140.8 | – | – | 7.2 → 67.6 | 6.21 | ok |
| 18 | `cs·tcp·50K·2000ms` | 800 | 40.00 | 103.9% | 96.0% | 2.9 | – | – | 7.6 → 38.2 | 3.30 | ok |
| 19 | `cs·tcp·50K·250ms` | 800 | 40.00 | 100.2% | 96.8% | 72.2 | – | – | 7.3 → 56.0 | 4.88 | ok |
| 20 | `mesh·tcp·100K·250ms` | 1600 | 160.00 | 101.1% | 98.5% | 1.2 | – | – | 7.3 → 47.6 | 3.77 | ok |
| 21 | `mesh·udp·250K·250ms` | 1600 | 400.00 | 101.0% | 98.9% | – | 0.22 | 0.00 | 7.2 → 43.8 | 3.37 | ok |
| 22 | `mesh·udp·250K·1000ms` | 1600 | 400.00 | 103.9% | 96.4% | – | 0.15 | 0.00 | 7.2 → 41.5 | 3.24 | ok |
| 23 | `mesh·udp·100K·2000ms` | 1600 | 160.00 | 107.9% | 93.2% | – | 0.12 | 0.00 | 7.2 → 27.8 | 1.91 | ok |
| 24 | `cs·udp·50K·100ms` | 800 | 40.00 | 100.2% | 99.0% | – | 0.72 | 0.00 | 7.3 → 47.1 | 3.87 | ok |
| 25 | `mesh·tcp·100K·1000ms` | 1600 | 160.00 | 104.4% | 96.2% | 1.8 | – | – | 7.4 → 40.6 | 3.17 | ok |
| 26 | `mesh·tcp·50K·500ms` | 1600 | 80.00 | 102.0% | 98.3% | 0.7 | – | – | 7.3 → 32.0 | 2.26 | ok |
| 27 | `cs·tcp·50K·1000ms` | 800 | 40.00 | 101.6% | 96.0% | 2.7 | – | – | 7.3 → 42.8 | 3.71 | ok |
| 28 | `cs·udp·50K·500ms` | 800 | 40.00 | 100.0% | 99.7% | – | 0.29 | 0.00 | 7.2 → 30.6 | 2.56 | ok |
| 29 | `mesh·tcp·100K·500ms` | 1600 | 160.00 | 102.2% | 97.8% | 1.3 | – | – | 7.4 → 42.9 | 3.38 | ok |
| 30 | `cs·tcp·100K·1000ms` | 800 | 80.00 | 101.3% | 97.5% | 58.6 | – | – | 7.4 → 60.4 | 5.52 | ok |
| 31 | `cs·tcp·100K·500ms` | 800 | 80.00 | 99.9% | 94.0% | 128.7 | – | – | 7.4 → 63.4 | 5.78 | ok |
| 32 | `cs·udp·50K·2000ms` | 800 | 40.00 | 103.3% | 96.0% | – | 0.27 | 0.00 | 7.2 → 26.2 | 2.20 | ok |
| 33 | `mesh·tcp·50K·250ms` | 1600 | 80.00 | 101.0% | 99.1% | 0.7 | – | – | 7.2 → 40.5 | 3.04 | ok |
| 34 | `cs·udp·50K·1000ms` | 800 | 40.00 | 101.8% | 97.9% | – | 0.27 | 0.00 | 7.2 → 29.2 | 2.45 | ok |
| 35 | `mesh·udp·100K·250ms` | 1600 | 160.00 | 100.7% | 98.9% | – | 0.16 | 0.00 | 7.3 → 36.7 | 2.62 | ok |
| 36 | `mesh·udp·50K·500ms` | 1600 | 80.00 | 101.0% | 97.8% | – | 0.13 | 0.00 | 7.3 → 25.3 | 1.62 | ok |
| 37 | `mesh·udp·50K·2000ms` | 1600 | 80.00 | 107.5% | 93.2% | – | 0.13 | 0.00 | 7.2 → 22.7 | 1.45 | ok |
| 38 | `cs·tcp·50K·500ms` | 800 | 40.00 | 100.8% | 97.0% | 2.8 | – | – | 7.1 → 48.6 | 4.23 | ok |
| 39 | `cs·tcp·100K·2000ms` | 800 | 80.00 | 102.4% | 95.8% | 6.8 | – | – | 7.3 → 59.0 | 5.34 | ok |
| 40 | `cs·tcp·100K·100ms` | 800 | 80.00 | 99.9% | 97.8% | 98.5 | – | – | 7.3 → 65.7 | 5.86 | ok |
| 41 | `mesh·udp·250K·100ms` | 1600 | 400.00 | 100.3% | 96.9% | – | 1.03 | 0.00 | 7.0 → 52.8 | 4.25 | ok |
| 42 | `mesh·udp·100K·100ms` | 1600 | 160.00 | 100.4% | 99.2% | – | 0.16 | 0.00 | 7.3 → 34.9 | 2.17 | ok |
| 43 | `cs·tcp·50K·100ms` | 800 | 40.00 | 99.8% | 97.2% | 86.4 | – | – | 7.4 → 67.1 | 5.92 | ok |
| 44 | `cs·udp·100K·1000ms` | 800 | 80.00 | 101.8% | 98.0% | – | 0.31 | 0.00 | 7.2 → 37.8 | 3.25 | ok |
| 45 | `mesh·tcp·100K·2000ms` | 1600 | 160.00 | 108.9% | 93.2% | 2.0 | – | – | 7.6 → 40.1 | 3.15 | ok |

Per image at 800 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 841 | 1.2 | 99.4% | – |
| `kathara/frr` | 5 | 1.3 | 0.6% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
