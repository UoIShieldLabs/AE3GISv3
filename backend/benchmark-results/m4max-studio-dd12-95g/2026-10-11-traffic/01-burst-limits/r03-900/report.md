# Benchmark: m4max-studio-dd12-95g · burst-limits · 900 hosts · round 3

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 29 cells on one deployment of 900 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 2061.9 of 101850.2 MB used (2.0%) · host CPU 9.8% · Docker processes 341.6 MB · Docker's disk 8.7% used
- **Outcome:** 26 of 29 cells passed (1 degraded, 2 failed) · 2026-10-12T15:35:04 → 2026-10-12T20:36:05

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 900 | 1 | 953 | 952 | 218.0 | 3.48 | 339.2 | 13.2 | 15.9 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 29 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 99.9% | 97.1% | 99.0% | 100.0% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 93.5% | 4.0% | 0.0% | 97.5% | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 154.2 | 146.5 | 146.3 | 132.7 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 31782 | 82283 | 66405 | 22984 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 58.3 | 59.2 | 57.8 | 56.0 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 6.13 | 6.25 | 6.05 | 5.96 | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 100.2% | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 99.0% | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 0.74 | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 0.00 | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 42.4 | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | 4.06 | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 101.4% | 102.7% | 105.5% | – |
| 100K | 94.7% | 100.8% | 102.6% | 105.7% | 111.2% |
| 250K | 96.2% | 0.0% | 101.3% | 100.2% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 64.1% | 98.1% | 96.4% | – |
| 100K | 0.0% | 0.0% | 96.9% | 96.4% | 93.3% |
| 250K | 0.0% | 0.0% | 0.0% | 99.0% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.9 | 0.9 | 1.1 | – |
| 100K | 5.8 | 16.1 | 1.8 | 2.8 | 2.3 |
| 250K | 954.2 | – | 392.3 | 144.2 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 341 | 131 | 44 | – |
| 100K | 0 | 4705 | 228 | 113 | 38 |
| 250K | 8678 | 0 | 2585 | 20369 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 30.1 | 24.2 | 22.7 | – |
| 100K | 34.0 | 36.3 | 30.5 | 30.3 | 28.5 |
| 250K | 48.0 | 0.9 | 43.8 | 43.6 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 2.65 | 2.16 | 2.04 | – |
| 100K | 2.95 | 3.42 | 2.80 | 2.81 | 2.67 |
| 250K | 4.70 | 0.90 | 4.46 | 4.40 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 100.0% | 101.3% | 102.4% | 105.6% | – |
| 100K | 100.6% | 101.3% | 100.2% | 105.6% | – |
| 250K | 100.0% | 101.4% | 102.7% | 105.7% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 99.9% | 96.3% | 98.2% | 96.5% | – |
| 100K | 99.5% | 97.3% | 99.8% | 96.5% | – |
| 250K | 99.8% | 97.9% | 97.9% | 96.4% | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.14 | 0.18 | 0.18 | 0.17 | – |
| 100K | 0.32 | 0.22 | 0.13 | 0.17 | – |
| 250K | 18.55 | 0.41 | 0.27 | 0.24 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.00 | 0.00 | 0.00 | 0.00 | – |
| 100K | 0.00 | 0.00 | 0.00 | 0.00 | – |
| 250K | 0.00 | 0.00 | 0.00 | 0.00 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 27.1 | 22.1 | 20.9 | 19.0 | – |
| 100K | 26.4 | 26.2 | 22.6 | 22.4 | – |
| 250K | 39.0 | 35.2 | 33.3 | 35.0 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern mesh · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 2.20 | 1.84 | 1.83 | 1.70 | – |
| 100K | 2.21 | 2.24 | 1.98 | 2.04 | – |
| 250K | 3.55 | 3.25 | 3.10 | 3.34 | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `mesh·tcp·100K·100ms` | 1800 | 180.00 | 94.7% | 0.0% | 5.8 | – | – | 8.0 → 42.0 | 2.95 | degraded: delivered 94.7% of what was asked (< 95%) |
| 2 | `mesh·udp·100K·100ms` | 1800 | 180.00 | 100.6% | 99.5% | – | 0.32 | 0.00 | 8.4 → 34.8 | 2.21 | ok |
| 3 | `mesh·tcp·100K·2000ms` | 1800 | 180.00 | 111.2% | 93.3% | 2.3 | – | – | 8.3 → 36.9 | 2.67 | ok |
| 4 | `mesh·udp·100K·1000ms` | 1800 | 180.00 | 105.6% | 96.5% | – | 0.17 | 0.00 | 8.4 → 30.8 | 2.04 | ok |
| 5 | `mesh·tcp·50K·1000ms` | 1800 | 90.00 | 105.5% | 96.4% | 1.1 | – | – | 8.0 → 30.8 | 2.04 | ok |
| 6 | `mesh·tcp·100K·1000ms` | 1800 | 180.00 | 105.7% | 96.4% | 2.8 | – | – | 8.0 → 38.4 | 2.81 | ok |
| 7 | `mesh·udp·250K·250ms` | 1800 | 450.00 | 101.4% | 97.9% | – | 0.41 | 0.00 | 7.9 → 43.1 | 3.25 | ok |
| 8 | `mesh·udp·250K·500ms` | 1800 | 450.00 | 102.7% | 97.9% | – | 0.27 | 0.00 | 8.0 → 41.2 | 3.10 | ok |
| 9 | `mesh·tcp·100K·500ms` | 1800 | 180.00 | 102.6% | 96.9% | 1.8 | – | – | 8.1 → 38.6 | 2.80 | ok |
| 10 | `mesh·udp·50K·250ms` | 1800 | 90.00 | 101.3% | 96.3% | – | 0.18 | 0.00 | 8.1 → 30.2 | 1.84 | ok |
| 11 | `mesh·tcp·250K·500ms` | 1800 | 450.00 | 101.3% | 0.0% | 392.3 | – | – | 8.3 → 52.1 | 4.46 | ok |
| 12 | `mesh·udp·50K·500ms` | 1800 | 90.00 | 102.4% | 98.2% | – | 0.18 | 0.00 | 8.0 → 28.9 | 1.83 | ok |
| 13 | `mesh·tcp·250K·100ms` | 1800 | 450.00 | 96.2% | 0.0% | 954.2 | – | – | 8.2 → 56.2 | 4.70 | ok |
| 14 | `cs·tcp·100K·1000ms` | 900 | 90.00 | 100.0% | 97.5% | 132.7 | – | – | 7.9 → 63.8 | 5.96 | ok |
| 15 | `mesh·tcp·50K·250ms` | 1800 | 90.00 | 101.4% | 64.1% | 0.9 | – | – | 7.7 → 37.8 | 2.65 | ok |
| 16 | `mesh·tcp·50K·500ms` | 1800 | 90.00 | 102.7% | 98.1% | 0.9 | – | – | 8.1 → 32.3 | 2.16 | ok |
| 17 | `mesh·tcp·250K·1000ms` | 1800 | 450.00 | 100.2% | 99.0% | 144.2 | – | – | 7.8 → 51.4 | 4.40 | ok |
| 18 | `mesh·udp·100K·500ms` | 1800 | 180.00 | 100.2% | 99.8% | – | 0.13 | 0.00 | 8.2 → 30.9 | 1.98 | ok |
| 19 | `cs·tcp·100K·250ms` | 900 | 90.00 | 97.1% | 4.0% | 146.5 | – | – | 8.1 → 67.3 | 6.25 | ok |
| 20 | `cs·udp·100K·100ms` | 900 | 90.00 | 100.2% | 99.0% | – | 0.74 | 0.00 | 8.3 → 50.7 | 4.06 | ok |
| 21 | `cs·tcp·100K·500ms` | 900 | 90.00 | 99.0% | 0.0% | 146.3 | – | – | 8.1 → 65.9 | 6.05 | ok |
| 22 | `mesh·udp·250K·1000ms` | 1800 | 450.00 | 105.7% | 96.4% | – | 0.24 | 0.00 | 8.2 → 43.2 | 3.34 | ok |
| 23 | `mesh·udp·50K·1000ms` | 1800 | 90.00 | 105.6% | 96.5% | – | 0.17 | 0.00 | 8.1 → 27.1 | 1.70 | ok |
| 24 | `mesh·udp·50K·100ms` | 1800 | 90.00 | 100.0% | 99.9% | – | 0.14 | 0.00 | 8.2 → 35.3 | 2.20 | ok |
| 25 | `cs·tcp·100K·100ms` | 900 | 90.00 | 99.9% | 93.5% | 154.2 | – | – | 8.3 → 66.6 | 6.13 | ok |
| 26 | `mesh·tcp·100K·250ms` | 1800 | 180.00 | 100.8% | 0.0% | 16.1 | – | – | 8.5 → 44.8 | 3.42 | ok |
| 27 | `mesh·udp·250K·100ms` | 1800 | 450.00 | 100.0% | 99.8% | – | 18.55 | 0.00 | 7.9 → 47.0 | 3.55 | failed: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| 28 | `mesh·tcp·250K·250ms` | 1800 | 450.00 | 0.0% | 0.0% | – | – | – | 7.9 → 8.8 | 0.90 | failed: RuntimeError: Not running: h2-78 |
| 29 | `mesh·udp·100K·250ms` | 1800 | 180.00 | 101.3% | 97.3% | – | 0.22 | 0.00 | 8.0 → 34.3 | 2.24 | ok |

Per image at 900 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 947 | 1.2 | 99.4% | – |
| `kathara/frr` | 6 | 1.3 | 0.6% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
