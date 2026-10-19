# Benchmark: m4-macbook-air · burst-limits · 800 hosts · round 2

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 14 cells on one deployment of 800 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 940.2 of 16746.1 MB used (5.6%) · host CPU 0.8% · Docker processes 257.8 MB · Docker's disk 70.9% used
- **Outcome:** 9 of 14 cells passed (5 degraded) · 2026-10-08T09:34:54 → 2026-10-08T11:27:25

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 800 | 1 | 846 | 845 | 238.2 | 10.83 | 195.0 | 13.4 | 15.8 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 14 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.4% | 98.0% | 98.7% | 100.2% | 101.2% |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 91.6% | 32.4% | 75.8% | 90.0% | 95.0% |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 231.9 | 306.6 | 259.6 | 85.8 | 22.7 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 5476 | 29798 | 23632 | 11343 | 3303 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 78.0 | 78.0 | 73.0 | 66.4 | 56.6 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 5.50 | 5.53 | 5.21 | 4.56 | 3.94 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 95.1% | 100.3% | 99.9% | 101.9% | 103.2% |
| 100K | 98.6% | – | 94.3% | 84.6% | 99.3% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 92.0% | 96.5% | 98.8% | 97.5% | 95.0% |
| 100K | 93.6% | – | 0.0% | 0.0% | 85.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 34.54 | 7.46 | 0.69 | 0.57 | 0.36 |
| 100K | 24.91 | – | 11.06 | 10.77 | 3.65 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.79 | 0.01 | 0.00 | 0.00 | 0.00 |
| 100K | 1.28 | – | 6.16 | 8.27 | 1.71 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 67.5 | 56.0 | 39.3 | 34.3 | 30.6 |
| 100K | 69.4 | – | 57.7 | 27.7 | 54.8 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.46 | 3.58 | 2.61 | 2.24 | 2.03 |
| 100K | 4.51 | – | 3.99 | 4.87 | 3.77 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·udp·100K·1000ms` | 800 | 80.00 | 84.6% | 0.0% | – | 10.77 | 8.27 | 48.2 → 75.8 | 4.87 | degraded: delivered 84.6% of what was asked (< 95%) |
| 2 | `cs·udp·50K·250ms` | 800 | 40.00 | 100.3% | 96.5% | – | 7.46 | 0.01 | 5.3 → 61.3 | 3.58 | ok |
| 3 | `cs·tcp·50K·1000ms` | 800 | 40.00 | 100.2% | 90.0% | 85.8 | – | – | 5.4 → 71.8 | 4.56 | ok |
| 4 | `cs·udp·50K·2000ms` | 800 | 40.00 | 103.2% | 95.0% | – | 0.36 | 0.00 | 5.8 → 36.4 | 2.03 | ok |
| 5 | `cs·udp·50K·100ms` | 800 | 40.00 | 95.1% | 92.0% | – | 34.54 | 4.79 | 7.1 → 74.5 | 4.46 | degraded: UDP loss 4.79% > 1.0% |
| 6 | `cs·udp·100K·2000ms` | 800 | 80.00 | 99.3% | 85.0% | – | 3.65 | 1.71 | 6.0 → 60.8 | 3.77 | degraded: UDP loss 1.71% > 1.0% |
| 7 | `cs·udp·100K·100ms` | 800 | 80.00 | 98.6% | 93.6% | – | 24.91 | 1.28 | 5.6 → 75.0 | 4.51 | degraded: UDP loss 1.28% > 1.0% |
| 8 | `cs·tcp·50K·500ms` | 800 | 40.00 | 98.7% | 75.8% | 259.6 | – | – | 7.2 → 80.2 | 5.21 | ok |
| 9 | `cs·tcp·50K·250ms` | 800 | 40.00 | 98.0% | 32.4% | 306.6 | – | – | 6.8 → 84.8 | 5.53 | ok |
| 10 | `cs·udp·50K·1000ms` | 800 | 40.00 | 101.9% | 97.5% | – | 0.57 | 0.00 | 7.0 → 41.3 | 2.24 | ok |
| 11 | `cs·tcp·50K·100ms` | 800 | 40.00 | 99.4% | 91.6% | 231.9 | – | – | 7.3 → 85.3 | 5.50 | ok |
| 12 | `cs·tcp·50K·2000ms` | 800 | 40.00 | 101.2% | 95.0% | 22.7 | – | – | 7.2 → 63.8 | 3.94 | ok |
| 13 | `cs·udp·50K·500ms` | 800 | 40.00 | 99.9% | 98.8% | – | 0.69 | 0.00 | 8.3 → 47.6 | 2.61 | ok |
| 14 | `cs·udp·100K·500ms` | 800 | 80.00 | 94.3% | 0.0% | – | 11.06 | 6.16 | 8.4 → 66.0 | 3.99 | degraded: delivered 94.3% of what was asked (< 95%) |

Per image at 800 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 841 | 1.2 | 99.4% | – |
| `kathara/frr` | 5 | 1.3 | 0.6% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
