# Benchmark: m4-macbook-air · burst-limits · 100 hosts · round 1

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 100 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 904.6 of 16746.1 MB used (5.4%) · host CPU 0.8% · Docker processes 267.9 MB · Docker's disk 68.4% used
- **Outcome:** 10 of 10 cells passed · 2026-10-07T23:55:05 → 2026-10-08T00:18:30

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | 1 | 109 | 108 | 12.8 | 0.68 | 7.4 | 13.9 | 15.9 | 1.3 / 1.3 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 100.0% | 100.0% | 100.1% | 100.0% | 99.9% |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 99.5% | 99.9% | 99.6% | 99.5% | 96.9% |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.68 | 0.55 | 0.86 | 1.09 | 0.29 |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.01 | 0.00 | 0.00 | 0.00 | 0.06 |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 63.6 | 62.9 | 59.3 | 58.3 | 59.4 |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 4.20 | 4.20 | 3.97 | 3.94 | 4.09 |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 100.2% | 100.2% | 100.2% | 100.6% | 100.4% |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 99.8% | 99.5% | 99.0% | 99.0% | 98.3% |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 2.6 | 7.7 | 5.7 | 4.8 | 8.8 |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 1824 | 343 | 10 | 2 | 1 |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 69.1 | 86.9 | 75.1 | 68.2 | 67.5 |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 4.60 | 6.29 | 5.19 | 4.44 | 4.52 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·udp·1M·1000ms` | 100 | 100.00 | 100.0% | 99.5% | – | 1.09 | 0.00 | 0.8 → 59.0 | 3.94 | ok |
| 2 | `cs·udp·1M·500ms` | 100 | 100.00 | 100.1% | 99.6% | – | 0.86 | 0.00 | 0.7 → 60.0 | 3.97 | ok |
| 3 | `mesh·tcp·1M·250ms` | 200 | 200.00 | 100.2% | 99.5% | 7.7 | – | – | 0.7 → 87.6 | 6.29 | ok |
| 4 | `cs·udp·1M·250ms` | 100 | 100.00 | 100.0% | 99.9% | – | 0.55 | 0.00 | 0.7 → 63.6 | 4.20 | ok |
| 5 | `mesh·tcp·1M·2000ms` | 200 | 200.00 | 100.4% | 98.3% | 8.8 | – | – | 0.8 → 68.3 | 4.52 | ok |
| 6 | `mesh·tcp·1M·100ms` | 200 | 200.00 | 100.2% | 99.8% | 2.6 | – | – | 0.7 → 69.8 | 4.60 | ok |
| 7 | `mesh·tcp·1M·1000ms` | 200 | 200.00 | 100.6% | 99.0% | 4.8 | – | – | 0.7 → 68.9 | 4.44 | ok |
| 8 | `cs·udp·1M·100ms` | 100 | 100.00 | 100.0% | 99.5% | – | 0.68 | 0.01 | 0.7 → 64.3 | 4.20 | ok |
| 9 | `cs·udp·1M·2000ms` | 100 | 100.00 | 99.9% | 96.9% | – | 0.29 | 0.06 | 0.8 → 60.2 | 4.09 | ok |
| 10 | `mesh·tcp·1M·500ms` | 200 | 200.00 | 100.2% | 99.0% | 5.7 | – | – | 0.7 → 75.9 | 5.19 | ok |

Per image at 100 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 107 | 1.3 | 97.9% | – |
| `kathara/frr` | 2 | 1.5 | 2.1% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
