# Benchmark: m4-macbook-air · burst-limits · 550 hosts · round 4

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `9f7bf000d83f` · bench
- **Environment fingerprint:** `8affbcfb7a1aea9104133f89048bbe26c107bbcd5ce1d1fe18845c01d1422c86`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 5 cells on one deployment of 550 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 947.7 of 16746.1 MB used (5.7%) · host CPU 0.8% · Docker processes 270.1 MB · Docker's disk 72.7% used
- **Outcome:** 3 of 5 cells passed (2 degraded) · 2026-10-09T04:51:33 → 2026-10-09T05:19:38

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 550 | 1 | 583 | 582 | 144.3 | 6.55 | 138.8 | 13.1 | 15.7 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 5 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 96.1% | 93.0% | 96.4% | 88.8% | 95.3% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 65.6% | 68.7% | 69.0% | 56.0% | 60.0% |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 267.6 | 260.7 | 239.6 | 285.4 | 252.3 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 27498 | 35113 | 32912 | 27439 | 18150 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 82.7 | 84.6 | 79.9 | 79.8 | 79.6 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 5.92 | 6.09 | 5.80 | 5.71 | 5.75 |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·100K·250ms` | 550 | 55.00 | 93.0% | 68.7% | 260.7 | – | – | 4.1 → 88.7 | 6.09 | degraded: delivered 93.0% of what was asked (< 95%) |
| 2 | `cs·tcp·100K·2000ms` | 550 | 55.00 | 95.3% | 60.0% | 252.3 | – | – | 4.2 → 83.8 | 5.75 | ok |
| 3 | `cs·tcp·100K·100ms` | 550 | 55.00 | 96.1% | 65.6% | 267.6 | – | – | 4.8 → 87.5 | 5.92 | ok |
| 4 | `cs·tcp·100K·500ms` | 550 | 55.00 | 96.4% | 69.0% | 239.6 | – | – | 4.7 → 84.6 | 5.80 | ok |
| 5 | `cs·tcp·100K·1000ms` | 550 | 55.00 | 88.8% | 56.0% | 285.4 | – | – | 4.1 → 83.9 | 5.71 | degraded: delivered 88.8% of what was asked (< 95%) |

Per image at 550 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 579 | 1.2 | 98.7% | – |
| `kathara/frr` | 4 | 2.3 | 1.3% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
