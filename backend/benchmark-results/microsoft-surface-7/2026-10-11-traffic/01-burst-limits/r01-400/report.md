# Benchmark: microsoft-surface-7 · burst-limits · 400 hosts · round 1

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `20c8b9e23b2c` · bench
- **Environment fingerprint:** `9d1d80259b4d11604209020eb2d6b0c309851a14861348436d5c06679e0ee5b5`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 5 cells on one deployment of 400 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1060.2 of 16605.5 MB used (6.4%) · host CPU 8.6% · Docker processes 383.4 MB · Docker's disk 13.3% used
- **Outcome:** 0 of 5 cells passed (5 degraded) · 2026-10-11T15:14:47 → 2026-10-11T17:40:55

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 400 | 1 | 424 | 423 | 1351.3 | 24.39 | 684.5 | – | – | – / – | – | – | – | – | – | – | – | ok |

Traffic matrix: 5 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 51.9% | 48.8% | 61.2% | 63.4% | 65.3% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 69.15 | 80.98 | 59.25 | 58.14 | 56.91 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 1.08 | 1.48 | 1.54 | 1.00 | 0.94 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 75.1 | 73.3 | 74.6 | 68.3 | 70.4 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 5.47 | 5.54 | 5.65 | 5.42 | 5.41 |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·udp·500K·250ms` | 800 | 400.00 | 48.8% | 0.0% | – | 80.98 | 1.48 | 15.3 → 88.6 | 5.54 | degraded: delivered 48.8% of what was asked (< 95%) |
| 2 | `mesh·udp·500K·2000ms` | 800 | 400.00 | 65.3% | 0.0% | – | 56.91 | 0.94 | 14.8 → 85.3 | 5.41 | degraded: delivered 65.3% of what was asked (< 95%) |
| 3 | `mesh·udp·500K·100ms` | 800 | 400.00 | 51.9% | 0.0% | – | 69.15 | 1.08 | 14.2 → 89.3 | 5.47 | degraded: delivered 51.9% of what was asked (< 95%) |
| 4 | `mesh·udp·500K·500ms` | 800 | 400.00 | 61.2% | 0.0% | – | 59.25 | 1.54 | 14.6 → 89.2 | 5.65 | degraded: delivered 61.2% of what was asked (< 95%) |
| 5 | `mesh·udp·500K·1000ms` | 800 | 400.00 | 63.4% | 0.0% | – | 58.14 | 1.00 | 17.4 → 85.7 | 5.42 | degraded: delivered 63.4% of what was asked (< 95%) |

Per image at 400 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | – | – | – | – |
| `kathara/frr` | – | – | – | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
