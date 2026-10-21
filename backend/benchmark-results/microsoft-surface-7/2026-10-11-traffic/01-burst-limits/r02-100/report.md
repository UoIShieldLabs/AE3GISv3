# Benchmark: microsoft-surface-7 · burst-limits · 100 hosts · round 2

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `20c8b9e23b2c` · bench
- **Environment fingerprint:** `a02b71cc44f28564a30fb3a1573607c1e92ebc5eb806ee5b1065b52b94a52663`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 100 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1060.5 of 16605.5 MB used (6.4%) · host CPU 10.8% · Docker processes 409.5 MB · Docker's disk 13.4% used
- **Outcome:** 5 of 10 cells passed (5 degraded) · 2026-10-11T21:27:54 → 2026-10-11T21:55:04

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | 1 | 109 | 108 | 149.3 | 4.33 | 56.3 | 23.8 | 31.7 | 1.2 / 1.1 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 99.8% | 99.8% | 100.1% | 98.6% | 100.0% |
| 1M | 53.1% | 53.0% | 52.2% | 51.3% | 50.8% |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 94.4% | 95.0% | 98.0% | 72.0% | 100.0% |
| 1M | 27.6% | 29.5% | 27.0% | 26.0% | 23.0% |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 332.7 | 225.4 | 216.5 | 370.4 | 299.2 |
| 1M | 318.0 | 398.8 | 359.6 | 370.1 | 340.9 |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 5853 | 4030 | 2108 | 7325 | 4538 |
| 1M | 9663 | 8266 | 9504 | 9570 | 9088 |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 79.3 | 75.9 | 74.6 | 78.3 | 76.9 |
| 1M | 79.3 | 79.7 | 78.8 | 79.0 | 79.3 |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 5.83 | 5.62 | 5.52 | 5.77 | 5.66 |
| 1M | 5.83 | 5.83 | 5.77 | 5.79 | 5.82 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·500K·1000ms` | 100 | 50.00 | 98.6% | 72.0% | 370.4 | – | – | 5.2 → 83.5 | 5.77 | ok |
| 2 | `cs·tcp·500K·500ms` | 100 | 50.00 | 100.1% | 98.0% | 216.5 | – | – | 5.0 → 79.6 | 5.52 | ok |
| 3 | `cs·tcp·1M·250ms` | 100 | 100.00 | 53.0% | 29.5% | 398.8 | – | – | 5.2 → 84.8 | 5.83 | degraded: delivered 53.0% of what was asked (< 95%) |
| 4 | `cs·tcp·500K·250ms` | 100 | 50.00 | 99.8% | 95.0% | 225.4 | – | – | 5.2 → 81.2 | 5.62 | ok |
| 5 | `cs·tcp·1M·2000ms` | 100 | 100.00 | 50.8% | 23.0% | 340.9 | – | – | 5.3 → 84.6 | 5.82 | degraded: delivered 50.8% of what was asked (< 95%) |
| 6 | `cs·tcp·1M·100ms` | 100 | 100.00 | 53.1% | 27.6% | 318.0 | – | – | 5.1 → 84.4 | 5.83 | degraded: delivered 53.1% of what was asked (< 95%) |
| 7 | `cs·tcp·1M·1000ms` | 100 | 100.00 | 51.3% | 26.0% | 370.1 | – | – | 5.2 → 84.2 | 5.79 | degraded: delivered 51.3% of what was asked (< 95%) |
| 8 | `cs·tcp·500K·100ms` | 100 | 50.00 | 99.8% | 94.4% | 332.7 | – | – | 5.4 → 84.7 | 5.83 | ok |
| 9 | `cs·tcp·500K·2000ms` | 100 | 50.00 | 100.0% | 100.0% | 299.2 | – | – | 5.1 → 82.0 | 5.66 | ok |
| 10 | `cs·tcp·1M·500ms` | 100 | 100.00 | 52.2% | 27.0% | 359.6 | – | – | 5.1 → 83.9 | 5.77 | degraded: delivered 52.2% of what was asked (< 95%) |

Per image at 100 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 107 | 1.1 | 92.4% | – |
| `kathara/frr` | 2 | 5.0 | 7.6% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
