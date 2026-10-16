# Benchmark: m4max-studio-dd12-95g · burst-limits · 200 hosts · round 1

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 200 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1995.0 of 101850.2 MB used (2.0%) · host CPU 9.8% · Docker processes 333.8 MB · Docker's disk 8.6% used
- **Outcome:** 5 of 10 cells passed (5 degraded) · 2026-10-11T14:39:12 → 2026-10-11T15:03:51

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 200 | 1 | 213 | 212 | 28.2 | 0.76 | 26.5 | 13.4 | 16.1 | 1.3 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 100.1% | 99.9% | 100.1% | 100.3% | 100.7% |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 99.7% | 93.0% | 99.0% | 98.0% | 98.0% |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 104.2 | 225.7 | 13.1 | 6.1 | 6.2 |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 4715 | 7752 | 0 | 0 | 0 |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 64.6 | 65.2 | 63.6 | 59.2 | 55.8 |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 5.99 | 6.17 | 6.06 | 5.54 | 5.22 |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 93.0% | 91.7% | 93.0% | 92.8% | 91.9% |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 63.7% | 52.4% | 0.0% | 56.4% | 0.0% |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.44 | 0.32 | 0.28 | 0.17 | 0.15 |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 6.73 | 8.26 | 6.63 | 7.16 | 7.13 |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 64.6 | 63.5 | 62.0 | 62.1 | 62.5 |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 6.26 | 6.25 | 6.13 | 6.15 | 6.08 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·500K·1000ms` | 200 | 100.00 | 100.3% | 98.0% | 6.1 | – | – | 2.3 → 61.5 | 5.54 | ok |
| 2 | `cs·tcp·500K·500ms` | 200 | 100.00 | 100.1% | 99.0% | 13.1 | – | – | 2.3 → 66.0 | 6.06 | ok |
| 3 | `cs·udp·1M·250ms` | 200 | 200.00 | 91.7% | 52.4% | – | 0.32 | 8.26 | 2.2 → 65.7 | 6.25 | degraded: delivered 91.7% of what was asked (< 95%) |
| 4 | `cs·tcp·500K·250ms` | 200 | 100.00 | 99.9% | 93.0% | 225.7 | – | – | 2.2 → 67.4 | 6.17 | ok |
| 5 | `cs·udp·1M·2000ms` | 200 | 200.00 | 91.9% | 0.0% | – | 0.15 | 7.13 | 2.2 → 64.8 | 6.08 | degraded: delivered 91.9% of what was asked (< 95%) |
| 6 | `cs·udp·1M·100ms` | 200 | 200.00 | 93.0% | 63.7% | – | 0.44 | 6.73 | 2.2 → 66.8 | 6.26 | degraded: delivered 93.0% of what was asked (< 95%) |
| 7 | `cs·udp·1M·1000ms` | 200 | 200.00 | 92.8% | 56.4% | – | 0.17 | 7.16 | 2.3 → 64.4 | 6.15 | degraded: delivered 92.8% of what was asked (< 95%) |
| 8 | `cs·tcp·500K·100ms` | 200 | 100.00 | 100.1% | 99.7% | 104.2 | – | – | 2.3 → 66.9 | 5.99 | ok |
| 9 | `cs·tcp·500K·2000ms` | 200 | 100.00 | 100.7% | 98.0% | 6.2 | – | – | 2.3 → 58.1 | 5.22 | ok |
| 10 | `cs·udp·1M·500ms` | 200 | 200.00 | 93.0% | 0.0% | – | 0.28 | 6.63 | 2.2 → 64.2 | 6.13 | degraded: delivered 93.0% of what was asked (< 95%) |

Per image at 200 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 211 | 1.3 | 99.0% | – |
| `kathara/frr` | 2 | 1.3 | 1.0% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
