# Benchmark: m4-macbook-air · burst-limits · 900 hosts · round 6

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `9f7bf000d83f` · bench
- **Environment fingerprint:** `58939362f38b923000697fbb01697cae5c6d7d2c90b8a8443f4c386240ecd2b6`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 18 cells on one deployment of 900 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 983.0 of 16746.1 MB used (5.9%) · host CPU 0.8% · Docker processes 270.9 MB · Docker's disk 75.8% used
- **Outcome:** 2 of 13 cells passed (10 degraded, 1 stopped) · 2026-10-10T19:28:42 → 2026-10-11T00:29:34

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 900 | 1 | 953 | 952 | 341.8 | 11.58 | 325.4 | 12.7 | 16.0 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 13 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 92.8% | 96.2% | 97.4% | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 20.8% | 41.2% | 15.0% | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 320.7 | 303.5 | 388.8 | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 31738 | 33887 | 31962 | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 73.4 | 70.9 | 67.1 | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 5.25 | 5.08 | 4.71 | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 96.5% | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.0% | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 26.94 | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 2.67 | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 58.8 | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 3.95 | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 55.3% | 63.5% | 49.1% | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.0% | 0.0% | 0.0% | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 4.9 | 247.2 | 33.8 | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 3557 | 6625 | 1335 | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 40.8 | 44.5 | 19.4 | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 2.14 | 2.44 | 3.91 | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 59.2% | 58.9% | – | 25.6% | – |
| 100K | – | – | – | 63.7% | 76.0% |
| 250K | – | – | – | – | 41.6% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.0% | 0.0% | – | 0.0% | – |
| 100K | – | – | – | 0.0% | 0.0% |
| 250K | – | – | – | – | 0.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 6.72 | 1.04 | – | 0.52 | – |
| 100K | – | – | – | 0.61 | 0.77 |
| 250K | – | – | – | – | 130.92 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | – | 0.00 | – |
| 100K | – | – | – | 0.00 | 0.00 |
| 250K | – | – | – | – | 1.22 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 36.6 | 33.9 | – | 31.0 | – |
| 100K | – | – | – | 35.0 | 36.5 |
| 250K | – | – | – | – | 46.2 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 1.79 | 1.67 | – | 1.27 | – |
| 100K | – | – | – | 1.71 | 1.81 |
| 250K | – | – | – | – | 3.24 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·50K·1000ms` | 1800 | 90.00 | 49.1% | 0.0% | 33.8 | – | – | 49.2 → 68.5 | 3.91 | degraded: delivered 49.1% of what was asked (< 95%) |
| 2 | `mesh·udp·100K·2000ms` | 1800 | 180.00 | 76.0% | 0.0% | – | 0.77 | 0.00 | 9.5 → 46.0 | 1.81 | degraded: delivered 76.0% of what was asked (< 95%) |
| 3 | `cs·udp·50K·250ms` | 900 | 45.00 | 96.5% | 0.0% | – | 26.94 | 2.67 | 9.2 → 68.0 | 3.95 | degraded: UDP loss 2.67% > 1.0% |
| 4 | `mesh·tcp·50K·500ms` | 1800 | 90.00 | 63.5% | 0.0% | 247.2 | – | – | 9.4 → 53.9 | 2.44 | degraded: delivered 63.5% of what was asked (< 95%) |
| 5 | `mesh·tcp·50K·250ms` | 1800 | 90.00 | 55.3% | 0.0% | 4.9 | – | – | 10.0 → 50.8 | 2.14 | degraded: delivered 55.3% of what was asked (< 95%) |
| 6 | `mesh·udp·50K·100ms` | 1800 | 90.00 | 59.2% | 0.0% | – | 6.72 | 0.00 | 9.6 → 46.2 | 1.79 | degraded: delivered 59.2% of what was asked (< 95%) |
| 7 | `mesh·udp·50K·250ms` | 1800 | 90.00 | 58.9% | 0.0% | – | 1.04 | 0.00 | 10.6 → 44.5 | 1.67 | degraded: delivered 58.9% of what was asked (< 95%) |
| 8 | `cs·tcp·50K·1000ms` | 900 | 45.00 | 97.4% | 15.0% | 388.8 | – | – | 9.2 → 76.3 | 4.71 | ok |
| 9 | `mesh·udp·250K·2000ms` | 1800 | 450.00 | 41.6% | 0.0% | – | 130.92 | 1.22 | 9.2 → 55.4 | 3.24 | degraded: delivered 41.6% of what was asked (< 95%) |
| 10 | `mesh·udp·100K·1000ms` | 1800 | 180.00 | 63.7% | 0.0% | – | 0.61 | 0.00 | 9.1 → 44.2 | 1.71 | degraded: delivered 63.7% of what was asked (< 95%) |
| 11 | `cs·tcp·50K·500ms` | 900 | 45.00 | 96.2% | 41.2% | 303.5 | – | – | 8.7 → 79.6 | 5.08 | ok |
| 12 | `cs·tcp·50K·250ms` | 900 | 45.00 | 92.8% | 20.8% | 320.7 | – | – | 8.9 → 82.3 | 5.25 | degraded: delivered 92.8% of what was asked (< 95%) |
| 13 | `mesh·udp·50K·1000ms` | 1800 | 90.00 | 25.6% | 0.0% | – | 0.52 | 0.00 | 8.8 → 39.8 | 1.27 | stopped: memory stalls 16.1% > 10.0% for 3 sweeps |

Per image at 900 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 947 | 1.2 | 99.3% | – |
| `kathara/frr` | 6 | 1.4 | 0.7% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
