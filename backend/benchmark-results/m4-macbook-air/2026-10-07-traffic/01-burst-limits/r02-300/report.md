# Benchmark: m4-macbook-air · burst-limits · 300 hosts · round 2

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 300 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 928.0 of 16746.1 MB used (5.5%) · host CPU 0.8% · Docker processes 267.9 MB · Docker's disk 70.0% used
- **Outcome:** 4 of 10 cells passed (6 degraded) · 2026-10-08T06:12:09 → 2026-10-08T06:40:48

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 300 | 1 | 320 | 319 | 58.4 | 3.29 | 43.4 | 12.8 | 15.6 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 77.5% | 76.2% | 75.3% | 73.6% | 80.8% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 50.8% | 51.5% | 43.0% | 50.0% | 53.3% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 249.7 | 238.7 | 250.2 | 244.7 | 228.7 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 23170 | 25905 | 24502 | 23387 | 24065 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 83.8 | 83.3 | 83.2 | 84.2 | 84.1 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 5.95 | 5.94 | 5.93 | 6.00 | 6.02 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 92.9% | 95.9% | 99.9% | 100.0% | 100.2% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 65.1% | 63.4% | 99.0% | 98.0% | 97.4% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 35.64 | 35.04 | 0.80 | 6.07 | 2.87 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 0.36 | 0.49 | 0.00 | 0.00 | 0.01 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 94.5 | 96.3 | 79.8 | 86.2 | 85.2 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 6.62 | 6.78 | 5.61 | 6.09 | 5.98 |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·250K·1000ms` | 300 | 75.00 | 73.6% | 50.0% | 244.7 | – | – | 1.6 → 85.9 | 6.00 | degraded: delivered 73.6% of what was asked (< 95%) |
| 2 | `cs·tcp·250K·500ms` | 300 | 75.00 | 75.3% | 43.0% | 250.2 | – | – | 1.6 → 84.9 | 5.93 | degraded: delivered 75.3% of what was asked (< 95%) |
| 3 | `mesh·udp·500K·250ms` | 600 | 300.00 | 95.9% | 63.4% | – | 35.04 | 0.49 | 1.9 → 98.2 | 6.78 | ok |
| 4 | `cs·tcp·250K·250ms` | 300 | 75.00 | 76.2% | 51.5% | 238.7 | – | – | 2.1 → 85.4 | 5.94 | degraded: delivered 76.2% of what was asked (< 95%) |
| 5 | `mesh·udp·500K·2000ms` | 600 | 300.00 | 100.2% | 97.4% | – | 2.87 | 0.01 | 2.0 → 87.2 | 5.98 | ok |
| 6 | `mesh·udp·500K·100ms` | 600 | 300.00 | 92.9% | 65.1% | – | 35.64 | 0.36 | 2.1 → 96.6 | 6.62 | degraded: delivered 92.9% of what was asked (< 95%) |
| 7 | `mesh·udp·500K·1000ms` | 600 | 300.00 | 100.0% | 98.0% | – | 6.07 | 0.00 | 1.8 → 88.0 | 6.09 | ok |
| 8 | `cs·tcp·250K·100ms` | 300 | 75.00 | 77.5% | 50.8% | 249.7 | – | – | 1.9 → 85.8 | 5.95 | degraded: delivered 77.5% of what was asked (< 95%) |
| 9 | `cs·tcp·250K·2000ms` | 300 | 75.00 | 80.8% | 53.3% | 228.7 | – | – | 1.9 → 86.0 | 6.02 | degraded: delivered 80.8% of what was asked (< 95%) |
| 10 | `mesh·udp·500K·500ms` | 600 | 300.00 | 99.9% | 99.0% | – | 0.80 | 0.00 | 2.1 → 82.0 | 5.61 | ok |

Per image at 300 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 317 | 1.2 | 99.0% | – |
| `kathara/frr` | 3 | 1.3 | 1.0% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
