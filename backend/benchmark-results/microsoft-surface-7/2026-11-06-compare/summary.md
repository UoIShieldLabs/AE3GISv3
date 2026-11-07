# AE3GIS vs GNS3 on microsoft-surface-7

Commit `ff12f7f629`. Cells are **AE3GIS / GNS3**; ratios are GNS3 ÷ AE3GIS.

- **ae3gis:** 3.1.0, Docker 29.9.2, kernel 6.6.87.2-microsoft-standard-WSL2, 8 CPUs, 15.6 GB, cgroup v2
- **gns3:** 2.2.56.1, Docker 28.1.1, kernel 5.15.0-136-generic, 8 CPUs, 15.6 GB, cgroup v1

## E0: at rest (mean of reps, last 3 min)

| metric | AE3GIS / GNS3 | ratio |
|---|---|---|
| host footprint, GB (VM + helpers) | 2.92 / 2.25 | 0.77× |
|   VM process | 2.04 / 2.07 | 1.02× |
|   helpers | 0.88 / 0.17 | 0.20× |
| host cores (VM + helpers) | 0.028 / 0.187 | 6.60× |
| memory used inside the VM, GB | 0.78 / 0.72 | 0.92× |
| CPU cores inside the VM | 0.009 / 0.033 | 3.61× |
| VM disk on the host, GB | 89.9 / 38.8 | 0.43× |
| VM start, s | 11.7 / 70.0 | 5.96× |

## E1: lab lifecycle (mean of ok reps)

| hosts | nodes | ok reps | deploy s | ready s | usable s | teardown s | usable ratio |
|---|---|---|---|---|---|---|---|
| 25 | 30 | 3/3 / 3/3 | 9.2 / 30.4 | 0.7 / 2.0 | 9.9 / 32.4 | 6.2 / 15.7 | 3.29× |
| 50 | 57 | 3/3 / 3/3 | 15.6 / 58.9 | 0.8 / 2.3 | 16.4 / 61.2 | 11.3 / 31.3 | 3.73× |
| 100 | 109 | 3/3 / 3/3 | 28.5 / 124.0 | 1.2 / 3.8 | 29.7 / 127.8 | 21.4 / 58.7 | 4.31× |
| 200 | 213 | 3/3 / 3/3 | 60.6 / 289.9 | 2.3 / 7.3 | 62.9 / 297.1 | 44.0 / 116.7 | 4.72× |
| 400 | 424 | 3/3 / 3/3 | 148.1 / 747.3 | 4.0 / 15.2 | 152.1 / 762.5 | 108.6 / 239.4 | 5.01× |
| 800 | 846 | 3/3 / 0/3 | 434.8 / skipped | 8.1 / skipped | 443.0 / skipped | 430.9 / skipped | – |

## E1: what a lab adds (over the step's reference)

| hosts | VM memory GB | per node MB | lab containers per node MB | platform's own GB | host footprint GB | footprint ratio | host cores at hold | VM cores at hold |
|---|---|---|---|---|---|---|---|---|
| 25 | 0.28 / 0.57 | 9.7 / 19.4 | 3.9 / 5.0 | 0.17 / 0.42 | 0.47 / 0.69 | 1.46× | 0.04 / 0.26 | 0.018 / 0.067 |
| 50 | 0.51 / 1.09 | 9.1 / 19.6 | 3.3 / 4.4 | 0.32 / 0.85 | 0.73 / 1.24 | 1.70× | 0.06 / 0.33 | 0.027 / 0.101 |
| 100 | 0.94 / 2.06 | 8.8 / 19.3 | 3.1 / 4.2 | 0.61 / 1.62 | 1.21 / 2.32 | 1.92× | 0.08 / 0.46 | 0.041 / 0.201 |
| 200 | 1.82 / 4.08 | 8.7 / 19.6 | 3.0 / 4.0 | 1.20 / 3.24 | 2.18 / 4.63 | 2.12× | 0.12 / 0.65 | 0.071 / 0.360 |
| 400 | 3.56 / 8.19 | 8.6 / 19.8 | 2.9 / 4.0 | 2.37 / 6.55 | 4.07 / 9.58 | 2.35× | 0.19 / 0.90 | 0.119 / 0.601 |
| 800 | 7.15 / skipped | 8.7 / skipped | 2.9 / skipped | 4.80 / skipped | 8.25 / skipped | – | 0.31 / skipped | 0.216 / skipped |

## E2: network on the 100-host lab

| ping | p50 ms | p95 ms | max ms |
|---|---|---|---|
| cross_core | 2.54 / 13.60 | 4.97 / 34.08 | 9.15 / 49.31 |
| same_lan | 1.22 / 1.47 | 3.14 / 15.06 | 61.36 / 51.04 |

| flat-out TCP | Gb/s | host cores | VM cores |
|---|---|---|---|
| cross_core | 0.05 / 0.08 | 6.33 / 2.40 | 6.65 / 3.22 |
| same_lan | 0.02 / 0.48 | 2.18 / 2.55 | 2.16 / 1.53 |

| load ladder | flows | highest rate passed (per flow) | total offered there, Mb/s | peak delivered, Mb/s |
|---|---|---|---|---|
| cs/tcp | 100 | 500K / 100K | 50 / 10 | 50 / 23 |
| cs/udp | 100 | 500K / 100K | 50 / 10 | 69 / 15 |
| mesh/tcp | 200 | 500K / 500K | 100 / 100 | 175 / 173 |
| mesh/udp | 200 | 1M / 250K | 200 / 50 | 203 / 87 |

| CPU at equal load | rate per flow | host cores per 100 Mb/s | VM cores per 100 Mb/s | RTT p95 ms |
|---|---|---|---|---|
| cs/tcp | 100K | 29.555 / 18.101 | 27.859 / 47.712 | 35.25 / 99.36 |
| cs/udp | 100K | 23.229 / 17.589 | 15.757 / 61.212 | – / – |
| mesh/tcp | 500K | 5.784 / 1.946 | 5.780 / 7.937 | 10.46 / 1409.83 |
| mesh/udp | 250K | 7.531 / 3.525 | 6.865 / 15.492 | – / – |

## E3: a lab at rest once the deploy's aftermath is over

The hold starts once the VM's CPU has stayed quiet for a while after the deploy (E1's hold starts 30 s after the network is ready).

| hosts | quiet after the deploy, s | host cores | VM cores | dockerd, containerd & co | lab's containers | E1 hold: host cores |
|---|---|---|---|---|---|---|
| 400 | 66 / 446 | 0.18 / 0.89 | 0.12 / 0.54 | 0.07 / 0.35 | 0.006 / 0.030 | 0.19 / 0.90 |

## Steps not ok

- gns3 e1-h800-r1: skipped
- gns3 e1-h800-r2: skipped
- gns3 e1-h800-r3: skipped

