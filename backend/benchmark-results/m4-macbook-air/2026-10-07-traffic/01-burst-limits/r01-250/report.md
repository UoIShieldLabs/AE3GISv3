# Benchmark: m4-macbook-air · burst-limits · 250 hosts · round 1

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 250 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 921.8 of 16746.1 MB used (5.5%) · host CPU 0.8% · Docker processes 259.5 MB · Docker's disk 68.6% used
- **Outcome:** 5 of 10 cells passed (5 degraded) · 2026-10-08T00:59:36 → 2026-10-08T01:25:56

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 250 | 1 | 268 | 267 | 38.8 | 2.49 | 27.7 | 12.9 | 15.6 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 99.6% | 99.1% | 99.7% | 100.1% | 100.4% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 91.3% | 87.9% | 91.6% | 96.7% | 96.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 180.4 | 199.5 | 195.8 | 16.3 | 8.9 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 6754 | 11953 | 4682 | 1 | 1 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 85.1 | 84.2 | 82.1 | 77.4 | 66.5 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 6.08 | 6.09 | 5.90 | 5.47 | 4.59 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 78.0% | 88.1% | 95.3% | 98.2% | 95.6% |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 73.4% | 81.1% | 88.4% | 91.9% | 0.0% |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 6.39 | 2.23 | 1.18 | 0.63 | 0.62 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 22.00 | 11.94 | 4.73 | 1.84 | 3.55 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 87.9 | 85.3 | 83.0 | 81.6 | 80.5 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 6.41 | 6.25 | 6.04 | 5.92 | 5.86 |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·250K·1000ms` | 250 | 62.50 | 100.1% | 96.7% | 16.3 | – | – | 1.4 → 78.8 | 5.47 | ok |
| 2 | `cs·tcp·250K·500ms` | 250 | 62.50 | 99.7% | 91.6% | 195.8 | – | – | 1.4 → 83.5 | 5.90 | ok |
| 3 | `cs·udp·500K·250ms` | 250 | 125.00 | 88.1% | 81.1% | – | 2.23 | 11.94 | 1.4 → 86.8 | 6.25 | degraded: delivered 88.1% of what was asked (< 95%) |
| 4 | `cs·tcp·250K·250ms` | 250 | 62.50 | 99.1% | 87.9% | 199.5 | – | – | 1.4 → 85.5 | 6.09 | ok |
| 5 | `cs·udp·500K·2000ms` | 250 | 125.00 | 95.6% | 0.0% | – | 0.62 | 3.55 | 1.4 → 82.0 | 5.86 | degraded: UDP loss 3.55% > 1.0% |
| 6 | `cs·udp·500K·100ms` | 250 | 125.00 | 78.0% | 73.4% | – | 6.39 | 22.00 | 1.4 → 89.3 | 6.41 | degraded: delivered 78.0% of what was asked (< 95%) |
| 7 | `cs·udp·500K·1000ms` | 250 | 125.00 | 98.2% | 91.9% | – | 0.63 | 1.84 | 1.4 → 83.0 | 5.92 | degraded: UDP loss 1.84% > 1.0% |
| 8 | `cs·tcp·250K·100ms` | 250 | 62.50 | 99.6% | 91.3% | 180.4 | – | – | 1.5 → 86.7 | 6.08 | ok |
| 9 | `cs·tcp·250K·2000ms` | 250 | 62.50 | 100.4% | 96.0% | 8.9 | – | – | 1.4 → 67.9 | 4.59 | ok |
| 10 | `cs·udp·500K·500ms` | 250 | 125.00 | 95.3% | 88.4% | – | 1.18 | 4.73 | 1.4 → 84.3 | 6.04 | degraded: UDP loss 4.73% > 1.0% |

Per image at 250 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 265 | 1.2 | 98.8% | – |
| `kathara/frr` | 3 | 1.3 | 1.2% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
