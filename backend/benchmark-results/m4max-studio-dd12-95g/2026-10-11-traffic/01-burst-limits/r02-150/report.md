# Benchmark: m4max-studio-dd12-95g · burst-limits · 150 hosts · round 2

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 10 cells on one deployment of 150 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1986.9 of 101850.2 MB used (1.9%) · host CPU 9.8% · Docker processes 340.4 MB · Docker's disk 8.6% used
- **Outcome:** 5 of 10 cells passed (5 degraded) · 2026-10-11T21:01:11 → 2026-10-11T21:25:06

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 150 | 1 | 161 | 160 | 21.4 | 0.48 | 19.3 | 14.1 | 16.1 | 1.3 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 10 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 81.3% | 81.8% | 80.7% | 82.1% | 82.8% |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 61.3% | 65.4% | 45.0% | 63.3% | 61.7% |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 214.2 | 132.6 | 250.2 | 178.7 | 193.4 |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 9414 | 16482 | 11143 | 13490 | 10043 |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 65.8 | 66.1 | 65.8 | 65.5 | 66.0 |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 6.27 | 6.26 | 6.25 | 6.25 | 6.26 |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 100.2% | 100.0% | 100.2% | 100.2% | 100.0% |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 99.8% | 99.7% | 99.0% | 99.2% | 99.8% |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.47 | 0.43 | 0.59 | 0.96 | 0.35 |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 55.7 | 55.1 | 53.6 | 52.7 | 52.3 |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 5.09 | 5.10 | 4.99 | 4.97 | 4.95 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·1M·1000ms` | 150 | 150.00 | 82.1% | 63.3% | 178.7 | – | – | 1.8 → 67.4 | 6.25 | degraded: delivered 82.1% of what was asked (< 95%) |
| 2 | `cs·tcp·1M·500ms` | 150 | 150.00 | 80.7% | 45.0% | 250.2 | – | – | 1.9 → 67.7 | 6.25 | degraded: delivered 80.7% of what was asked (< 95%) |
| 3 | `cs·udp·1M·250ms` | 150 | 150.00 | 100.0% | 99.7% | – | 0.43 | 0.00 | 1.8 → 56.9 | 5.10 | ok |
| 4 | `cs·tcp·1M·250ms` | 150 | 150.00 | 81.8% | 65.4% | 132.6 | – | – | 1.9 → 67.9 | 6.26 | degraded: delivered 81.8% of what was asked (< 95%) |
| 5 | `cs·udp·1M·2000ms` | 150 | 150.00 | 100.0% | 99.8% | – | 0.35 | 0.00 | 1.8 → 54.1 | 4.95 | ok |
| 6 | `cs·udp·1M·100ms` | 150 | 150.00 | 100.2% | 99.8% | – | 0.47 | 0.00 | 1.8 → 57.5 | 5.09 | ok |
| 7 | `cs·udp·1M·1000ms` | 150 | 150.00 | 100.2% | 99.2% | – | 0.96 | 0.00 | 1.8 → 54.5 | 4.97 | ok |
| 8 | `cs·tcp·1M·100ms` | 150 | 150.00 | 81.3% | 61.3% | 214.2 | – | – | 1.8 → 67.7 | 6.27 | degraded: delivered 81.3% of what was asked (< 95%) |
| 9 | `cs·tcp·1M·2000ms` | 150 | 150.00 | 82.8% | 61.7% | 193.4 | – | – | 1.8 → 67.8 | 6.26 | degraded: delivered 82.8% of what was asked (< 95%) |
| 10 | `cs·udp·1M·500ms` | 150 | 150.00 | 100.2% | 99.0% | – | 0.59 | 0.00 | 1.9 → 55.4 | 4.99 | ok |

Per image at 150 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 159 | 1.2 | 95.6% | – |
| `kathara/frr` | 2 | 4.5 | 4.4% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
