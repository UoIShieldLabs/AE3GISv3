# Benchmark: m4-macbook-air · burst-limits · 550 hosts · round 1

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 25 cells on one deployment of 550 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 928.9 of 16746.1 MB used (5.5%) · host CPU 0.8% · Docker processes 266.0 MB · Docker's disk 68.9% used
- **Outcome:** 14 of 17 cells passed (2 degraded, 1 stopped) · 2026-10-08T02:29:35 → 2026-10-08T03:23:10

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 550 | 1 | 583 | 582 | 123.3 | 6.07 | 129.7 | 13.3 | 15.7 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 17 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 102.2% | – |
| 100K | 100.2% | 100.4% | 100.5% | 101.8% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 96.7% | – |
| 100K | 95.0% | 0.0% | 96.3% | 95.9% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 2.3 | – |
| 100K | 62.1 | 3600.6 | 84.1 | 6.0 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 1051 | – |
| 100K | 527 | 7156 | 8405 | 3303 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 39.4 | – |
| 100K | 72.6 | 75.6 | 61.2 | 58.3 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | 1.93 | – |
| 100K | 4.15 | 4.38 | 3.68 | 3.62 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.9% | 100.6% | 101.4% | 102.3% | – |
| 100K | 100.2% | 97.7% | – | 103.1% | 104.3% |
| 250K | 62.9% | 96.2% | – | 101.6% | 102.3% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 90.4% | 100.4% | 98.3% | 96.7% | – |
| 100K | 99.0% | 74.8% | – | 96.7% | 93.3% |
| 250K | 0.0% | 0.0% | – | 82.0% | 93.3% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 55.67 | 1.11 | 3.96 | 0.20 | – |
| 100K | 1.07 | 103.87 | – | 2.77 | 0.22 |
| 250K | 109.03 | 76.64 | – | 13.19 | 0.85 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | 0.00 | 0.00 | – |
| 100K | 0.00 | 0.00 | – | 0.00 | 0.00 |
| 250K | 1.95 | 1.37 | – | 0.14 | 0.00 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 54.8 | 37.6 | 30.6 | 26.4 | – |
| 100K | 51.5 | 55.4 | – | 43.0 | 34.5 |
| 250K | 78.0 | 76.4 | – | 69.1 | 61.5 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 2.87 | 1.91 | 2.14 | 1.15 | – |
| 100K | 2.29 | 2.69 | – | 2.44 | 1.73 |
| 250K | 4.68 | 5.09 | – | 4.35 | 3.86 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·100K·1000ms` | 1100 | 110.00 | 101.8% | 95.9% | 6.0 | – | – | 3.8 → 62.1 | 3.62 | ok |
| 2 | `mesh·udp·100K·2000ms` | 1100 | 110.00 | 104.3% | 93.3% | – | 0.22 | 0.00 | 5.1 → 39.6 | 1.73 | ok |
| 3 | `mesh·udp·50K·500ms` | 1100 | 55.00 | 101.4% | 98.3% | – | 3.96 | 0.00 | 5.2 → 35.8 | 2.14 | ok |
| 4 | `mesh·udp·250K·250ms` | 1100 | 275.00 | 96.2% | 0.0% | – | 76.64 | 1.37 | 5.3 → 81.7 | 5.09 | degraded: UDP loss 1.37% > 1.0% |
| 5 | `mesh·tcp·100K·500ms` | 1100 | 110.00 | 100.5% | 96.3% | 84.1 | – | – | 5.4 → 66.6 | 3.68 | ok |
| 6 | `mesh·udp·50K·250ms` | 1100 | 55.00 | 100.6% | 100.4% | – | 1.11 | 0.00 | 5.1 → 42.8 | 1.91 | ok |
| 7 | `mesh·udp·250K·2000ms` | 1100 | 275.00 | 102.3% | 93.3% | – | 0.85 | 0.00 | 5.3 → 66.8 | 3.86 | ok |
| 8 | `mesh·udp·250K·1000ms` | 1100 | 275.00 | 101.6% | 82.0% | – | 13.19 | 0.14 | 5.5 → 74.5 | 4.35 | ok |
| 9 | `mesh·udp·50K·100ms` | 1100 | 55.00 | 99.9% | 90.4% | – | 55.67 | 0.00 | 7.8 → 62.6 | 2.87 | ok |
| 10 | `mesh·udp·250K·100ms` | 1100 | 275.00 | 62.9% | 0.0% | – | 109.03 | 1.95 | 4.9 → 82.9 | 4.68 | degraded: delivered 62.9% of what was asked (< 95%) |
| 11 | `mesh·udp·100K·100ms` | 1100 | 110.00 | 100.2% | 99.0% | – | 1.07 | 0.00 | 4.9 → 56.4 | 2.29 | ok |
| 12 | `mesh·udp·100K·1000ms` | 1100 | 110.00 | 103.1% | 96.7% | – | 2.77 | 0.00 | 5.0 → 48.1 | 2.44 | ok |
| 13 | `mesh·udp·50K·1000ms` | 1100 | 55.00 | 102.3% | 96.7% | – | 0.20 | 0.00 | 5.6 → 31.9 | 1.15 | ok |
| 14 | `mesh·tcp·50K·1000ms` | 1100 | 55.00 | 102.2% | 96.7% | 2.3 | – | – | 4.9 → 44.3 | 1.93 | ok |
| 15 | `mesh·tcp·100K·100ms` | 1100 | 110.00 | 100.2% | 95.0% | 62.1 | – | – | 3.3 → 75.9 | 4.15 | ok |
| 16 | `mesh·tcp·100K·250ms` | 1100 | 110.00 | 100.4% | 0.0% | 3600.6 | – | – | 4.8 → 80.3 | 4.38 | ok |
| 17 | `mesh·udp·100K·250ms` | 1100 | 110.00 | 97.7% | 74.8% | – | 103.87 | 0.00 | 4.8 → 60.2 | 2.69 | stopped: memory stalls 13.1% > 10.0% for 3 sweeps |

Per image at 550 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 579 | 1.2 | 99.3% | – |
| `kathara/frr` | 4 | 1.3 | 0.7% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
