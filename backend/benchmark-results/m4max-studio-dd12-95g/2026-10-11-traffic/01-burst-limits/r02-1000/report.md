# Benchmark: m4max-studio-dd12-95g · burst-limits · 1000 hosts · round 2

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 42 cells on one deployment of 1000 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 2008.4 of 101850.2 MB used (2.0%) · host CPU 9.8% · Docker processes 340.6 MB · Docker's disk 8.6% used
- **Outcome:** 17 of 42 cells passed (22 degraded, 3 failed) · 2026-10-12T01:51:40 → 2026-10-12T11:42:41

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1000 | 1 | 1057 | 1056 | 265.1 | 4.07 | 288.1 | 13.7 | 16.0 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 42 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.8% | 100.1% | 100.7% | 102.0% | 104.0% |
| 100K | 92.6% | 91.4% | 93.7% | 94.6% | 95.3% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 98.0% | 90.0% | 96.8% | 97.3% | 95.0% |
| 100K | 14.7% | 3.8% | 0.0% | 15.0% | 20.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 138.2 | 127.5 | 9.9 | 3.4 | 3.7 |
| 100K | 155.3 | 152.9 | 149.6 | 149.6 | 154.3 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0 | 23923 | 9886 | 1630 | 147 |
| 100K | 76243 | 90744 | 84528 | 78810 | 73378 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 56.9 | 48.6 | 46.6 | 40.6 | 34.4 |
| 100K | 55.4 | 57.5 | 57.3 | 57.2 | 55.6 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 5.87 | 5.09 | 4.85 | 4.30 | 3.72 |
| 100K | 5.84 | 6.18 | 6.11 | 6.12 | 5.97 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.2% | 100.5% | 99.5% | 102.2% | 103.9% |
| 100K | 100.0% | 99.8% | – | 102.1% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.2% | 98.5% | 98.8% | 97.5% | 95.0% |
| 100K | 100.0% | 98.0% | – | 97.5% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 1.50 | 0.28 | 0.36 | 0.32 | 0.27 |
| 100K | 1.22 | 0.56 | – | 0.35 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.04 | 0.00 | 0.00 | 0.00 | 0.00 |
| 100K | 0.00 | 0.00 | – | 0.00 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 44.3 | 37.0 | 27.5 | 25.3 | 23.3 |
| 100K | 43.8 | 46.0 | – | 34.3 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.32 | 3.63 | 2.99 | 2.85 | 2.74 |
| 100K | 4.20 | 4.51 | – | 3.65 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 79.5% | 85.4% | 88.1% | 96.7% |
| 100K | 76.7% | 80.2% | 81.2% | 87.1% | 0.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.0% | 0.0% | 0.0% | 0.0% |
| 100K | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 1.9 | 1.0 | 1.2 | 2.3 |
| 100K | 10.2 | 1.4 | 2.4 | 3.0 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 471 | 48 | 55 | 22 |
| 100K | 0 | 582 | 314 | 101 | 0 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 27.7 | 22.3 | 20.4 | 22.3 |
| 100K | 31.0 | 28.7 | 29.2 | 26.3 | -0.4 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 2.56 | 2.09 | 1.96 | 2.08 |
| 100K | 2.83 | 2.74 | 2.75 | 2.56 | 0.97 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 78.3% | 82.4% | 87.2% | 88.5% | 100.0% |
| 100K | 78.0% | 77.5% | 85.5% | 87.9% | 100.0% |
| 250K | 0.0% | 82.0% | 82.2% | 88.8% | 96.1% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.0% | 0.0% | 0.0% | 0.0% | 99.9% |
| 100K | 0.0% | 0.0% | 0.0% | 0.0% | 99.8% |
| 250K | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.39 | 0.24 | 0.18 | 0.22 | 0.12 |
| 100K | 0.37 | 0.28 | 0.22 | 0.20 | 0.12 |
| 250K | – | 0.33 | 0.29 | 0.21 | 0.16 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 100K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 250K | – | 0.00 | 0.00 | 0.00 | 0.00 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 25.0 | 20.0 | 17.0 | 19.9 | 16.6 |
| 100K | 25.3 | 23.7 | 21.8 | 22.2 | 19.9 |
| 250K | 0.3 | 28.8 | 30.5 | 27.2 | 27.9 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 2.17 | 1.83 | 1.53 | 1.84 | 1.59 |
| 100K | 2.21 | 2.18 | 1.99 | 2.09 | 1.87 |
| 250K | 1.01 | 2.70 | 2.74 | 2.65 | 2.71 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·udp·100K·1000ms` | 1000 | 100.00 | 102.1% | 97.5% | – | 0.35 | 0.00 | 8.7 → 43.0 | 3.65 | ok |
| 2 | `mesh·udp·100K·250ms` | 2000 | 200.00 | 77.5% | 0.0% | – | 0.28 | 0.00 | 9.2 → 32.9 | 2.18 | degraded: delivered 77.5% of what was asked (< 95%) |
| 3 | `mesh·udp·50K·2000ms` | 2000 | 100.00 | 100.0% | 99.9% | – | 0.12 | 0.00 | 9.2 → 25.9 | 1.59 | ok |
| 4 | `mesh·udp·250K·250ms` | 2000 | 500.00 | 82.0% | 0.0% | – | 0.33 | 0.00 | 8.9 → 37.8 | 2.70 | degraded: delivered 82.0% of what was asked (< 95%) |
| 5 | `mesh·udp·50K·250ms` | 2000 | 100.00 | 82.4% | 0.0% | – | 0.24 | 0.00 | 9.2 → 29.3 | 1.83 | degraded: delivered 82.4% of what was asked (< 95%) |
| 6 | `mesh·udp·100K·2000ms` | 2000 | 200.00 | 100.0% | 99.8% | – | 0.12 | 0.00 | 9.1 → 29.1 | 1.87 | ok |
| 7 | `mesh·tcp·50K·500ms` | 2000 | 100.00 | 85.4% | 0.0% | 1.0 | – | – | 9.1 → 31.4 | 2.09 | degraded: delivered 85.4% of what was asked (< 95%) |
| 8 | `cs·udp·50K·2000ms` | 1000 | 50.00 | 103.9% | 95.0% | – | 0.27 | 0.00 | 9.3 → 32.5 | 2.74 | ok |
| 9 | `cs·udp·100K·100ms` | 1000 | 100.00 | 100.0% | 100.0% | – | 1.22 | 0.00 | 8.9 → 52.7 | 4.20 | failed: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| 10 | `cs·udp·100K·250ms` | 1000 | 100.00 | 99.8% | 98.0% | – | 0.56 | 0.00 | 7.1 → 53.1 | 4.51 | ok |
| 11 | `mesh·udp·250K·500ms` | 2000 | 500.00 | 82.2% | 0.0% | – | 0.29 | 0.00 | 7.3 → 37.8 | 2.74 | degraded: delivered 82.2% of what was asked (< 95%) |
| 12 | `cs·udp·50K·250ms` | 1000 | 50.00 | 100.5% | 98.5% | – | 0.28 | 0.00 | 7.2 → 44.1 | 3.63 | ok |
| 13 | `mesh·tcp·100K·500ms` | 2000 | 200.00 | 81.2% | 0.0% | 2.4 | – | – | 8.7 → 37.9 | 2.75 | degraded: delivered 81.2% of what was asked (< 95%) |
| 14 | `mesh·tcp·100K·250ms` | 2000 | 200.00 | 80.2% | 0.0% | 1.4 | – | – | 9.2 → 37.9 | 2.74 | degraded: delivered 80.2% of what was asked (< 95%) |
| 15 | `mesh·udp·250K·2000ms` | 2000 | 500.00 | 96.1% | 0.0% | – | 0.16 | 0.00 | 9.3 → 37.1 | 2.71 | ok |
| 16 | `cs·tcp·100K·250ms` | 1000 | 100.00 | 91.4% | 3.8% | 152.9 | – | – | 9.4 → 66.9 | 6.18 | degraded: delivered 91.4% of what was asked (< 95%) |
| 17 | `cs·tcp·50K·2000ms` | 1000 | 50.00 | 104.0% | 95.0% | 3.7 | – | – | 9.1 → 43.5 | 3.72 | ok |
| 18 | `cs·tcp·50K·250ms` | 1000 | 50.00 | 100.1% | 90.0% | 127.5 | – | – | 9.6 → 58.2 | 5.09 | ok |
| 19 | `mesh·tcp·100K·1000ms` | 2000 | 200.00 | 87.1% | 0.0% | 3.0 | – | – | 9.5 → 35.8 | 2.56 | degraded: delivered 87.1% of what was asked (< 95%) |
| 20 | `mesh·tcp·50K·1000ms` | 2000 | 100.00 | 88.1% | 0.0% | 1.2 | – | – | 9.3 → 29.7 | 1.96 | degraded: delivered 88.1% of what was asked (< 95%) |
| 21 | `mesh·udp·250K·1000ms` | 2000 | 500.00 | 88.8% | 0.0% | – | 0.21 | 0.00 | 9.5 → 36.8 | 2.65 | degraded: delivered 88.8% of what was asked (< 95%) |
| 22 | `mesh·udp·250K·100ms` | 2000 | 500.00 | 0.0% | 0.0% | – | – | – | 9.2 → 9.5 | 1.01 | failed: RuntimeError: Not running: h3-192, h3-193, h3-195, h3-196, h3-197, h3-198, h3-199, h3-200 |
| 23 | `cs·udp·50K·100ms` | 1000 | 50.00 | 100.2% | 99.2% | – | 1.50 | 0.04 | 9.2 → 53.5 | 4.32 | ok |
| 24 | `mesh·tcp·100K·2000ms` | 2000 | 200.00 | 0.0% | 0.0% | – | – | – | 9.4 → 9.0 | 0.97 | failed: RuntimeError: Not running: h4-134, h4-138, h4-139, h4-152 |
| 25 | `mesh·tcp·100K·100ms` | 2000 | 200.00 | 76.7% | 0.0% | 10.2 | – | – | 8.9 → 39.9 | 2.83 | degraded: delivered 76.7% of what was asked (< 95%) |
| 26 | `cs·tcp·50K·1000ms` | 1000 | 50.00 | 102.0% | 97.3% | 3.4 | – | – | 9.0 → 49.7 | 4.30 | ok |
| 27 | `cs·udp·50K·500ms` | 1000 | 50.00 | 99.5% | 98.8% | – | 0.36 | 0.00 | 8.6 → 36.2 | 2.99 | ok |
| 28 | `mesh·udp·50K·100ms` | 2000 | 100.00 | 78.3% | 0.0% | – | 0.39 | 0.00 | 8.9 → 33.8 | 2.17 | degraded: delivered 78.3% of what was asked (< 95%) |
| 29 | `cs·tcp·100K·1000ms` | 1000 | 100.00 | 94.6% | 15.0% | 149.6 | – | – | 8.7 → 65.9 | 6.12 | degraded: delivered 94.6% of what was asked (< 95%) |
| 30 | `mesh·udp·50K·1000ms` | 2000 | 100.00 | 88.5% | 0.0% | – | 0.22 | 0.00 | 8.7 → 28.6 | 1.84 | degraded: delivered 88.5% of what was asked (< 95%) |
| 31 | `cs·tcp·100K·500ms` | 1000 | 100.00 | 93.7% | 0.0% | 149.6 | – | – | 8.7 → 66.0 | 6.11 | degraded: delivered 93.7% of what was asked (< 95%) |
| 32 | `mesh·tcp·50K·2000ms` | 2000 | 100.00 | 96.7% | 0.0% | 2.3 | – | – | 8.6 → 30.9 | 2.08 | ok |
| 33 | `cs·udp·50K·1000ms` | 1000 | 50.00 | 102.2% | 97.5% | – | 0.32 | 0.00 | 8.8 → 34.1 | 2.85 | ok |
| 34 | `mesh·udp·100K·100ms` | 2000 | 200.00 | 78.0% | 0.0% | – | 0.37 | 0.00 | 9.0 → 34.2 | 2.21 | degraded: delivered 78.0% of what was asked (< 95%) |
| 35 | `mesh·udp·100K·500ms` | 2000 | 200.00 | 85.5% | 0.0% | – | 0.22 | 0.00 | 8.8 → 30.6 | 1.99 | degraded: delivered 85.5% of what was asked (< 95%) |
| 36 | `cs·tcp·50K·500ms` | 1000 | 50.00 | 100.7% | 96.8% | 9.9 | – | – | 8.8 → 55.4 | 4.85 | ok |
| 37 | `cs·tcp·100K·2000ms` | 1000 | 100.00 | 95.3% | 20.0% | 154.3 | – | – | 9.1 → 64.7 | 5.97 | ok |
| 38 | `cs·tcp·100K·100ms` | 1000 | 100.00 | 92.6% | 14.7% | 155.3 | – | – | 8.8 → 64.1 | 5.84 | degraded: delivered 92.6% of what was asked (< 95%) |
| 39 | `mesh·udp·100K·1000ms` | 2000 | 200.00 | 87.9% | 0.0% | – | 0.20 | 0.00 | 9.0 → 31.1 | 2.09 | degraded: delivered 87.9% of what was asked (< 95%) |
| 40 | `cs·tcp·50K·100ms` | 1000 | 50.00 | 99.8% | 98.0% | 138.2 | – | – | 8.4 → 65.2 | 5.87 | ok |
| 41 | `mesh·tcp·50K·250ms` | 2000 | 100.00 | 79.5% | 0.0% | 1.9 | – | – | 8.8 → 36.4 | 2.56 | degraded: delivered 79.5% of what was asked (< 95%) |
| 42 | `mesh·udp·50K·500ms` | 2000 | 100.00 | 87.2% | 0.0% | – | 0.18 | 0.00 | 9.1 → 26.1 | 1.53 | degraded: delivered 87.2% of what was asked (< 95%) |

Per image at 1000 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 1051 | 1.2 | 99.4% | – |
| `kathara/frr` | 6 | 1.3 | 0.6% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
