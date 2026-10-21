# Benchmark: microsoft-surface-7 · burst-limits · 400 hosts · round 6

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `f6638a8abd99` · bench
- **Environment fingerprint:** `0b6ea01f7920c75dc4dae05dd5654af47479ee38b005cc61413deac517c9e66d`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 12 cells on one deployment of 400 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1145.0 of 16605.5 MB used (6.9%) · host CPU 25.7% · Docker processes 483.2 MB · Docker's disk 13.5% used
- **Outcome:** 10 of 12 cells passed (2 degraded) · 2026-10-13T14:34:04 → 2026-10-13T16:13:11

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 400 | 1 | 424 | 423 | 1512.7 | 26.67 | 764.1 | – | – | – / – | – | – | – | – | – | – | – | ok |

Traffic matrix: 12 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 98.4% | 98.9% | 99.0% | 99.8% | 100.0% |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 74.5% | 78.4% | 86.0% | 95.0% | 99.9% |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 316.8 | 355.1 | 397.9 | 146.2 | 147.0 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 832 | 4978 | 5884 | 3346 | 1698 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 62.2 | 57.5 | 53.4 | 48.6 | 51.0 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 5.02 | 4.95 | 4.68 | 4.59 | 4.40 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 96.8% | 100.0% | 100.0% | 100.0% |
| 100K | – | – | 96.1% | 92.1% | 98.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.0% | 100.0% | 97.5% | 97.2% |
| 100K | – | – | 0.0% | 0.0% | 0.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 16.55 | 8.28 | 4.02 | 3.39 |
| 100K | – | – | 13.73 | 5.02 | 4.22 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.96 | 0.00 | 0.00 | 0.00 |
| 100K | – | – | 1.38 | 0.96 | 0.23 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 52.2 | 46.4 | 43.8 | 42.7 |
| 100K | – | – | 56.5 | 51.6 | 50.5 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 4.39 | 4.13 | 3.87 | 3.87 |
| 100K | – | – | 4.72 | 4.49 | 4.42 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·50K·500ms` | 400 | 20.00 | 99.0% | 86.0% | 397.9 | – | – | 19.2 → 72.6 | 4.68 | ok |
| 2 | `cs·udp·50K·250ms` | 400 | 20.00 | 96.8% | 0.0% | – | 16.55 | 0.96 | 16.2 → 68.4 | 4.39 | ok |
| 3 | `cs·tcp·50K·1000ms` | 400 | 20.00 | 99.8% | 95.0% | 146.2 | – | – | 22.2 → 70.8 | 4.59 | ok |
| 4 | `cs·udp·50K·500ms` | 400 | 20.00 | 100.0% | 100.0% | – | 8.28 | 0.00 | 19.2 → 65.6 | 4.13 | ok |
| 5 | `cs·udp·100K·500ms` | 400 | 40.00 | 96.1% | 0.0% | – | 13.73 | 1.38 | 16.0 → 72.5 | 4.72 | degraded: UDP loss 1.38% > 1.0% |
| 6 | `cs·udp·50K·2000ms` | 400 | 20.00 | 100.0% | 97.2% | – | 3.39 | 0.00 | 16.6 → 59.3 | 3.87 | ok |
| 7 | `cs·udp·100K·1000ms` | 400 | 40.00 | 92.1% | 0.0% | – | 5.02 | 0.96 | 17.6 → 69.2 | 4.49 | degraded: delivered 92.1% of what was asked (< 95%) |
| 8 | `cs·tcp·50K·250ms` | 400 | 20.00 | 98.9% | 78.4% | 355.1 | – | – | 20.0 → 77.5 | 4.95 | ok |
| 9 | `cs·tcp·50K·100ms` | 400 | 20.00 | 98.4% | 74.5% | 316.8 | – | – | 16.8 → 79.1 | 5.02 | ok |
| 10 | `cs·tcp·50K·2000ms` | 400 | 20.00 | 100.0% | 99.9% | 147.0 | – | – | 17.0 → 68.0 | 4.40 | ok |
| 11 | `cs·udp·50K·1000ms` | 400 | 20.00 | 100.0% | 97.5% | – | 4.02 | 0.00 | 16.3 → 60.1 | 3.87 | ok |
| 12 | `cs·udp·100K·2000ms` | 400 | 40.00 | 98.0% | 0.0% | – | 4.22 | 0.23 | 17.3 → 67.8 | 4.42 | ok |

Per image at 400 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | – | – | – | – |
| `kathara/frr` | – | – | – | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
