# Benchmark: m4-macbook-air · burst-limits · 200 hosts · round 2

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 200 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 943.4 of 16746.1 MB used (5.6%) · host CPU 0.8% · Docker processes 266.7 MB · Docker's disk 69.8% used
- **Outcome:** 5 of 10 cells passed (5 degraded) · 2026-10-08T05:21:36 → 2026-10-08T05:47:04

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 200 | 1 | 213 | 212 | 32.1 | 1.91 | 20.5 | 13.3 | 15.6 | 1.3 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 72.8% | 73.1% | 72.9% | 69.7% | 72.0% |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 52.6% | 50.4% | 48.0% | 43.3% | 50.0% |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 226.7 | 228.9 | 245.7 | 228.0 | 241.5 |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 18244 | 17459 | 18385 | 17507 | 17468 |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 87.3 | 86.9 | 86.7 | 86.1 | 84.1 |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 6.31 | 6.27 | 6.27 | 6.23 | 6.15 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 100.1% | 99.9% | 100.0% | 100.0% | 100.1% |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 99.5% | 96.2% | 99.7% | 99.2% | 97.0% |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 1.25 | 1.27 | 0.56 | 0.83 | 0.84 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 0.03 | 0.40 | 0.00 | 0.00 | 0.09 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 77.7 | 71.9 | 67.0 | 64.0 | 64.6 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 5.38 | 4.95 | 4.61 | 4.38 | 4.47 |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·500K·1000ms` | 200 | 100.00 | 69.7% | 43.3% | 228.0 | – | – | 1.4 → 87.4 | 6.23 | degraded: delivered 69.7% of what was asked (< 95%) |
| 2 | `cs·tcp·500K·500ms` | 200 | 100.00 | 72.9% | 48.0% | 245.7 | – | – | 1.3 → 88.0 | 6.27 | degraded: delivered 72.9% of what was asked (< 95%) |
| 3 | `cs·udp·500K·250ms` | 200 | 100.00 | 99.9% | 96.2% | – | 1.27 | 0.40 | 1.2 → 73.2 | 4.95 | ok |
| 4 | `cs·tcp·500K·250ms` | 200 | 100.00 | 73.1% | 50.4% | 228.9 | – | – | 1.3 → 88.1 | 6.27 | degraded: delivered 73.1% of what was asked (< 95%) |
| 5 | `cs·udp·500K·2000ms` | 200 | 100.00 | 100.1% | 97.0% | – | 0.84 | 0.09 | 1.3 → 66.0 | 4.47 | ok |
| 6 | `cs·udp·500K·100ms` | 200 | 100.00 | 100.1% | 99.5% | – | 1.25 | 0.03 | 1.2 → 78.9 | 5.38 | ok |
| 7 | `cs·udp·500K·1000ms` | 200 | 100.00 | 100.0% | 99.2% | – | 0.83 | 0.00 | 1.3 → 65.3 | 4.38 | ok |
| 8 | `cs·tcp·500K·100ms` | 200 | 100.00 | 72.8% | 52.6% | 226.7 | – | – | 1.5 → 88.8 | 6.31 | degraded: delivered 72.8% of what was asked (< 95%) |
| 9 | `cs·tcp·500K·2000ms` | 200 | 100.00 | 72.0% | 50.0% | 241.5 | – | – | 2.3 → 86.4 | 6.15 | degraded: delivered 72.0% of what was asked (< 95%) |
| 10 | `cs·udp·500K·500ms` | 200 | 100.00 | 100.0% | 99.7% | – | 0.56 | 0.00 | 1.1 → 68.1 | 4.61 | ok |

Per image at 200 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 211 | 1.2 | 98.1% | – |
| `kathara/frr` | 2 | 2.5 | 1.9% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
