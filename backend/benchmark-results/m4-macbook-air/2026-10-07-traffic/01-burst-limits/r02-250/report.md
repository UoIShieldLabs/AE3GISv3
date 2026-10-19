# Benchmark: m4-macbook-air · burst-limits · 250 hosts · round 2

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 8 cells on one deployment of 250 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 968.3 of 16746.1 MB used (5.8%) · host CPU 0.8% · Docker processes 273.0 MB · Docker's disk 69.8% used
- **Outcome:** 0 of 8 cells passed (8 degraded) · 2026-10-08T05:47:52 → 2026-10-08T06:11:11

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 250 | 1 | 268 | 267 | 39.8 | 2.90 | 40.3 | 12.9 | 15.6 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 8 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 87.9% | 77.3% | 93.6% | 84.6% | 90.6% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 34.7% | 27.0% | 42.0% | 46.7% | 48.0% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 5927.5 | 8832.4 | 2964.5 | 7068.3 | 3986.1 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 2136 | 1955 | 1355 | 660 | 2016 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 96.7 | 98.3 | 95.9 | 96.5 | 96.9 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 6.98 | 7.18 | 7.08 | 7.15 | 7.18 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | 69.9% | 71.3% | 72.8% |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | 0.0% | 34.6% | 34.9% |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | 25.16 | 25.60 | 22.01 |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | 11.73 | 11.04 | 10.90 |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | 97.2 | 97.1 | 97.7 |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | 7.08 | 7.14 | 7.19 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·500K·250ms` | 500 | 250.00 | 77.3% | 27.0% | 8832.4 | – | – | 1.4 → 99.7 | 7.18 | degraded: delivered 77.3% of what was asked (< 95%) |
| 2 | `mesh·udp·1M·500ms` | 500 | 500.00 | 69.9% | 0.0% | – | 25.16 | 11.73 | 1.6 → 98.8 | 7.08 | degraded: delivered 69.9% of what was asked (< 95%) |
| 3 | `mesh·tcp·500K·1000ms` | 500 | 250.00 | 84.6% | 46.7% | 7068.3 | – | – | 1.6 → 98.1 | 7.15 | degraded: delivered 84.6% of what was asked (< 95%) |
| 4 | `mesh·tcp·500K·2000ms` | 500 | 250.00 | 90.6% | 48.0% | 3986.1 | – | – | 1.5 → 98.4 | 7.18 | degraded: delivered 90.6% of what was asked (< 95%) |
| 5 | `mesh·tcp·500K·100ms` | 500 | 250.00 | 87.9% | 34.7% | 5927.5 | – | – | 1.5 → 98.2 | 6.98 | degraded: delivered 87.9% of what was asked (< 95%) |
| 6 | `mesh·tcp·500K·500ms` | 500 | 250.00 | 93.6% | 42.0% | 2964.5 | – | – | 1.8 → 97.7 | 7.08 | degraded: delivered 93.6% of what was asked (< 95%) |
| 7 | `mesh·udp·1M·1000ms` | 500 | 500.00 | 71.3% | 34.6% | – | 25.60 | 11.04 | 1.6 → 98.7 | 7.14 | degraded: delivered 71.3% of what was asked (< 95%) |
| 8 | `mesh·udp·1M·2000ms` | 500 | 500.00 | 72.8% | 34.9% | – | 22.01 | 10.90 | 1.5 → 99.2 | 7.19 | degraded: delivered 72.8% of what was asked (< 95%) |

Per image at 250 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 265 | 1.2 | 98.9% | – |
| `kathara/frr` | 3 | 1.3 | 1.1% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
