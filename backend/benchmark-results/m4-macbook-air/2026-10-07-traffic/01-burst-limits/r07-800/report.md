# Benchmark: m4-macbook-air · burst-limits · 800 hosts · round 7

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `9f7bf000d83f` · bench
- **Environment fingerprint:** `58939362f38b923000697fbb01697cae5c6d7d2c90b8a8443f4c386240ecd2b6`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 13 cells on one deployment of 800 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1003.0 of 16746.1 MB used (6.0%) · host CPU 0.7% · Docker processes 267.6 MB · Docker's disk 76.3% used
- **Outcome:** 0 of 13 cells passed (13 degraded) · 2026-10-11T02:52:48 → 2026-10-11T07:02:17

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 800 | 1 | 846 | 845 | 237.8 | 11.46 | 234.2 | 13.0 | 16.0 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 13 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 48.0% | 69.1% | 75.7% | 89.2% |
| 100K | – | 42.8% | – | – | 49.6% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.0% | 0.0% | 0.0% | 0.0% |
| 100K | – | 0.0% | – | – | 0.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 12.0 | 104.2 | 140.6 | 10.2 |
| 100K | – | 523.2 | – | – | 2716.5 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 4001 | 5443 | 3277 | 694 |
| 100K | – | 6988 | – | – | 4704 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 43.8 | 40.3 | 7.7 | 39.4 |
| 100K | – | 53.8 | – | – | 54.5 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 2.25 | 2.53 | 2.64 | 1.87 |
| 100K | – | 2.89 | – | – | 3.90 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 63.7% | 72.6% | – | 72.3% | 86.4% |
| 100K | – | – | – | 71.0% | 92.0% |
| 250K | – | – | – | – | 75.4% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.0% | 0.0% | – | 0.0% | 0.0% |
| 100K | – | – | – | 0.0% | 0.0% |
| 250K | – | – | – | – | 0.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 41.12 | 4.25 | – | 3.60 | 1.02 |
| 100K | – | – | – | 1.83 | 0.46 |
| 250K | – | – | – | – | 7.42 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | – | 0.00 | 0.00 |
| 100K | – | – | – | 0.00 | 0.00 |
| 250K | – | – | – | – | 0.00 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 43.5 | 40.1 | – | 36.9 | 33.8 |
| 100K | – | – | – | 38.2 | 37.9 |
| 250K | – | – | – | – | 48.5 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 2.02 | 1.82 | – | 1.70 | 1.55 |
| 100K | – | – | – | 1.86 | 1.75 |
| 250K | – | – | – | – | 2.79 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·50K·1000ms` | 1600 | 80.00 | 75.7% | 0.0% | 140.6 | – | – | 48.3 → 56.0 | 2.64 | degraded: delivered 75.7% of what was asked (< 95%) |
| 2 | `mesh·tcp·100K·2000ms` | 1600 | 160.00 | 49.6% | 0.0% | 2716.5 | – | – | 7.0 → 61.5 | 3.90 | degraded: delivered 49.6% of what was asked (< 95%) |
| 3 | `mesh·tcp·50K·2000ms` | 1600 | 80.00 | 89.2% | 0.0% | 10.2 | – | – | 7.9 → 47.3 | 1.87 | degraded: delivered 89.2% of what was asked (< 95%) |
| 4 | `mesh·udp·50K·100ms` | 1600 | 80.00 | 63.7% | 0.0% | – | 41.12 | 0.00 | 8.9 → 52.4 | 2.02 | degraded: delivered 63.7% of what was asked (< 95%) |
| 5 | `mesh·udp·100K·1000ms` | 1600 | 160.00 | 71.0% | 0.0% | – | 1.83 | 0.00 | 8.9 → 47.1 | 1.86 | degraded: delivered 71.0% of what was asked (< 95%) |
| 6 | `mesh·udp·50K·2000ms` | 1600 | 80.00 | 86.4% | 0.0% | – | 1.02 | 0.00 | 8.9 → 42.7 | 1.55 | degraded: delivered 86.4% of what was asked (< 95%) |
| 7 | `mesh·udp·250K·2000ms` | 1600 | 400.00 | 75.4% | 0.0% | – | 7.42 | 0.00 | 8.7 → 57.2 | 2.79 | degraded: delivered 75.4% of what was asked (< 95%) |
| 8 | `mesh·tcp·50K·500ms` | 1600 | 80.00 | 69.1% | 0.0% | 104.2 | – | – | 8.2 → 48.4 | 2.53 | degraded: delivered 69.1% of what was asked (< 95%) |
| 9 | `mesh·udp·50K·1000ms` | 1600 | 80.00 | 72.3% | 0.0% | – | 3.60 | 0.00 | 8.5 → 45.5 | 1.70 | degraded: delivered 72.3% of what was asked (< 95%) |
| 10 | `mesh·tcp·50K·250ms` | 1600 | 80.00 | 48.0% | 0.0% | 12.0 | – | – | 8.1 → 51.9 | 2.25 | degraded: delivered 48.0% of what was asked (< 95%) |
| 11 | `mesh·tcp·100K·250ms` | 1600 | 160.00 | 42.8% | 0.0% | 523.2 | – | – | 7.0 → 60.7 | 2.89 | degraded: delivered 42.8% of what was asked (< 95%) |
| 12 | `mesh·udp·50K·250ms` | 1600 | 80.00 | 72.6% | 0.0% | – | 4.25 | 0.00 | 7.7 → 47.8 | 1.82 | degraded: delivered 72.6% of what was asked (< 95%) |
| 13 | `mesh·udp·100K·2000ms` | 1600 | 160.00 | 92.0% | 0.0% | – | 0.46 | 0.00 | 8.0 → 45.8 | 1.75 | degraded: delivered 92.0% of what was asked (< 95%) |

Per image at 800 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 841 | 1.2 | 99.4% | – |
| `kathara/frr` | 5 | 1.3 | 0.6% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
