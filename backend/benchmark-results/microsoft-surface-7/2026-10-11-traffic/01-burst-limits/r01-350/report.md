# Benchmark: microsoft-surface-7 · burst-limits · 350 hosts · round 1

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `20c8b9e23b2c` · bench
- **Environment fingerprint:** `9d1d80259b4d11604209020eb2d6b0c309851a14861348436d5c06679e0ee5b5`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 5 cells on one deployment of 350 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1049.6 of 16605.5 MB used (6.3%) · host CPU 8.5% · Docker processes 379.0 MB · Docker's disk 13.3% used
- **Outcome:** 1 of 5 cells passed (4 degraded) · 2026-10-11T12:54:06 → 2026-10-11T15:12:32

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 350 | 1 | 372 | 371 | 1083.5 | 15.60 | 513.5 | 26.7 | 35.1 | 1.1 / 1.1 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 5 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 79.9% | 79.0% | 90.2% | 95.1% | 87.2% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 15.0% | 11.0% | 20.0% | 23.3% | 0.0% |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 7853.8 | 6921.7 | 5371.3 | 4590.1 | 6138.5 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 606 | 1001 | 976 | 981 | 654 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 72.5 | 77.0 | 75.1 | 75.3 | 72.1 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | 5.37 | 5.75 | 5.64 | 5.70 | 5.54 |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·250K·250ms` | 700 | 175.00 | 79.0% | 11.0% | 6921.7 | – | – | 13.5 → 90.5 | 5.75 | degraded: delivered 79.0% of what was asked (< 95%) |
| 2 | `mesh·tcp·250K·2000ms` | 700 | 175.00 | 87.2% | 0.0% | 6138.5 | – | – | 14.4 → 86.5 | 5.54 | degraded: delivered 87.2% of what was asked (< 95%) |
| 3 | `mesh·tcp·250K·100ms` | 700 | 175.00 | 79.9% | 15.0% | 7853.8 | – | – | 14.2 → 86.7 | 5.37 | degraded: delivered 79.9% of what was asked (< 95%) |
| 4 | `mesh·tcp·250K·500ms` | 700 | 175.00 | 90.2% | 20.0% | 5371.3 | – | – | 13.0 → 88.2 | 5.64 | degraded: delivered 90.2% of what was asked (< 95%) |
| 5 | `mesh·tcp·250K·1000ms` | 700 | 175.00 | 95.1% | 23.3% | 4590.1 | – | – | 12.4 → 87.7 | 5.70 | ok |

Per image at 350 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 369 | 1.1 | 97.3% | – |
| `kathara/frr` | 3 | 3.7 | 2.7% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
