# Benchmark: microsoft-surface-7 · burst-limits · 200 hosts · round 2

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `20c8b9e23b2c` · bench
- **Environment fingerprint:** `80bcc0f7cf6416d6093c854bced92b36fd9c47bcd0cf66b50bbcf2bab60c304b`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 200 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1078.5 of 16605.5 MB used (6.5%) · host CPU 13.8% · Docker processes 439.0 MB · Docker's disk 13.4% used
- **Outcome:** 0 of 10 cells passed (10 degraded) · 2026-10-11T22:40:42 → 2026-10-11T23:16:38

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 200 | 1 | 213 | 212 | 466.6 | 11.13 | 197.5 | 23.2 | 31.3 | 1.1 / 1.1 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 86.4% | 88.6% | 90.8% | 87.0% | 86.2% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 40.4% | 53.5% | 57.0% | 0.0% | 40.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 431.2 | 433.1 | 433.8 | 404.7 | 407.8 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 12712 | 13019 | 12874 | 13426 | 14471 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 74.2 | 73.1 | 73.7 | 72.7 | 73.5 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 5.55 | 5.56 | 5.57 | 5.48 | 5.55 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 60.9% | 61.5% | 60.9% | 67.2% | 68.7% |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 14.96 | 10.28 | 14.50 | 7.76 | 2.60 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 25.54 | 29.63 | 29.69 | 27.87 | 21.78 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 75.1 | 74.6 | 74.2 | 73.0 | 72.5 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 5.69 | 5.66 | 5.70 | 5.68 | 5.61 |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·250K·1000ms` | 200 | 50.00 | 87.0% | 0.0% | 404.7 | – | – | 8.7 → 81.4 | 5.48 | degraded: delivered 87.0% of what was asked (< 95%) |
| 2 | `cs·tcp·250K·500ms` | 200 | 50.00 | 90.8% | 57.0% | 433.8 | – | – | 8.3 → 82.1 | 5.57 | degraded: delivered 90.8% of what was asked (< 95%) |
| 3 | `cs·udp·500K·250ms` | 200 | 100.00 | 61.5% | 0.0% | – | 10.28 | 29.63 | 8.2 → 82.8 | 5.66 | degraded: delivered 61.5% of what was asked (< 95%) |
| 4 | `cs·tcp·250K·250ms` | 200 | 50.00 | 88.6% | 53.5% | 433.1 | – | – | 9.3 → 82.4 | 5.56 | degraded: delivered 88.6% of what was asked (< 95%) |
| 5 | `cs·udp·500K·2000ms` | 200 | 100.00 | 68.7% | 0.0% | – | 2.60 | 21.78 | 8.7 → 81.2 | 5.61 | degraded: delivered 68.7% of what was asked (< 95%) |
| 6 | `cs·udp·500K·100ms` | 200 | 100.00 | 60.9% | 0.0% | – | 14.96 | 25.54 | 9.4 → 84.4 | 5.69 | degraded: delivered 60.9% of what was asked (< 95%) |
| 7 | `cs·udp·500K·1000ms` | 200 | 100.00 | 67.2% | 0.0% | – | 7.76 | 27.87 | 9.0 → 82.0 | 5.68 | degraded: delivered 67.2% of what was asked (< 95%) |
| 8 | `cs·tcp·250K·100ms` | 200 | 50.00 | 86.4% | 40.4% | 431.2 | – | – | 8.6 → 82.7 | 5.55 | degraded: delivered 86.4% of what was asked (< 95%) |
| 9 | `cs·tcp·250K·2000ms` | 200 | 50.00 | 86.2% | 40.0% | 407.8 | – | – | 8.3 → 81.8 | 5.55 | degraded: delivered 86.2% of what was asked (< 95%) |
| 10 | `cs·udp·500K·500ms` | 200 | 100.00 | 60.9% | 0.0% | – | 14.50 | 29.69 | 8.4 → 82.7 | 5.70 | degraded: delivered 60.9% of what was asked (< 95%) |

Per image at 200 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 211 | 1.1 | 95.8% | – |
| `kathara/frr` | 2 | 5.0 | 4.2% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
