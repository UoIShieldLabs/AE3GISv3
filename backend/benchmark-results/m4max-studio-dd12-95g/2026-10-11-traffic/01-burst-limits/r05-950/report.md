# Benchmark: m4max-studio-dd12-95g · burst-limits · 950 hosts · round 5

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 20 cells on one deployment of 950 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 2016.2 of 101850.2 MB used (2.0%) · host CPU 9.8% · Docker processes 340.6 MB · Docker's disk 8.8% used
- **Outcome:** 15 of 20 cells passed (5 degraded) · 2026-10-13T19:36:09 → 2026-10-13T23:22:39

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 950 | 1 | 1005 | 1004 | 243.2 | 3.82 | 280.0 | 13.5 | 15.9 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 20 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 96.0% | – | 95.6% | 98.9% | 99.5% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 41.8% | – | 6.2% | 47.5% | 80.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 152.0 | – | 145.1 | 149.6 | 147.0 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 72396 | – | 81352 | 61906 | 56841 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 57.1 | – | 55.0 | 57.2 | 57.6 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 6.06 | – | 5.86 | 6.07 | 6.17 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 100.2% | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 99.0% | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 1.14 | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 0.00 | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 44.2 | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 4.29 | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 101.3% | – |
| 100K | – | – | – | 95.1% | 109.9% |
| 250K | 85.5% | – | 87.7% | 92.7% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 0.0% | – |
| 100K | – | – | – | 0.0% | 0.0% |
| 250K | 0.0% | – | 0.0% | 0.0% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 1.3 | – |
| 100K | – | – | – | 2.5 | 2.7 |
| 250K | 738.7 | – | 460.7 | 205.2 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 54 | – |
| 100K | – | – | – | 45 | 43 |
| 250K | 9209 | – | 2066 | 941 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 22.5 | – |
| 100K | – | – | – | 29.4 | 28.1 |
| 250K | 44.6 | – | 42.7 | 39.3 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 2.07 | – |
| 100K | – | – | – | 2.77 | 2.67 |
| 250K | 4.40 | – | 4.37 | 4.00 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | 97.9% | 101.1% | – |
| 100K | – | – | 99.3% | 103.1% | 109.6% |
| 250K | – | – | 94.7% | 101.6% | – |
| 500K | – | – | – | 92.3% | 96.9% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | 0.0% | 0.0% | – |
| 100K | – | – | 0.0% | 0.0% | 0.0% |
| 250K | – | – | 0.0% | 0.0% | – |
| 500K | – | – | – | 0.0% | 0.0% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | 0.18 | 0.20 | – |
| 100K | – | – | 0.17 | 0.18 | 0.15 |
| 250K | – | – | 0.32 | 0.25 | – |
| 500K | – | – | – | 7.97 | 6.85 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | 0.00 | 0.00 | – |
| 100K | – | – | 0.00 | 0.00 | 0.00 |
| 250K | – | – | 0.00 | 0.00 | – |
| 500K | – | – | – | 0.00 | 0.03 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | 19.9 | 20.7 | – |
| 100K | – | – | 21.4 | 20.6 | 22.1 |
| 250K | – | – | 29.0 | 29.7 | – |
| 500K | – | – | – | 39.8 | 41.6 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | 1.84 | 1.90 | – |
| 100K | – | – | 1.86 | 1.87 | 2.03 |
| 250K | – | – | 2.80 | 2.77 | – |
| 500K | – | – | – | 4.15 | 4.32 |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·100K·1000ms` | 1900 | 190.00 | 95.1% | 0.0% | 2.5 | – | – | 8.4 → 37.9 | 2.77 | ok |
| 2 | `mesh·udp·100K·2000ms` | 1900 | 190.00 | 109.6% | 0.0% | – | 0.15 | 0.00 | 8.8 → 30.9 | 2.03 | ok |
| 3 | `cs·tcp·100K·500ms` | 950 | 95.00 | 95.6% | 6.2% | 145.1 | – | – | 8.9 → 63.9 | 5.86 | ok |
| 4 | `mesh·udp·500K·1000ms` | 1900 | 950.00 | 92.3% | 0.0% | – | 7.97 | 0.00 | 9.0 → 48.8 | 4.15 | degraded: delivered 92.3% of what was asked (< 95%) |
| 5 | `mesh·udp·500K·2000ms` | 1900 | 950.00 | 96.9% | 0.0% | – | 6.85 | 0.03 | 8.6 → 50.2 | 4.32 | ok |
| 6 | `mesh·tcp·100K·2000ms` | 1900 | 190.00 | 109.9% | 0.0% | 2.7 | – | – | 8.8 → 36.9 | 2.67 | ok |
| 7 | `mesh·udp·250K·500ms` | 1900 | 475.00 | 94.7% | 0.0% | – | 0.32 | 0.00 | 8.9 → 38.0 | 2.80 | degraded: delivered 94.7% of what was asked (< 95%) |
| 8 | `mesh·udp·50K·500ms` | 1900 | 95.00 | 97.9% | 0.0% | – | 0.18 | 0.00 | 9.0 → 28.8 | 1.84 | ok |
| 9 | `mesh·tcp·250K·1000ms` | 1900 | 475.00 | 92.7% | 0.0% | 205.2 | – | – | 8.6 → 47.9 | 4.00 | degraded: delivered 92.7% of what was asked (< 95%) |
| 10 | `mesh·tcp·50K·1000ms` | 1900 | 95.00 | 101.3% | 0.0% | 1.3 | – | – | 8.7 → 31.2 | 2.07 | ok |
| 11 | `cs·tcp·100K·2000ms` | 950 | 95.00 | 99.5% | 80.0% | 147.0 | – | – | 8.6 → 66.2 | 6.17 | ok |
| 12 | `mesh·udp·50K·1000ms` | 1900 | 95.00 | 101.1% | 0.0% | – | 0.20 | 0.00 | 8.8 → 29.5 | 1.90 | ok |
| 13 | `mesh·udp·100K·500ms` | 1900 | 190.00 | 99.3% | 0.0% | – | 0.17 | 0.00 | 8.5 → 29.9 | 1.86 | ok |
| 14 | `mesh·tcp·250K·100ms` | 1900 | 475.00 | 85.5% | 0.0% | 738.7 | – | – | 8.7 → 53.2 | 4.40 | degraded: delivered 85.5% of what was asked (< 95%) |
| 15 | `mesh·udp·250K·1000ms` | 1900 | 475.00 | 101.6% | 0.0% | – | 0.25 | 0.00 | 8.5 → 38.2 | 2.77 | ok |
| 16 | `cs·udp·100K·100ms` | 950 | 95.00 | 100.2% | 99.0% | – | 1.14 | 0.00 | 8.4 → 52.6 | 4.29 | ok |
| 17 | `cs·tcp·100K·1000ms` | 950 | 95.00 | 98.9% | 47.5% | 149.6 | – | – | 8.7 → 65.9 | 6.07 | ok |
| 18 | `cs·tcp·100K·100ms` | 950 | 95.00 | 96.0% | 41.8% | 152.0 | – | – | 8.9 → 66.0 | 6.06 | ok |
| 19 | `mesh·tcp·250K·500ms` | 1900 | 475.00 | 87.7% | 0.0% | 460.7 | – | – | 8.5 → 51.3 | 4.37 | degraded: delivered 87.7% of what was asked (< 95%) |
| 20 | `mesh·udp·100K·1000ms` | 1900 | 190.00 | 103.1% | 0.0% | – | 0.18 | 0.00 | 8.8 → 29.4 | 1.87 | ok |

Per image at 950 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 999 | 1.2 | 99.4% | – |
| `kathara/frr` | 6 | 1.3 | 0.6% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
