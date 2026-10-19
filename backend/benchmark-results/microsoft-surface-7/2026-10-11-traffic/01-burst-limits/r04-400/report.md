# Benchmark: microsoft-surface-7 · burst-limits · 400 hosts · round 4

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `f6638a8abd99` · bench
- **Environment fingerprint:** `35ffbf9e79e8826491c22ff6c473b23bcd00e104d4b9f8bb6fd617afa3d87d28`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 21 cells on one deployment of 400 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1042.8 of 16605.5 MB used (6.3%) · host CPU 17.0% · Docker processes 398.0 MB · Docker's disk 13.4% used
- **Outcome:** 12 of 21 cells passed (9 degraded) · 2026-10-12T19:40:23 → 2026-10-12T22:05:54

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 400 | 1 | 424 | 423 | 1570.8 | 24.86 | 794.7 | – | – | – / – | – | – | – | – | – | – | – | ok |

Traffic matrix: 21 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 98.8% | 97.8% | 100.3% | 99.9% | 100.0% |
| 100K | 83.5% | 80.0% | 80.0% | 85.6% | 81.4% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 93.0% | 87.5% | 92.5% | 95.0% | 99.9% |
| 100K | 0.0% | 10.5% | 17.5% | 0.0% | 0.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 299.7 | 341.1 | 325.2 | 204.3 | 139.8 |
| 100K | 492.0 | 494.3 | 475.9 | 439.1 | 605.8 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 1186 | 4623 | 6051 | 4179 | 1833 |
| 100K | 14205 | 16631 | 16646 | 17106 | 14794 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 61.8 | 62.8 | 59.4 | 54.9 | 52.9 |
| 100K | 62.9 | 63.8 | 62.6 | 63.2 | 60.2 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.96 | 4.99 | 4.84 | 4.64 | 4.47 |
| 100K | 5.12 | 5.09 | 5.12 | 5.12 | 5.02 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 95.2% | 98.2% | 100.0% | 100.0% | 100.0% |
| 100K | 94.0% | 87.0% | 95.0% | 96.0% | 99.2% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.0% | 0.0% | 98.0% | 98.8% | 98.9% |
| 100K | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 28.84 | 10.00 | 8.79 | 4.96 | 2.83 |
| 100K | 22.32 | 17.65 | 12.19 | 7.05 | 3.09 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 2.97 | 0.21 | 0.06 | 0.00 | 0.00 |
| 100K | 1.25 | 4.52 | 0.74 | 0.51 | 0.25 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 56.9 | 47.6 | 49.2 | 42.8 | 41.3 |
| 100K | 57.3 | 59.5 | 55.9 | 53.4 | 51.7 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.57 | 4.38 | 4.11 | 3.77 | 3.69 |
| 100K | 4.67 | 4.79 | 4.68 | 4.50 | 4.53 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | 62.7% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | 0.0% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | 7865.5 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | 1270 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | 71.4 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | 5.54 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·100K·250ms` | 400 | 40.00 | 80.0% | 10.5% | 494.3 | – | – | 14.6 → 78.5 | 5.09 | degraded: delivered 80.0% of what was asked (< 95%) |
| 2 | `cs·udp·100K·100ms` | 400 | 40.00 | 94.0% | 0.0% | – | 22.32 | 1.25 | 17.1 → 74.4 | 4.67 | degraded: delivered 94.0% of what was asked (< 95%) |
| 3 | `cs·tcp·50K·250ms` | 400 | 20.00 | 97.8% | 87.5% | 341.1 | – | – | 15.5 → 78.3 | 4.99 | ok |
| 4 | `cs·udp·100K·2000ms` | 400 | 40.00 | 99.2% | 0.0% | – | 3.09 | 0.25 | 17.3 → 69.0 | 4.53 | ok |
| 5 | `mesh·tcp·250K·1000ms` | 800 | 200.00 | 62.7% | 0.0% | 7865.5 | – | – | 16.2 → 87.6 | 5.54 | degraded: delivered 62.7% of what was asked (< 95%) |
| 6 | `cs·tcp·100K·500ms` | 400 | 40.00 | 80.0% | 17.5% | 475.9 | – | – | 16.2 → 78.8 | 5.12 | degraded: delivered 80.0% of what was asked (< 95%) |
| 7 | `cs·udp·100K·250ms` | 400 | 40.00 | 87.0% | 0.0% | – | 17.65 | 4.52 | 15.2 → 74.8 | 4.79 | degraded: delivered 87.0% of what was asked (< 95%) |
| 8 | `cs·udp·50K·250ms` | 400 | 20.00 | 98.2% | 0.0% | – | 10.00 | 0.21 | 21.2 → 68.8 | 4.38 | ok |
| 9 | `cs·udp·50K·100ms` | 400 | 20.00 | 95.2% | 0.0% | – | 28.84 | 2.97 | 16.7 → 73.5 | 4.57 | degraded: UDP loss 2.97% > 1.0% |
| 10 | `cs·tcp·100K·100ms` | 400 | 40.00 | 83.5% | 0.0% | 492.0 | – | – | 16.9 → 79.7 | 5.12 | degraded: delivered 83.5% of what was asked (< 95%) |
| 11 | `cs·tcp·50K·1000ms` | 400 | 20.00 | 99.9% | 95.0% | 204.3 | – | – | 16.8 → 71.7 | 4.64 | ok |
| 12 | `cs·udp·50K·500ms` | 400 | 20.00 | 100.0% | 98.0% | – | 8.79 | 0.06 | 15.4 → 64.6 | 4.11 | ok |
| 13 | `cs·udp·50K·1000ms` | 400 | 20.00 | 100.0% | 98.8% | – | 4.96 | 0.00 | 16.4 → 59.2 | 3.77 | ok |
| 14 | `cs·tcp·100K·1000ms` | 400 | 40.00 | 85.6% | 0.0% | 439.1 | – | – | 16.0 → 79.3 | 5.12 | degraded: delivered 85.6% of what was asked (< 95%) |
| 15 | `cs·udp·100K·1000ms` | 400 | 40.00 | 96.0% | 0.0% | – | 7.05 | 0.51 | 15.4 → 68.8 | 4.50 | ok |
| 16 | `cs·tcp·50K·2000ms` | 400 | 20.00 | 100.0% | 99.9% | 139.8 | – | – | 15.6 → 68.4 | 4.47 | ok |
| 17 | `cs·tcp·50K·500ms` | 400 | 20.00 | 100.3% | 92.5% | 325.2 | – | – | 16.2 → 75.6 | 4.84 | ok |
| 18 | `cs·udp·100K·500ms` | 400 | 40.00 | 95.0% | 0.0% | – | 12.19 | 0.74 | 16.2 → 72.1 | 4.68 | ok |
| 19 | `cs·tcp·50K·100ms` | 400 | 20.00 | 98.8% | 93.0% | 299.7 | – | – | 16.1 → 77.8 | 4.96 | ok |
| 20 | `cs·tcp·100K·2000ms` | 400 | 40.00 | 81.4% | 0.0% | 605.8 | – | – | 16.3 → 76.5 | 5.02 | degraded: delivered 81.4% of what was asked (< 95%) |
| 21 | `cs·udp·50K·2000ms` | 400 | 20.00 | 100.0% | 98.9% | – | 2.83 | 0.00 | 16.2 → 57.5 | 3.69 | ok |

Per image at 400 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | – | – | – | – |
| `kathara/frr` | – | – | – | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
