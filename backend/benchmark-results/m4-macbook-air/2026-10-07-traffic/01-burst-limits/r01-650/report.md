# Benchmark: m4-macbook-air · burst-limits · 650 hosts · round 1

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 20 cells on one deployment of 650 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 923.3 of 16746.1 MB used (5.5%) · host CPU 0.8% · Docker processes 265.5 MB · Docker's disk 69.3% used
- **Outcome:** 14 of 20 cells passed (6 degraded) · 2026-10-08T03:24:06 → 2026-10-08T04:36:40

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 650 | 1 | 690 | 689 | 212.9 | 13.59 | 168.0 | – | – | – / – | – | – | – | – | – | – | – | ok |

Traffic matrix: 20 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.5% | 99.3% | 100.9% | 103.4% | 101.0% |
| 100K | 79.2% | 78.2% | 75.5% | 76.8% | 83.9% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 94.5% | 0.0% | 95.0% | 94.8% | 92.0% |
| 100K | 4.2% | 35.0% | 21.0% | 18.0% | 16.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 157.2 | 295.5 | 94.6 | 36.4 | 14.9 |
| 100K | 289.5 | 290.1 | 314.8 | 296.6 | 265.3 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0 | 19099 | 13823 | 7427 | 1568 |
| 100K | 38874 | 44162 | 41511 | 43445 | 44222 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 79.2 | 77.5 | 65.1 | 59.0 | 49.6 |
| 100K | 82.9 | 83.5 | 78.1 | 78.5 | 79.1 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 5.67 | 5.46 | 4.59 | 3.94 | 3.43 |
| 100K | 5.81 | 5.93 | 5.54 | 5.64 | 5.80 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.2% | 100.5% | 100.0% | 102.0% | 103.4% |
| 100K | 99.6% | 96.2% | 100.0% | 101.3% | 102.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.5% | 99.5% | 99.7% | 98.0% | 96.0% |
| 100K | 98.6% | 86.5% | 97.0% | 96.0% | 96.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 6.61 | 1.11 | 0.52 | 0.38 | 0.32 |
| 100K | 11.71 | 15.65 | 5.47 | 1.08 | 0.68 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 100K | 0.55 | 3.05 | 0.56 | 0.01 | 0.01 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 64.7 | 48.8 | 33.5 | 29.6 | 24.6 |
| 100K | 62.6 | 67.5 | 56.0 | 46.3 | 45.3 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.01 | 3.07 | 2.16 | 1.87 | 1.76 |
| 100K | 4.02 | 4.68 | 3.76 | 3.14 | 3.15 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·100K·250ms` | 650 | 65.00 | 78.2% | 35.0% | 290.1 | – | – | 4.0 → 87.5 | 5.93 | degraded: delivered 78.2% of what was asked (< 95%) |
| 2 | `cs·udp·100K·100ms` | 650 | 65.00 | 99.6% | 98.6% | – | 11.71 | 0.55 | 5.6 → 68.2 | 4.02 | ok |
| 3 | `cs·tcp·50K·250ms` | 650 | 32.50 | 99.3% | 0.0% | 295.5 | – | – | 5.5 → 83.0 | 5.46 | ok |
| 4 | `cs·udp·100K·1000ms` | 650 | 65.00 | 101.3% | 96.0% | – | 1.08 | 0.01 | 5.3 → 51.6 | 3.14 | ok |
| 5 | `cs·udp·100K·2000ms` | 650 | 65.00 | 102.0% | 96.0% | – | 0.68 | 0.01 | 5.6 → 51.0 | 3.15 | ok |
| 6 | `cs·tcp·100K·500ms` | 650 | 65.00 | 75.5% | 21.0% | 314.8 | – | – | 5.2 → 83.2 | 5.54 | degraded: delivered 75.5% of what was asked (< 95%) |
| 7 | `cs·udp·100K·250ms` | 650 | 65.00 | 96.2% | 86.5% | – | 15.65 | 3.05 | 6.0 → 73.5 | 4.68 | degraded: UDP loss 3.05% > 1.0% |
| 8 | `cs·udp·50K·250ms` | 650 | 32.50 | 100.5% | 99.5% | – | 1.11 | 0.00 | 3.9 → 52.7 | 3.07 | ok |
| 9 | `cs·udp·50K·100ms` | 650 | 32.50 | 100.2% | 99.5% | – | 6.61 | 0.00 | 3.9 → 68.6 | 4.01 | ok |
| 10 | `cs·tcp·100K·100ms` | 650 | 65.00 | 79.2% | 4.2% | 289.5 | – | – | 3.6 → 86.5 | 5.81 | degraded: delivered 79.2% of what was asked (< 95%) |
| 11 | `cs·tcp·50K·1000ms` | 650 | 32.50 | 103.4% | 94.8% | 36.4 | – | – | 3.3 → 62.3 | 3.94 | ok |
| 12 | `cs·udp·50K·500ms` | 650 | 32.50 | 100.0% | 99.7% | – | 0.52 | 0.00 | 4.7 → 38.2 | 2.16 | ok |
| 13 | `cs·udp·50K·1000ms` | 650 | 32.50 | 102.0% | 98.0% | – | 0.38 | 0.00 | 3.4 → 33.0 | 1.87 | ok |
| 14 | `cs·tcp·100K·1000ms` | 650 | 65.00 | 76.8% | 18.0% | 296.6 | – | – | 5.3 → 83.8 | 5.64 | degraded: delivered 76.8% of what was asked (< 95%) |
| 15 | `cs·udp·100K·500ms` | 650 | 65.00 | 100.0% | 97.0% | – | 5.47 | 0.56 | 5.3 → 61.3 | 3.76 | ok |
| 16 | `cs·tcp·50K·2000ms` | 650 | 32.50 | 101.0% | 92.0% | 14.9 | – | – | 5.6 → 55.1 | 3.43 | ok |
| 17 | `cs·tcp·50K·500ms` | 650 | 32.50 | 100.9% | 95.0% | 94.6 | – | – | 6.2 → 71.3 | 4.59 | ok |
| 18 | `cs·tcp·50K·100ms` | 650 | 32.50 | 99.5% | 94.5% | 157.2 | – | – | 6.3 → 85.5 | 5.67 | ok |
| 19 | `cs·tcp·100K·2000ms` | 650 | 65.00 | 83.9% | 16.0% | 265.3 | – | – | 6.2 → 85.3 | 5.80 | degraded: delivered 83.9% of what was asked (< 95%) |
| 20 | `cs·udp·50K·2000ms` | 650 | 32.50 | 103.4% | 96.0% | – | 0.32 | 0.00 | 6.4 → 31.1 | 1.76 | ok |

Per image at 650 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | – | – | – | – |
| `kathara/frr` | – | – | – | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
