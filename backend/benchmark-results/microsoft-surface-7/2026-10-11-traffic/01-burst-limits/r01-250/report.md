# Benchmark: microsoft-surface-7 · burst-limits · 250 hosts · round 1

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `20c8b9e23b2c` · bench
- **Environment fingerprint:** `80bcc0f7cf6416d6093c854bced92b36fd9c47bcd0cf66b50bbcf2bab60c304b`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 250 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1120.0 of 16605.5 MB used (6.8%) · host CPU 9.7% · Docker processes 470.4 MB · Docker's disk 13.3% used
- **Outcome:** 0 of 10 cells passed (10 degraded) · 2026-10-11T11:58:10 → 2026-10-11T12:51:50

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 250 | 1 | 268 | 267 | 621.5 | 9.24 | 288.0 | 23.5 | 31.8 | 1.1 / 1.1 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 62.4% | 61.6% | 60.7% | 59.8% | 61.3% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 0.0% | 26.5% | 1.2% | 0.0% | 24.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 433.1 | 446.7 | 410.2 | 424.5 | 436.3 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 15506 | 17407 | 17696 | 17343 | 17844 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 71.5 | 71.9 | 71.2 | 71.3 | 69.6 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 5.41 | 5.49 | 5.42 | 5.43 | 5.43 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 37.8% | 40.6% | 43.4% | 46.5% | 49.2% |
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
| 500K | 52.53 | 24.16 | 18.45 | 10.96 | 7.66 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 52.72 | 50.99 | 45.26 | 42.66 | 36.72 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 77.5 | 77.0 | 75.0 | 73.9 | 75.9 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 5.90 | 5.97 | 5.79 | 5.75 | 5.91 |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·250K·1000ms` | 250 | 62.50 | 59.8% | 0.0% | 424.5 | – | – | 10.2 → 81.6 | 5.43 | degraded: delivered 59.8% of what was asked (< 95%) |
| 2 | `cs·tcp·250K·500ms` | 250 | 62.50 | 60.7% | 1.2% | 410.2 | – | – | 10.1 → 81.2 | 5.42 | degraded: delivered 60.7% of what was asked (< 95%) |
| 3 | `cs·udp·500K·250ms` | 250 | 125.00 | 40.6% | 0.0% | – | 24.16 | 50.99 | 10.3 → 87.3 | 5.97 | degraded: delivered 40.6% of what was asked (< 95%) |
| 4 | `cs·tcp·250K·250ms` | 250 | 62.50 | 61.6% | 26.5% | 446.7 | – | – | 10.0 → 81.9 | 5.49 | degraded: delivered 61.6% of what was asked (< 95%) |
| 5 | `cs·udp·500K·2000ms` | 250 | 125.00 | 49.2% | 0.0% | – | 7.66 | 36.72 | 10.1 → 86.0 | 5.91 | degraded: delivered 49.2% of what was asked (< 95%) |
| 6 | `cs·udp·500K·100ms` | 250 | 125.00 | 37.8% | 0.0% | – | 52.53 | 52.72 | 9.8 → 87.3 | 5.90 | degraded: delivered 37.8% of what was asked (< 95%) |
| 7 | `cs·udp·500K·1000ms` | 250 | 125.00 | 46.5% | 0.0% | – | 10.96 | 42.66 | 9.9 → 83.8 | 5.75 | degraded: delivered 46.5% of what was asked (< 95%) |
| 8 | `cs·tcp·250K·100ms` | 250 | 62.50 | 62.4% | 0.0% | 433.1 | – | – | 9.8 → 81.3 | 5.41 | degraded: delivered 62.4% of what was asked (< 95%) |
| 9 | `cs·tcp·250K·2000ms` | 250 | 62.50 | 61.3% | 24.0% | 436.3 | – | – | 11.3 → 81.0 | 5.43 | degraded: delivered 61.3% of what was asked (< 95%) |
| 10 | `cs·udp·500K·500ms` | 250 | 125.00 | 43.4% | 0.0% | – | 18.45 | 45.26 | 9.7 → 84.7 | 5.79 | degraded: delivered 43.4% of what was asked (< 95%) |

Per image at 250 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 265 | 1.1 | 96.3% | – |
| `kathara/frr` | 3 | 3.7 | 3.7% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
