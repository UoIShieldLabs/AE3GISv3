# Benchmark: m4max-studio-dd12-95g · burst-limits · 950 hosts · round 4

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 23 cells on one deployment of 950 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 2052.3 of 101850.2 MB used (2.0%) · host CPU 9.7% · Docker processes 342.2 MB · Docker's disk 8.8% used
- **Outcome:** 13 of 23 cells passed (10 degraded) · 2026-10-13T05:53:17 → 2026-10-13T10:15:18

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 950 | 1 | 1005 | 1004 | 233.9 | 3.81 | 264.4 | 13.5 | 15.9 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 23 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 96.9% | 93.9% | 96.8% | 97.9% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 0.0% | 8.1% | 16.2% | 75.0% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 152.5 | 146.8 | 151.0 | 152.1 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 69972 | 86227 | 80922 | 69325 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 58.7 | 59.5 | 55.6 | 57.6 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 6.20 | 6.31 | 6.05 | 6.15 | – |
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
| 100K | 1.79 | – | – | – | – |
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
| 100K | 42.8 | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 4.14 | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 93.0% | 91.3% | 101.6% | – |
| 100K | – | 93.1% | 92.9% | 100.3% | 111.7% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.0% | 0.0% | 0.0% | – |
| 100K | – | 0.0% | 0.0% | 0.0% | 0.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.8 | 0.9 | 1.7 | – |
| 100K | – | 1.6 | 5.1 | 2.9 | 3.0 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 278 | 103 | 67 | – |
| 100K | – | 636 | 699 | 129 | 66 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 28.0 | 26.5 | 22.0 | – |
| 100K | – | 31.9 | 31.4 | 27.6 | 26.9 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 2.54 | 2.39 | 2.07 | – |
| 100K | – | 2.94 | 2.97 | 2.59 | 2.56 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 92.4% | 93.1% | 99.3% | 102.4% | – |
| 100K | 90.2% | 91.6% | 96.7% | 103.0% | – |
| 250K | – | 91.9% | 96.9% | 101.8% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.0% | 0.0% | 0.0% | 0.0% | – |
| 100K | 0.0% | 0.0% | 0.0% | 0.0% | – |
| 250K | – | 0.0% | 0.0% | 0.0% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.23 | 0.28 | 0.17 | 0.17 | – |
| 100K | 0.33 | 0.28 | 0.20 | 0.18 | – |
| 250K | – | 0.39 | 0.28 | 0.21 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | 0.00 | 0.00 | – |
| 100K | 0.00 | 0.00 | 0.00 | 0.00 | – |
| 250K | – | 0.00 | 0.00 | 0.00 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 24.8 | 24.2 | 18.7 | 18.8 | – |
| 100K | 25.8 | 27.0 | 22.6 | 21.8 | – |
| 250K | – | 30.2 | 30.7 | 29.8 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 1.96 | 2.15 | 1.63 | 1.77 | – |
| 100K | 2.16 | 2.45 | 2.06 | 2.02 | – |
| 250K | – | 2.86 | 2.91 | 2.83 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·50K·500ms` | 1900 | 95.00 | 91.3% | 0.0% | 0.9 | – | – | 8.2 → 34.8 | 2.39 | degraded: delivered 91.3% of what was asked (< 95%) |
| 2 | `mesh·udp·100K·100ms` | 1900 | 190.00 | 90.2% | 0.0% | – | 0.33 | 0.00 | 8.6 → 34.4 | 2.16 | degraded: delivered 90.2% of what was asked (< 95%) |
| 3 | `mesh·udp·50K·1000ms` | 1900 | 95.00 | 102.4% | 0.0% | – | 0.17 | 0.00 | 8.9 → 27.7 | 1.77 | ok |
| 4 | `mesh·udp·250K·250ms` | 1900 | 475.00 | 91.9% | 0.0% | – | 0.39 | 0.00 | 9.0 → 39.2 | 2.86 | degraded: delivered 91.9% of what was asked (< 95%) |
| 5 | `mesh·udp·100K·1000ms` | 1900 | 190.00 | 103.0% | 0.0% | – | 0.18 | 0.00 | 8.6 → 30.4 | 2.02 | ok |
| 6 | `mesh·tcp·50K·1000ms` | 1900 | 95.00 | 101.6% | 0.0% | 1.7 | – | – | 9.0 → 31.0 | 2.07 | ok |
| 7 | `mesh·udp·100K·500ms` | 1900 | 190.00 | 96.7% | 0.0% | – | 0.20 | 0.00 | 8.8 → 31.4 | 2.06 | ok |
| 8 | `mesh·tcp·100K·2000ms` | 1900 | 190.00 | 111.7% | 0.0% | 3.0 | – | – | 9.0 → 36.0 | 2.56 | ok |
| 9 | `mesh·tcp·100K·1000ms` | 1900 | 190.00 | 100.3% | 0.0% | 2.9 | – | – | 8.8 → 36.4 | 2.59 | ok |
| 10 | `mesh·tcp·50K·250ms` | 1900 | 95.00 | 93.0% | 0.0% | 0.8 | – | – | 8.6 → 36.6 | 2.54 | degraded: delivered 93.0% of what was asked (< 95%) |
| 11 | `cs·tcp·100K·1000ms` | 950 | 95.00 | 97.9% | 75.0% | 152.1 | – | – | 8.6 → 66.1 | 6.15 | ok |
| 12 | `mesh·udp·50K·250ms` | 1900 | 95.00 | 93.1% | 0.0% | – | 0.28 | 0.00 | 8.8 → 33.0 | 2.15 | degraded: delivered 93.1% of what was asked (< 95%) |
| 13 | `mesh·udp·50K·100ms` | 1900 | 95.00 | 92.4% | 0.0% | – | 0.23 | 0.00 | 8.5 → 33.3 | 1.96 | degraded: delivered 92.4% of what was asked (< 95%) |
| 14 | `mesh·udp·250K·500ms` | 1900 | 475.00 | 96.9% | 0.0% | – | 0.28 | 0.00 | 9.0 → 39.7 | 2.91 | ok |
| 15 | `mesh·tcp·100K·250ms` | 1900 | 190.00 | 93.1% | 0.0% | 1.6 | – | – | 8.5 → 40.5 | 2.94 | degraded: delivered 93.1% of what was asked (< 95%) |
| 16 | `cs·tcp·100K·250ms` | 950 | 95.00 | 93.9% | 8.1% | 146.8 | – | – | 8.6 → 68.0 | 6.31 | degraded: delivered 93.9% of what was asked (< 95%) |
| 17 | `cs·udp·100K·100ms` | 950 | 95.00 | 100.2% | 99.0% | – | 1.79 | 0.00 | 8.3 → 51.1 | 4.14 | ok |
| 18 | `cs·tcp·100K·500ms` | 950 | 95.00 | 96.8% | 16.2% | 151.0 | – | – | 8.8 → 64.4 | 6.05 | ok |
| 19 | `mesh·udp·100K·250ms` | 1900 | 190.00 | 91.6% | 0.0% | – | 0.28 | 0.00 | 8.9 → 36.0 | 2.45 | degraded: delivered 91.6% of what was asked (< 95%) |
| 20 | `cs·tcp·100K·100ms` | 950 | 95.00 | 96.9% | 0.0% | 152.5 | – | – | 8.6 → 67.3 | 6.20 | ok |
| 21 | `mesh·tcp·100K·500ms` | 1900 | 190.00 | 92.9% | 0.0% | 5.1 | – | – | 8.5 → 39.9 | 2.97 | degraded: delivered 92.9% of what was asked (< 95%) |
| 22 | `mesh·udp·50K·500ms` | 1900 | 95.00 | 99.3% | 0.0% | – | 0.17 | 0.00 | 8.7 → 27.4 | 1.63 | ok |
| 23 | `mesh·udp·250K·1000ms` | 1900 | 475.00 | 101.8% | 0.0% | – | 0.21 | 0.00 | 8.8 → 38.6 | 2.83 | ok |

Per image at 950 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 999 | 1.2 | 99.3% | – |
| `kathara/frr` | 6 | 1.5 | 0.7% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
