# Benchmark: m4-macbook-air · burst-limits · 500 hosts · round 4

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `9f7bf000d83f` · bench
- **Environment fingerprint:** `8affbcfb7a1aea9104133f89048bbe26c107bbcd5ce1d1fe18845c01d1422c86`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 7 cells on one deployment of 500 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 983.8 of 16746.1 MB used (5.9%) · host CPU 0.8% · Docker processes 274.5 MB · Docker's disk 72.5% used
- **Outcome:** 4 of 7 cells passed (3 degraded) · 2026-10-09T04:20:56 → 2026-10-09T04:50:43

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 500 | 1 | 531 | 530 | 109.5 | 5.55 | 88.8 | 13.0 | 15.6 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 7 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | 73.5% | 67.9% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | 15.3% | 0.0% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | 8456.0 | 9585.2 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | 1213 | 1245 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | 85.0 | 89.8 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | 5.95 | 6.05 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | 99.8% | 101.0% | – | – |
| 250K | 94.2% | 100.3% | 100.7% | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | 99.4% | 98.8% | – | – |
| 250K | 0.0% | 98.1% | 97.5% | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | 0.22 | 0.18 | – | – |
| 250K | 59.08 | 8.03 | 6.33 | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | 0.00 | 0.00 | – | – |
| 250K | 0.10 | 0.00 | 0.00 | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | 33.8 | 27.3 | – | – |
| 250K | 81.9 | 64.1 | 65.0 | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | 1.94 | 1.57 | – | – |
| 250K | 5.48 | 4.11 | 4.26 | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·250K·1000ms` | 1000 | 250.00 | 67.9% | 0.0% | 9585.2 | – | – | 3.4 → 93.2 | 6.05 | degraded: delivered 67.9% of what was asked (< 95%) |
| 2 | `mesh·udp·250K·500ms` | 1000 | 250.00 | 100.7% | 97.5% | – | 6.33 | 0.00 | 4.5 → 69.5 | 4.26 | ok |
| 3 | `mesh·udp·250K·100ms` | 1000 | 250.00 | 94.2% | 0.0% | – | 59.08 | 0.10 | 4.7 → 86.6 | 5.48 | degraded: delivered 94.2% of what was asked (< 95%) |
| 4 | `mesh·tcp·250K·500ms` | 1000 | 250.00 | 73.5% | 15.3% | 8456.0 | – | – | 4.6 → 89.6 | 5.95 | degraded: delivered 73.5% of what was asked (< 95%) |
| 5 | `mesh·udp·100K·250ms` | 1000 | 100.00 | 99.8% | 99.4% | – | 0.22 | 0.00 | 5.1 → 38.8 | 1.94 | ok |
| 6 | `mesh·udp·100K·500ms` | 1000 | 100.00 | 101.0% | 98.8% | – | 0.18 | 0.00 | 5.0 → 32.2 | 1.57 | ok |
| 7 | `mesh·udp·250K·250ms` | 1000 | 250.00 | 100.3% | 98.1% | – | 8.03 | 0.00 | 4.3 → 68.5 | 4.11 | ok |

Per image at 500 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 527 | 1.2 | 99.2% | – |
| `kathara/frr` | 4 | 1.3 | 0.8% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
