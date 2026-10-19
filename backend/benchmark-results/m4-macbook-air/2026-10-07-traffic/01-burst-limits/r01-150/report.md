# Benchmark: m4-macbook-air · burst-limits · 150 hosts · round 1

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `59892984a8de` · bench
- **Environment fingerprint:** `d94299ab04b0ad7eff7eaa2ec3fc0edf566cfaa76511a7a173c08929cbda418e`
- **Topology:** generated, mixed (seed 0), ≤ 200 hosts per subnet, ≤ 48 per switch. Hosts: workstation. Servers: workstation 1/50 hosts. Switches: switch. Core: router
- **Steps:** traffic matrix of 5 cells on one deployment of 150 hosts × 1 · pre 15.0s, settle 15.0s, hold 50.0s · monitor every 5.0s
- **Load:** per cell: cs: clients → servers; mesh: mesh; axes: pattern cs / mesh, protocol tcp / udp, bitrate 50K / 100K / 250K / 500K / 1M, burst_interval_ms 100ms / 250ms / 500ms / 1000ms / 2000ms (iperf3 report every 10s)
- **At rest (before the first step):** 967.4 of 16746.1 MB used (5.8%) · host CPU 0.8% · Docker processes 273.3 MB · Docker's disk 68.5% used
- **Outcome:** 5 of 5 cells passed · 2026-10-08T00:19:20 → 2026-10-08T00:32:31

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 150 | 1 | 161 | 160 | 20.3 | 1.26 | 12.6 | 13.7 | 15.8 | 1.3 / 1.2 | – | – | – | – | 0.2 | – | – | ok |

Traffic matrix: 5 cells, bitrate (rows) × burst_interval_ms (columns), per pattern, protocol; each cell held 50.0s after a 5.0s ramp and a 60.0s idle gap (host CPU over idle compares the two).

**pattern cs · protocol tcp — Delivered (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 99.7% | 97.6% | 97.7% | 98.0% | 100.0% |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Slowest flow (% of asked)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 99.2% | 79.0% | 68.3% | 90.0% | 100.0% |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — RTT p95 (ms)**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 153.7 | 225.3 | 213.0 | 54.6 | 42.1 |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Retransmits**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 1814 | 8777 | 8282 | 1784 | 34 |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Host CPU % over idle**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 86.2 | 87.4 | 86.7 | 82.6 | 77.2 |
| 1M | – | – | – | – | – |

**pattern cs · protocol tcp — Docker cores**

| bitrate \ burst_interval_ms | 100ms | 250ms | 500ms | 1000ms | 2000ms |
|---|---:|---:|---:|---:|---:|
| 50K | – | – | – | – | – |
| 100K | – | – | – | – | – |
| 250K | – | – | – | – | – |
| 500K | 6.23 | 6.37 | 6.32 | 5.92 | 5.49 |
| 1M | – | – | – | – | – |

Cells in run order:

| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms | Loss % | Host CPU % (idle → load) | Docker cores | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `cs·tcp·500K·250ms` | 150 | 75.00 | 97.6% | 79.0% | 225.3 | – | – | 1.0 → 88.3 | 6.37 | ok |
| 2 | `cs·tcp·500K·2000ms` | 150 | 75.00 | 100.0% | 100.0% | 42.1 | – | – | 1.0 → 78.1 | 5.49 | ok |
| 3 | `cs·tcp·500K·100ms` | 150 | 75.00 | 99.7% | 99.2% | 153.7 | – | – | 1.0 → 87.1 | 6.23 | ok |
| 4 | `cs·tcp·500K·500ms` | 150 | 75.00 | 97.7% | 68.3% | 213.0 | – | – | 0.9 → 87.6 | 6.32 | ok |
| 5 | `cs·tcp·500K·1000ms` | 150 | 75.00 | 98.0% | 90.0% | 54.6 | – | – | 0.9 → 83.5 | 5.92 | ok |

Per image at 150 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `kathara/base` | 159 | 1.3 | 98.6% | – |
| `kathara/frr` | 2 | 1.4 | 1.4% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
