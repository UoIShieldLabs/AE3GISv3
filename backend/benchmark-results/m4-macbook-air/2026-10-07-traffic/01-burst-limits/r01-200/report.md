# Benchmark: m4-macbook-air · burst-limits · 200 hosts · round 1

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 200 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 888.3 of 16746.1 MB used (5.3%) · host CPU 0.8% · Docker processes 264.3 MB · Docker's disk 68.5% used
- **Outcome:** 8 of 10 cells passed (2 degraded) · 2026-10-08T00:33:20 → 2026-10-08T00:58:48

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 200 | 1 | 213 | 212 | 30.6 | 1.87 | 19.0 | 13.7 | 15.7 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 100.0% | 100.4% | 99.9% | 100.4% | 100.5% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 98.8% | 99.5% | 99.2% | 98.0% | 96.7% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 109.0 | 9.2 | 68.0 | 7.5 | 8.6 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 11079 | 500 | 341 | 36 | 3 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 87.1 | 84.8 | 88.8 | 78.5 | 69.5 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 6.20 | 6.08 | 6.41 | 5.48 | 4.67 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 94.8% | 88.8% | 95.8% | 97.9% | 99.9% |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 77.5% | 42.5% | 81.0% | 81.3% | 92.7% |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 18.38 | 19.37 | 15.40 | 13.21 | 7.49 |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.17 | 3.22 | 0.16 | 0.02 | 0.07 |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 96.2 | 96.9 | 95.1 | 95.4 | 95.5 |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 6.99 | 7.03 | 6.94 | 6.99 | 7.02 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·500K·1000ms` | 400 | 200.00 | 100.4% | 98.0% | 7.5 | – | – | 1.4 → 79.9 | 5.48 | ok |
| 2 | `mesh·tcp·500K·500ms` | 400 | 200.00 | 99.9% | 99.2% | 68.0 | – | – | 1.3 → 90.1 | 6.41 | ok |
| 3 | `mesh·udp·1M·250ms` | 400 | 400.00 | 88.8% | 42.5% | – | 19.37 | 3.22 | 1.2 → 98.1 | 7.03 | degraded: delivered 88.8% of what was asked (< 95%) |
| 4 | `mesh·tcp·500K·250ms` | 400 | 200.00 | 100.4% | 99.5% | 9.2 | – | – | 1.2 → 86.0 | 6.08 | ok |
| 5 | `mesh·udp·1M·2000ms` | 400 | 400.00 | 99.9% | 92.7% | – | 7.49 | 0.07 | 1.3 → 96.8 | 7.02 | ok |
| 6 | `mesh·udp·1M·100ms` | 400 | 400.00 | 94.8% | 77.5% | – | 18.38 | 0.17 | 1.2 → 97.4 | 6.99 | degraded: delivered 94.8% of what was asked (< 95%) |
| 7 | `mesh·udp·1M·1000ms` | 400 | 400.00 | 97.9% | 81.3% | – | 13.21 | 0.02 | 1.2 → 96.6 | 6.99 | ok |
| 8 | `mesh·tcp·500K·100ms` | 400 | 200.00 | 100.0% | 98.8% | 109.0 | – | – | 1.3 → 88.4 | 6.20 | ok |
| 9 | `mesh·tcp·500K·2000ms` | 400 | 200.00 | 100.5% | 96.7% | 8.6 | – | – | 1.2 → 70.7 | 4.67 | ok |
| 10 | `mesh·udp·1M·500ms` | 400 | 400.00 | 95.8% | 81.0% | – | 15.40 | 0.16 | 1.2 → 96.3 | 6.94 | ok |

Per image at 200 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 211 | 1.2 | 99.0% | – |
| `kathara/frr` | 2 | 1.3 | 1.0% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
