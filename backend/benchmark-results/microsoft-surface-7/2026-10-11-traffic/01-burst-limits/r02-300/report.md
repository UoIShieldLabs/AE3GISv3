# Benchmark: microsoft-surface-7 · burst-limits · 300 hosts · round 2

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `20c8b9e23b2c` · bench
- **Environment fingerprint:** `80bcc0f7cf6416d6093c854bced92b36fd9c47bcd0cf66b50bbcf2bab60c304b`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 5 cells on one deployment of 300 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1109.4 of 16605.5 MB used (6.7%) · host CPU 9.9% · Docker processes 463.5 MB · Docker's disk 13.4% used
- **Outcome:** 0 of 5 cells passed (5 degraded) · 2026-10-11T23:50:47 → 2026-10-12T01:14:38

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 300 | 1 | 320 | 319 | 923.2 | 12.15 | 468.6 | 25.2 | 33.4 | 1.1 / 1.1 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 5 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 69.8% | 74.8% | 87.6% | 94.9% | 93.3% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 0.0% | 32.6% | 36.5% | 50.3% | 50.0% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 52.84 | 51.10 | 45.60 | 41.58 | 40.71 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 1.78 | 2.52 | 1.72 | 0.21 | 0.35 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 80.2 | 81.8 | 82.0 | 78.8 | 81.5 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 5.81 | 6.12 | 6.20 | 5.98 | 6.27 |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·udp·500K·250ms` | 600 | 300.00 | 74.8% | 32.6% | – | 51.10 | 2.52 | 12.3 → 94.1 | 6.12 | degraded: delivered 74.8% of what was asked (< 95%) |
| 2 | `mesh·udp·500K·2000ms` | 600 | 300.00 | 93.3% | 50.0% | – | 40.71 | 0.35 | 12.6 → 94.1 | 6.27 | degraded: delivered 93.3% of what was asked (< 95%) |
| 3 | `mesh·udp·500K·100ms` | 600 | 300.00 | 69.8% | 0.0% | – | 52.84 | 1.78 | 11.6 → 91.8 | 5.81 | degraded: delivered 69.8% of what was asked (< 95%) |
| 4 | `mesh·udp·500K·500ms` | 600 | 300.00 | 87.6% | 36.5% | – | 45.60 | 1.72 | 12.3 → 94.3 | 6.20 | degraded: delivered 87.6% of what was asked (< 95%) |
| 5 | `mesh·udp·500K·1000ms` | 600 | 300.00 | 94.9% | 50.3% | – | 41.58 | 0.21 | 11.9 → 90.8 | 5.98 | degraded: delivered 94.9% of what was asked (< 95%) |

Per image at 300 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 317 | 1.1 | 96.9% | – |
| `kathara/frr` | 3 | 3.7 | 3.1% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
