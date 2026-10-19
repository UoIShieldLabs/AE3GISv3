# Benchmark: m4-macbook-air · burst-limits · 100 hosts · round 3

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 100 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 955.5 of 16746.1 MB used (5.7%) · host CPU 0.8% · Docker processes 266.8 MB · Docker's disk 71.2% used
- **Outcome:** 10 of 10 cells passed · 2026-10-08T11:41:13 → 2026-10-08T12:04:32

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | 1 | 109 | 108 | 12.3 | 0.67 | 7.1 | 14.1 | 15.8 | 1.3 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 100.0% | 100.0% | 100.1% | 100.1% | 100.0% |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 99.8% | 100.0% | 99.5% | 99.3% | 97.6% |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.75 | 0.49 | 0.76 | 1.23 | 0.18 |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 64.9 | 63.4 | 62.3 | 60.9 | 63.3 |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 4.29 | 4.25 | 4.14 | 4.15 | 4.36 |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 100.2% | 100.1% | 100.3% | 100.5% | 100.3% |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 99.8% | 99.5% | 99.0% | 98.0% | 98.0% |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 2.6 | 8.7 | 5.9 | 6.0 | 10.0 |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 1449 | 72 | 208 | 1 | 0 |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 69.2 | 85.7 | 76.9 | 69.6 | 68.0 |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 4.61 | 6.23 | 5.33 | 4.66 | 4.58 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·udp·1M·1000ms` | 100 | 100.00 | 100.1% | 99.3% | – | 1.23 | 0.00 | 0.7 → 61.6 | 4.15 | ok |
| 2 | `cs·udp·1M·500ms` | 100 | 100.00 | 100.1% | 99.5% | – | 0.76 | 0.00 | 0.7 → 63.0 | 4.14 | ok |
| 3 | `mesh·tcp·1M·250ms` | 200 | 200.00 | 100.1% | 99.5% | 8.7 | – | – | 0.7 → 86.4 | 6.23 | ok |
| 4 | `cs·udp·1M·250ms` | 100 | 100.00 | 100.0% | 100.0% | – | 0.49 | 0.00 | 0.7 → 64.2 | 4.25 | ok |
| 5 | `mesh·tcp·1M·2000ms` | 200 | 200.00 | 100.3% | 98.0% | 10.0 | – | – | 0.7 → 68.7 | 4.58 | ok |
| 6 | `mesh·tcp·1M·100ms` | 200 | 200.00 | 100.2% | 99.8% | 2.6 | – | – | 0.7 → 69.9 | 4.61 | ok |
| 7 | `mesh·tcp·1M·1000ms` | 200 | 200.00 | 100.5% | 98.0% | 6.0 | – | – | 0.8 → 70.4 | 4.66 | ok |
| 8 | `cs·udp·1M·100ms` | 100 | 100.00 | 100.0% | 99.8% | – | 0.75 | 0.00 | 0.7 → 65.6 | 4.29 | ok |
| 9 | `cs·udp·1M·2000ms` | 100 | 100.00 | 100.0% | 97.6% | – | 0.18 | 0.01 | 0.8 → 64.1 | 4.36 | ok |
| 10 | `mesh·tcp·1M·500ms` | 200 | 200.00 | 100.3% | 99.0% | 5.9 | – | – | 0.7 → 77.6 | 5.33 | ok |

Per image at 100 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 107 | 1.3 | 98.1% | – |
| `kathara/frr` | 2 | 1.3 | 1.9% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
