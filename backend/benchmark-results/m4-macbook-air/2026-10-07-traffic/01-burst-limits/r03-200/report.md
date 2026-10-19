# Benchmark: m4-macbook-air · burst-limits · 200 hosts · round 3

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 14 cells on one deployment of 200 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 935.9 of 16746.1 MB used (5.6%) · host CPU 0.8% · Docker processes 264.8 MB · Docker's disk 71.3% used
- **Outcome:** 12 of 14 cells passed (2 degraded) · 2026-10-08T12:23:58 → 2026-10-08T12:58:19

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 200 | 1 | 213 | 212 | 29.8 | 1.75 | 20.8 | 13.3 | 15.6 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 14 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 100.0% | 100.5% | 98.9% | 100.1% | 100.1% |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 99.3% | 99.5% | 97.8% | 98.9% | 98.1% |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 1.15 | 0.69 | 0.61 | 0.72 | 0.89 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 0.05 | 0.00 | 1.06 | 0.00 | 0.00 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 75.8 | 70.8 | 66.8 | 63.0 | 64.0 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 5.16 | 4.80 | 4.55 | 4.23 | 4.40 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 100.3% | 100.3% | 100.6% | 100.8% | 100.6% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 98.8% | 99.5% | 99.0% | 96.0% | 98.0% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 94.1 | 6.6 | 7.8 | 7.1 | 8.7 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 9529 | 474 | 173 | 19 | 4 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 88.7 | 83.7 | 87.1 | 76.3 | 71.2 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 6.33 | 6.00 | 6.30 | 5.25 | 4.82 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 100.2% | – | – | – | – |
| 1M | – | – | 95.0% | 94.8% | 99.5% |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 99.8% | – | – | – | – |
| 1M | – | – | 60.0% | 58.1% | 91.5% |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 0.25 | – | – | – | – |
| 1M | – | – | 19.30 | 16.95 | 7.57 |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 0.00 | – | – | – | – |
| 1M | – | – | 0.63 | 0.62 | 0.06 |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 51.5 | – | – | – | – |
| 1M | – | – | 96.5 | 98.4 | 96.5 |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 3.19 | – | – | – | – |
| 1M | – | – | 7.04 | 7.23 | 7.13 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·udp·1M·1000ms` | 400 | 400.00 | 94.8% | 58.1% | – | 16.95 | 0.62 | 1.2 → 99.6 | 7.23 | degraded: delivered 94.8% of what was asked (< 95%) |
| 2 | `mesh·tcp·500K·250ms` | 400 | 200.00 | 100.3% | 99.5% | 6.6 | – | – | 1.2 → 84.9 | 6.00 | ok |
| 3 | `cs·udp·500K·1000ms` | 200 | 100.00 | 100.1% | 98.9% | – | 0.72 | 0.00 | 1.2 → 64.2 | 4.23 | ok |
| 4 | `mesh·tcp·500K·2000ms` | 400 | 200.00 | 100.6% | 98.0% | 8.7 | – | – | 1.2 → 72.4 | 4.82 | ok |
| 5 | `mesh·tcp·500K·100ms` | 400 | 200.00 | 100.3% | 98.8% | 94.1 | – | – | 1.1 → 89.8 | 6.33 | ok |
| 6 | `mesh·udp·1M·2000ms` | 400 | 400.00 | 99.5% | 91.5% | – | 7.57 | 0.06 | 1.2 → 97.8 | 7.13 | ok |
| 7 | `mesh·udp·500K·100ms` | 400 | 200.00 | 100.2% | 99.8% | – | 0.25 | 0.00 | 1.2 → 52.7 | 3.19 | ok |
| 8 | `cs·udp·500K·500ms` | 200 | 100.00 | 98.9% | 97.8% | – | 0.61 | 1.06 | 1.2 → 68.0 | 4.55 | degraded: UDP loss 1.06% > 1.0% |
| 9 | `cs·udp·500K·250ms` | 200 | 100.00 | 100.5% | 99.5% | – | 0.69 | 0.00 | 1.2 → 71.9 | 4.80 | ok |
| 10 | `mesh·tcp·500K·1000ms` | 400 | 200.00 | 100.8% | 96.0% | 7.1 | – | – | 1.1 → 77.4 | 5.25 | ok |
| 11 | `cs·udp·500K·100ms` | 200 | 100.00 | 100.0% | 99.3% | – | 1.15 | 0.05 | 1.1 → 76.9 | 5.16 | ok |
| 12 | `cs·udp·500K·2000ms` | 200 | 100.00 | 100.1% | 98.1% | – | 0.89 | 0.00 | 1.2 → 65.2 | 4.40 | ok |
| 13 | `mesh·tcp·500K·500ms` | 400 | 200.00 | 100.6% | 99.0% | 7.8 | – | – | 1.2 → 88.3 | 6.30 | ok |
| 14 | `mesh·udp·1M·500ms` | 400 | 400.00 | 95.0% | 60.0% | – | 19.30 | 0.63 | 1.2 → 97.7 | 7.04 | ok |

Per image at 200 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 211 | 1.2 | 99.0% | – |
| `kathara/frr` | 2 | 1.3 | 1.0% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
