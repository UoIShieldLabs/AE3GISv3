# Benchmark: m4-macbook-air · burst-limits · 1000 hosts · round 4

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `9f7bf000d83f` · bench
- **Environment fingerprint:** `8affbcfb7a1aea9104133f89048bbe26c107bbcd5ce1d1fe18845c01d1422c86`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 9 cells on one deployment of 1000 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 939.1 of 16746.1 MB used (5.6%) · host CPU 0.8% · Docker processes 273.4 MB · Docker's disk 73.1% used
- **Outcome:** 4 of 9 cells passed (5 degraded) · 2026-10-09T09:05:20 → 2026-10-09T12:37:49

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1000 | 1 | 1057 | 1056 | 378.9 | 14.11 | 397.4 | 12.7 | 15.7 | 1.2 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 9 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 87.9% | 86.0% | 86.5% | 71.2% | 99.6% |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 0.0% | 15.0% | 0.0% | 0.0% | 40.0% |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 404.2 | 415.9 | 474.7 | 815.4 | 315.5 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 16613 | 29029 | 34852 | 18316 | 22248 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 69.0 | 73.6 | 70.3 | 32.4 | 65.7 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | 4.80 | 5.05 | 4.73 | 5.29 | 4.66 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 94.0% | 99.5% | 101.6% | 102.6% |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 0.0% | 96.2% | 96.9% | 93.3% |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Jitter p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 26.95 | 3.68 | 1.89 | 1.01 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Loss %**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 6.16 | 0.01 | 0.00 | 0.00 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 60.8 | 46.8 | 41.9 | 38.4 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

**pattern cs · protocol udp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | 4.00 | 3.12 | 2.77 | 2.58 |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | – | – | – | – | – |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·50K·1000ms` | 1000 | 50.00 | 71.2% | 0.0% | 815.4 | – | – | 51.2 → 83.7 | 5.29 | degraded: delivered 71.2% of what was asked (< 95%) |
| 2 | `cs·tcp·50K·500ms` | 1000 | 50.00 | 86.5% | 0.0% | 474.7 | – | – | 10.8 → 81.1 | 4.73 | degraded: delivered 86.5% of what was asked (< 95%) |
| 3 | `cs·udp·50K·250ms` | 1000 | 50.00 | 94.0% | 0.0% | – | 26.95 | 6.16 | 10.0 → 70.8 | 4.00 | degraded: delivered 94.0% of what was asked (< 95%) |
| 4 | `cs·tcp·50K·250ms` | 1000 | 50.00 | 86.0% | 15.0% | 415.9 | – | – | 9.8 → 83.5 | 5.05 | degraded: delivered 86.0% of what was asked (< 95%) |
| 5 | `cs·udp·50K·500ms` | 1000 | 50.00 | 99.5% | 96.2% | – | 3.68 | 0.01 | 10.5 → 57.3 | 3.12 | ok |
| 6 | `cs·udp·50K·2000ms` | 1000 | 50.00 | 102.6% | 93.3% | – | 1.01 | 0.00 | 10.1 → 48.5 | 2.58 | ok |
| 7 | `cs·tcp·50K·100ms` | 1000 | 50.00 | 87.9% | 0.0% | 404.2 | – | – | 11.2 → 80.2 | 4.80 | degraded: delivered 87.9% of what was asked (< 95%) |
| 8 | `cs·tcp·50K·2000ms` | 1000 | 50.00 | 99.6% | 40.0% | 315.5 | – | – | 11.2 → 77.0 | 4.66 | ok |
| 9 | `cs·udp·50K·1000ms` | 1000 | 50.00 | 101.6% | 96.9% | – | 1.89 | 0.00 | 10.1 → 52.0 | 2.77 | ok |

Per image at 1000 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 1051 | 1.2 | 99.2% | – |
| `kathara/frr` | 6 | 1.7 | 0.8% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
