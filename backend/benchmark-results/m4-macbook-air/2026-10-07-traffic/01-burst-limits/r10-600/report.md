# Benchmark: m4-macbook-air · burst-limits · 600 hosts · round 10

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `e2d8d34a0813` · bench
- **Environment fingerprint:** `036273b48a56817c3973529837184fdad38a1fb3b176fea81eb0198dd7e57ee8`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 6 cells on one deployment of 600 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 986.6 of 16746.1 MB used (5.9%) · host CPU 0.7% · Docker processes 266.2 MB · Docker's disk 79.3% used
- **Outcome:** 6 of 6 cells passed · 2026-10-13T11:16:45 → 2026-10-13T11:47:43

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 600 | 1 | 635 | 634 | 147.9 | 7.50 | 138.2 | 13.4 | 16.1 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 6 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 99.0% | – | 100.4% | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 97.8% | – | 98.3% | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 2.60 | – | 0.68 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 0.91 | – | 0.30 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 49.9 | – | 44.0 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 3.33 | – | 3.12 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 100.1% | – | 100.8% | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 99.3% | – | 99.2% | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 7.7 | – | 3.6 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 516 | – | 12466 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 78.0 | – | 64.5 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 5.26 | – | 4.51 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | 100.0% | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | 100.0% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | 99.0% | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | 98.3% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | 0.19 | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | 1.26 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | 0.00 | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | 0.00 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | 27.9 | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | 75.8 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | 1.97 | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | 5.59 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·udp·100K·500ms` | 600 | 60.00 | 100.4% | 98.3% | – | 0.68 | 0.30 | 5.8 → 49.8 | 3.12 | ok |
| 2 | `mesh·udp·50K·500ms` | 1200 | 60.00 | 100.0% | 99.0% | – | 0.19 | 0.00 | 5.8 → 33.7 | 1.97 | ok |
| 3 | `cs·udp·100K·100ms` | 600 | 60.00 | 99.0% | 97.8% | – | 2.60 | 0.91 | 5.7 → 55.6 | 3.33 | ok |
| 4 | `mesh·tcp·100K·100ms` | 1200 | 120.00 | 100.1% | 99.3% | 7.7 | – | – | 5.6 → 83.7 | 5.26 | ok |
| 5 | `mesh·tcp·100K·500ms` | 1200 | 120.00 | 100.8% | 99.2% | 3.6 | – | – | 5.7 → 70.3 | 4.51 | ok |
| 6 | `mesh·udp·250K·1000ms` | 1200 | 300.00 | 100.0% | 98.3% | – | 1.26 | 0.00 | 5.9 → 81.6 | 5.59 | ok |

Per image at 600 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 631 | 1.2 | 99.3% | – |
| `kathara/frr` | 4 | 1.3 | 0.7% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
