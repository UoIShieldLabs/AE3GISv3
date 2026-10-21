# Benchmark: m4max-studio-dd12-95g · burst-limits · 900 hosts · round 5

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 900 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 2011.2 of 101850.2 MB used (2.0%) · host CPU 9.9% · Docker processes 335.1 MB · Docker's disk 8.8% used
- **Outcome:** 9 of 10 cells passed (1 degraded) · 2026-10-13T15:40:52 → 2026-10-13T19:35:09

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 900 | 1 | 953 | 952 | 211.0 | 3.55 | 245.8 | 13.4 | 16.0 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | 94.9% | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | 18.7% | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | 146.7 | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | 83602 | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | 55.9 | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | 6.19 | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 101.3% | 103.0% | – | – |
| 100K | – | 96.5% | 103.1% | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 95.4% | 92.3% | – | – |
| 100K | – | 0.0% | 91.7% | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.8 | 1.0 | – | – |
| 100K | – | 6.3 | 3.0 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 273 | 103 | – | – |
| 100K | – | 2343 | 423 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 27.5 | 25.0 | – | – |
| 100K | – | 34.0 | 29.1 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 2.73 | 2.45 | – | – |
| 100K | – | 3.35 | 3.03 | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.6% | 101.3% | – | – | – |
| 100K | 100.0% | 101.3% | – | – | – |
| 250K | – | 101.6% | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 94.8% | 96.4% | – | – | – |
| 100K | 99.9% | 95.5% | – | – | – |
| 250K | – | 79.4% | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.29 | 0.23 | – | – | – |
| 100K | 0.12 | 0.22 | – | – | – |
| 250K | – | 0.49 | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | – | – | – |
| 100K | 0.00 | 0.00 | – | – | – |
| 250K | – | 0.00 | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 25.4 | 22.7 | – | – | – |
| 100K | 26.4 | 25.8 | – | – | – |
| 250K | – | 31.6 | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 2.38 | 2.16 | – | – | – |
| 100K | 2.39 | 2.50 | – | – | – |
| 250K | – | 3.18 | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·100K·250ms` | 1800 | 180.00 | 96.5% | 0.0% | 6.3 | – | – | 10.1 → 44.1 | 3.35 | ok |
| 2 | `mesh·tcp·50K·500ms` | 1800 | 90.00 | 103.0% | 92.3% | 1.0 | – | – | 10.4 → 35.4 | 2.45 | ok |
| 3 | `mesh·udp·50K·250ms` | 1800 | 90.00 | 101.3% | 96.4% | – | 0.23 | 0.00 | 10.3 → 33.1 | 2.16 | ok |
| 4 | `mesh·tcp·50K·250ms` | 1800 | 90.00 | 101.3% | 95.4% | 0.8 | – | – | 10.9 → 38.5 | 2.73 | ok |
| 5 | `mesh·udp·250K·250ms` | 1800 | 450.00 | 101.6% | 79.4% | – | 0.49 | 0.00 | 10.6 → 42.2 | 3.18 | ok |
| 6 | `mesh·udp·50K·100ms` | 1800 | 90.00 | 100.6% | 94.8% | – | 0.29 | 0.00 | 10.3 → 35.8 | 2.38 | ok |
| 7 | `mesh·udp·100K·250ms` | 1800 | 180.00 | 101.3% | 95.5% | – | 0.22 | 0.00 | 10.7 → 36.6 | 2.50 | ok |
| 8 | `cs·tcp·100K·250ms` | 900 | 90.00 | 94.9% | 18.7% | 146.7 | – | – | 10.3 → 66.2 | 6.19 | degraded: delivered 94.9% of what was asked (< 95%) |
| 9 | `mesh·tcp·100K·500ms` | 1800 | 180.00 | 103.1% | 91.7% | 3.0 | – | – | 11.0 → 40.1 | 3.03 | ok |
| 10 | `mesh·udp·100K·100ms` | 1800 | 180.00 | 100.0% | 99.9% | – | 0.12 | 0.00 | 10.5 → 36.9 | 2.39 | ok |

Per image at 900 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 947 | 1.2 | 99.4% | – |
| `kathara/frr` | 6 | 1.3 | 0.6% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
