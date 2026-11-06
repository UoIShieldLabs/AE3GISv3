# AE3GIS vs GNS3 on m4-macbook-air

Commit `04e2d0f205`. Cells are **AE3GIS / GNS3**; ratios are GNS3 ÷ AE3GIS.

- **ae3gis:** 3.1.0, Docker 29.9.2, kernel 7.0.14-linuxkit, 8 CPUs, 15.6 GB, cgroup v2
- **gns3:** 2.2.54, Docker 28.1.1, kernel 5.15.0-136-generic, 8 CPUs, 15.6 GB, cgroup v1

## E0: at rest (mean of reps, last 3 min)

| metric | AE3GIS / GNS3 | ratio |
|---|---|---|
| host footprint, GB (VM + helpers) | 2.09 / 2.25 | 1.08× |
|   VM process | 1.64 / 2.23 | 1.36× |
|   helpers | 0.45 / 0.02 | 0.05× |
| host cores (VM + helpers) | 0.045 / 0.033 | 0.72× |
| memory used inside the VM, GB | 0.78 / 0.57 | 0.74× |
| CPU cores inside the VM | 0.011 / 0.011 | 1.07× |
| VM disk on the host, GB | 46.7 / 36.8 | 0.79× |
| VM start, s | 6.8 / 42.8 | 6.33× |

## E1: lab lifecycle (mean of ok reps)

| hosts | nodes | ok reps | deploy s | ready s | usable s | teardown s | usable ratio |
|---|---|---|---|---|---|---|---|
| 25 | 30 | 3/3 / 3/3 | 4.4 / 16.6 | 0.3 / 0.4 | 4.8 / 17.0 | 2.4 / 7.0 | 3.58× |
| 50 | 57 | 3/3 / 3/3 | 6.8 / 21.0 | 0.4 / 0.5 | 7.2 / 21.5 | 4.9 / 8.4 | 2.98× |
| 100 | 109 | 3/3 / 3/3 | 12.5 / 52.1 | 0.7 / 1.5 | 13.2 / 53.6 | 7.8 / 10.2 | 4.06× |
| 200 | 213 | 3/3 / 2/3 | 29.0 / 69.4 | 1.7 / 0.9 | 30.7 / 70.3 | 23.4 / 18.0 | 2.29× |
| 400 | 424 | 3/3 / 2/3 | 87.3 / 208.1 | 3.3 / 1.5 | 90.6 / 209.6 | 73.8 / 74.1 | 2.31× |
| 800 | 846 | 3/3 / 0/3 | 266.7 / skipped | 8.5 / skipped | 275.2 / skipped | 300.9 / skipped | – |

## E1: what a lab adds (over the step's reference)

| hosts | VM memory GB | per node MB | lab containers per node MB | platform's own GB | host footprint GB | footprint ratio | host cores at hold | VM cores at hold |
|---|---|---|---|---|---|---|---|---|
| 25 | 0.52 / 0.58 | 17.7 / 19.7 | 5.0 / 4.5 | 0.37 / 0.44 | 0.71 / 0.76 | 1.07× | 0.23 / 0.07 | 0.023 / 0.025 |
| 50 | 0.89 / 1.09 | 15.9 / 19.6 | 3.8 / 4.0 | 0.68 / 0.87 | 1.12 / 1.34 | 1.20× | 0.18 / 0.13 | 0.033 / 0.035 |
| 100 | 1.64 / 2.04 | 15.4 / 19.2 | 3.2 / 3.9 | 1.30 / 1.63 | 1.90 / 2.49 | 1.31× | 0.13 / 0.19 | 0.050 / 0.046 |
| 200 | 3.06 / 4.04 | 14.7 / 19.4 | 2.9 / 3.8 | 2.45 / 3.26 | 3.41 / 4.89 | 1.43× | 3.26 / 0.20 | 2.637 / 0.085 |
| 400 | 5.86 / 8.45 | 14.1 / 20.4 | 2.8 / 3.7 | 4.70 / 6.93 | 6.39 / 10.76 | 1.68× | 4.20 / 0.41 | 3.476 / 0.281 |
| 800 | 11.20 / skipped | 13.6 / skipped | 2.7 / skipped | 8.97 / skipped | 12.40 / skipped | – | 4.44 / skipped | 3.831 / skipped |

## E2: network on the 100-host lab

| ping | p50 ms | p95 ms | max ms |
|---|---|---|---|
| cross_core | 6.55 / 1.35 | 9.15 / 1.74 | 10.09 / 2.15 |
| same_lan | 1.52 / 0.44 | 3.48 / 0.89 | 10.62 / 1.20 |

| flat-out TCP | Gb/s | host cores | VM cores |
|---|---|---|---|
| cross_core | 0.08 / 1.59 | 6.96 / 4.30 | 6.85 / 3.48 |
| same_lan | 0.13 / 4.65 | 2.96 / 4.02 | 2.69 / 3.21 |

| load ladder | flows | highest rate passed (per flow) | total offered there, Mb/s | peak delivered, Mb/s |
|---|---|---|---|---|
| cs/tcp | 100 | 500K / 5M | 50 / 500 | 80 / 500 |
| cs/udp | 100 | 1M / 5M | 100 / 500 | 100 / 498 |
| mesh/tcp | 200 | 1M / 5M | 200 / 1000 | 218 / 1000 |
| mesh/udp | 200 | 1M / 5M | 200 / 1000 | 346 / 1000 |

| CPU at equal load | rate per flow | host cores per 100 Mb/s | VM cores per 100 Mb/s | RTT p95 ms |
|---|---|---|---|---|
| cs/tcp | 500K | 8.773 / 1.808 | 8.313 / 1.342 | 12.80 / 2.14 |
| cs/udp | 1M | 6.068 / 1.379 | 5.820 / 0.650 | – / – |
| mesh/tcp | 1M | 3.050 / 0.597 | 2.989 / 0.457 | 18.02 / 0.53 |
| mesh/udp | 1M | 2.520 / 0.569 | 2.307 / 0.333 | – / – |

## Steps not ok

- gns3 e1-h200-r1: not_ready
- gns3 e1-h400-r1: skipped
- gns3 e1-h800-r1: skipped
- gns3 e1-h800-r2: skipped
- gns3 e1-h800-r3: skipped

