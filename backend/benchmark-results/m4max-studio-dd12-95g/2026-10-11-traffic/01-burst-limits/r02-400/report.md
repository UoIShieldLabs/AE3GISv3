# Benchmark: m4max-studio-dd12-95g · burst-limits · 400 hosts · round 2

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 11 cells on one deployment of 400 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 1993.4 of 101850.2 MB used (2.0%) · host CPU 9.8% · Docker processes 338.8 MB · Docker's disk 8.6% used
- **Outcome:** 9 of 11 cells passed (2 failed) · 2026-10-11T22:15:05 → 2026-10-11T22:54:02

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 400 | 1 | 424 | 423 | 66.0 | 1.48 | 68.0 | 12.8 | 15.8 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 11 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | 103.9% |
| 500K | 100.1% | 100.3% | 100.6% | 101.2% | 100.8% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | 96.0% |
| 500K | 99.4% | 99.0% | 98.9% | 98.0% | 96.0% |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | 2.1 |
| 500K | 38.5 | 64.8 | 7.7 | 3.8 | 5.2 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | 2 |
| 500K | 18146 | 2873 | 415 | 63 | 8 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | 41.0 |
| 500K | 71.4 | 73.6 | 69.8 | 65.5 | 62.7 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | 3.93 |
| 500K | 7.29 | 7.87 | 7.31 | 6.69 | 6.33 |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 100.1% | 0.0% | 100.6% | 0.0% | 99.8% |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 99.2% | 0.0% | 99.0% | 0.0% | 96.0% |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 3.54 | – | 0.30 | – | 0.78 |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 0.00 | – | 0.00 | – | 0.14 |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 74.8 | 0.1 | 74.5 | -0.1 | 74.4 |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | 7.95 | 0.42 | 8.01 | 0.42 | 7.97 |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·500K·250ms` | 800 | 400.00 | 100.3% | 99.0% | 64.8 | – | – | 4.2 → 77.8 | 7.87 | ok |
| 2 | `mesh·tcp·500K·2000ms` | 800 | 400.00 | 100.8% | 96.0% | 5.2 | – | – | 4.0 → 66.7 | 6.33 | ok |
| 3 | `mesh·tcp·500K·500ms` | 800 | 400.00 | 100.6% | 98.9% | 7.7 | – | – | 4.0 → 73.8 | 7.31 | ok |
| 4 | `mesh·udp·1M·100ms` | 800 | 800.00 | 100.1% | 99.2% | – | 3.54 | 0.00 | 4.0 → 78.9 | 7.95 | ok |
| 5 | `mesh·udp·1M·1000ms` | 800 | 800.00 | 0.0% | 0.0% | – | – | – | 4.1 → 4.0 | 0.42 | failed: RuntimeError: Not running: h1-145, h1-147, h1-149, h1-150, h1-151, h1-155, h1-160 |
| 6 | `mesh·udp·1M·500ms` | 800 | 800.00 | 100.6% | 99.0% | – | 0.30 | 0.00 | 4.0 → 78.5 | 8.01 | ok |
| 7 | `mesh·udp·1M·2000ms` | 800 | 800.00 | 99.8% | 96.0% | – | 0.78 | 0.14 | 4.0 → 78.4 | 7.97 | ok |
| 8 | `mesh·tcp·500K·100ms` | 800 | 400.00 | 100.1% | 99.4% | 38.5 | – | – | 3.9 → 75.3 | 7.29 | ok |
| 9 | `mesh·tcp·250K·2000ms` | 800 | 200.00 | 103.9% | 96.0% | 2.1 | – | – | 4.1 → 45.0 | 3.93 | ok |
| 10 | `mesh·tcp·500K·1000ms` | 800 | 400.00 | 101.2% | 98.0% | 3.8 | – | – | 4.0 → 69.5 | 6.69 | ok |
| 11 | `mesh·udp·1M·250ms` | 800 | 800.00 | 0.0% | 0.0% | – | – | – | 4.0 → 4.0 | 0.42 | failed: RuntimeError: Not running: h1-27, h1-34, h1-35, h1-37, h1-41, h1-43 |

Per image at 400 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 421 | 1.2 | 99.3% | – |
| `kathara/frr` | 3 | 1.3 | 0.7% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
