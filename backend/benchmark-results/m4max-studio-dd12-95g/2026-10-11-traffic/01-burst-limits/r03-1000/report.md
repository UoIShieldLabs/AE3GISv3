# Benchmark: m4max-studio-dd12-95g · burst-limits · 1000 hosts · round 3

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 20 cells on one deployment of 1000 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1990.6 of 101850.2 MB used (1.9%) · host CPU 9.8% · Docker processes 347.9 MB · Docker's disk 8.7% used
- **Outcome:** 15 of 20 cells passed (5 degraded) · 2026-10-12T20:36:57 → 2026-10-13T00:18:29

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1000 | 1 | 1057 | 1056 | 266.6 | 4.20 | 301.5 | 13.5 | 15.9 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 20 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.7% | 100.0% | 100.8% | 102.1% | 103.9% |
| 100K | – | – | – | – | 94.9% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 97.6% | 90.0% | 96.9% | 97.5% | 95.0% |
| 100K | – | – | – | – | 0.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 136.2 | 135.0 | 68.2 | 3.1 | 4.8 |
| 100K | – | – | – | – | 153.9 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0 | 21689 | 12131 | 687 | 624 |
| 100K | – | – | – | – | 73911 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 54.9 | 52.5 | 45.4 | 39.1 | 37.0 |
| 100K | – | – | – | – | 55.2 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 5.71 | 5.46 | 4.68 | 4.11 | 4.01 |
| 100K | – | – | – | – | 5.94 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.2% | 100.5% | 99.4% | 102.1% | 104.0% |
| 100K | – | 99.7% | – | 102.0% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 98.6% | 98.5% | 98.8% | 97.5% | 95.0% |
| 100K | – | 99.0% | – | 97.5% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.99 | 0.60 | 0.34 | 0.32 | 0.27 |
| 100K | – | 1.02 | – | 0.36 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 100K | – | 0.00 | – | 0.00 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 42.3 | 35.4 | 28.6 | 23.1 | 21.4 |
| 100K | – | 46.7 | – | 35.3 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.04 | 3.69 | 3.13 | 2.64 | 2.48 |
| 100K | – | 4.79 | – | 3.78 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 96.1% |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 0.0% |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 2.4 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 34 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 22.4 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 2.14 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 97.4% |
| 100K | – | – | – | – | 94.7% |
| 250K | – | – | – | – | 95.8% |
| 500K | 72.7% | – | – | 82.6% | 87.9% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 0.0% |
| 100K | – | – | – | – | 0.0% |
| 250K | – | – | – | – | 0.0% |
| 500K | 0.0% | – | – | 0.0% | 0.0% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 0.18 |
| 100K | – | – | – | – | 0.17 |
| 250K | – | – | – | – | 0.17 |
| 500K | 33.53 | – | – | 4.20 | 4.04 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 0.00 |
| 100K | – | – | – | – | 0.00 |
| 250K | – | – | – | – | 0.00 |
| 500K | 0.00 | – | – | 0.00 | 0.01 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 19.0 |
| 100K | – | – | – | – | 21.3 |
| 250K | – | – | – | – | 29.6 |
| 500K | 42.5 | – | – | 37.4 | 35.9 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | 1.80 |
| 100K | – | – | – | – | 2.06 |
| 250K | – | – | – | – | 2.92 |
| 500K | 4.25 | – | – | 3.87 | 3.74 |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·udp·50K·100ms` | 1000 | 50.00 | 100.2% | 98.6% | – | 0.99 | 0.00 | 8.7 → 51.0 | 4.04 | ok |
| 2 | `mesh·udp·100K·2000ms` | 2000 | 200.00 | 94.7% | 0.0% | – | 0.17 | 0.00 | 9.3 → 30.6 | 2.06 | degraded: delivered 94.7% of what was asked (< 95%) |
| 3 | `cs·tcp·50K·250ms` | 1000 | 50.00 | 100.0% | 90.0% | 135.0 | – | – | 9.0 → 61.4 | 5.46 | ok |
| 4 | `mesh·udp·500K·1000ms` | 2000 | 1000.00 | 82.6% | 0.0% | – | 4.20 | 0.00 | 9.2 → 46.6 | 3.87 | degraded: delivered 82.6% of what was asked (< 95%) |
| 5 | `mesh·udp·500K·2000ms` | 2000 | 1000.00 | 87.9% | 0.0% | – | 4.04 | 0.01 | 9.3 → 45.2 | 3.74 | degraded: delivered 87.9% of what was asked (< 95%) |
| 6 | `cs·udp·50K·250ms` | 1000 | 50.00 | 100.5% | 98.5% | – | 0.60 | 0.00 | 9.1 → 44.5 | 3.69 | ok |
| 7 | `mesh·udp·250K·2000ms` | 2000 | 500.00 | 95.8% | 0.0% | – | 0.17 | 0.00 | 9.5 → 39.2 | 2.92 | ok |
| 8 | `cs·udp·100K·250ms` | 1000 | 100.00 | 99.7% | 99.0% | – | 1.02 | 0.00 | 8.7 → 55.4 | 4.79 | ok |
| 9 | `cs·udp·50K·2000ms` | 1000 | 50.00 | 104.0% | 95.0% | – | 0.27 | 0.00 | 8.8 → 30.1 | 2.48 | ok |
| 10 | `cs·tcp·100K·2000ms` | 1000 | 100.00 | 94.9% | 0.0% | 153.9 | – | – | 8.8 → 64.0 | 5.94 | degraded: delivered 94.9% of what was asked (< 95%) |
| 11 | `cs·tcp·50K·1000ms` | 1000 | 50.00 | 102.1% | 97.5% | 3.1 | – | – | 8.8 → 48.0 | 4.11 | ok |
| 12 | `cs·udp·100K·1000ms` | 1000 | 100.00 | 102.0% | 97.5% | – | 0.36 | 0.00 | 8.6 → 44.0 | 3.78 | ok |
| 13 | `mesh·tcp·50K·2000ms` | 2000 | 100.00 | 96.1% | 0.0% | 2.4 | – | – | 8.9 → 31.3 | 2.14 | ok |
| 14 | `cs·udp·50K·500ms` | 1000 | 50.00 | 99.4% | 98.8% | – | 0.34 | 0.00 | 8.8 → 37.5 | 3.13 | ok |
| 15 | `mesh·udp·500K·100ms` | 2000 | 1000.00 | 72.7% | 0.0% | – | 33.53 | 0.00 | 8.7 → 51.2 | 4.25 | degraded: delivered 72.7% of what was asked (< 95%) |
| 16 | `cs·tcp·50K·2000ms` | 1000 | 50.00 | 103.9% | 95.0% | 4.8 | – | – | 8.9 → 45.9 | 4.01 | ok |
| 17 | `cs·tcp·50K·500ms` | 1000 | 50.00 | 100.8% | 96.9% | 68.2 | – | – | 8.7 → 54.2 | 4.68 | ok |
| 18 | `cs·tcp·50K·100ms` | 1000 | 50.00 | 99.7% | 97.6% | 136.2 | – | – | 8.8 → 63.7 | 5.71 | ok |
| 19 | `cs·udp·50K·1000ms` | 1000 | 50.00 | 102.1% | 97.5% | – | 0.32 | 0.00 | 8.7 → 31.8 | 2.64 | ok |
| 20 | `mesh·udp·50K·2000ms` | 2000 | 100.00 | 97.4% | 0.0% | – | 0.18 | 0.00 | 9.0 → 27.9 | 1.80 | ok |

Per image at 1000 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 1051 | 1.2 | 99.4% | – |
| `kathara/frr` | 6 | 1.3 | 0.6% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
