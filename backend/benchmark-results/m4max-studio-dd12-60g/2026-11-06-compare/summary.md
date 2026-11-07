# AE3GIS vs GNS3 on m4max-studio-dd12-60g

Commit `c7defa6228`. Cells are **AE3GIS / GNS3**; ratios are GNS3 ÷ AE3GIS.

- **ae3gis:** 3.1.0, Docker 29.8.2, kernel 7.0.14-linuxkit, 12 CPUs, 58.8 GB, cgroup v2
- **gns3:** 2.2.54, Docker 28.1.1, kernel 5.15.0-136-generic, 12 CPUs, 58.7 GB, cgroup v1

## E0: at rest (mean of reps, last 3 min)

| metric | AE3GIS / GNS3 | ratio |
|---|---|---|
| host footprint, GB (VM + helpers) | 3.81 / 3.35 | 0.88× |
|   VM process | 3.19 / 3.32 | 1.04× |
|   helpers | 0.62 / 0.03 | 0.04× |
| host cores (VM + helpers) | 0.058 / 0.032 | 0.56× |
| memory used inside the VM, GB | 1.13 / 1.02 | 0.91× |
| CPU cores inside the VM | 0.017 / 0.010 | 0.62× |
| VM disk on the host, GB | 45.9 / 18.0 | 0.39× |
| VM start, s | 9.3 / 72.0 | 7.77× |

## E1: lab lifecycle (mean of ok reps)

| hosts | nodes | ok reps | deploy s | ready s | usable s | teardown s | usable ratio |
|---|---|---|---|---|---|---|---|
| 25 | 30 | 3/3 / 3/3 | 3.1 / 5.9 | 0.3 / 0.4 | 3.3 / 6.2 | 2.1 / 7.1 | 1.87× |
| 50 | 57 | 3/3 / 3/3 | 4.1 / 11.1 | 0.3 / 0.4 | 4.4 / 11.5 | 3.1 / 8.4 | 2.59× |
| 100 | 109 | 3/3 / 3/3 | 8.1 / 33.8 | 0.5 / 0.5 | 8.6 / 34.3 | 5.1 / 9.9 | 3.96× |
| 200 | 213 | 3/3 / 3/3 | 16.9 / 54.8 | 0.9 / 0.7 | 17.8 / 55.5 | 11.8 / 23.1 | 3.12× |
| 400 | 424 | 3/3 / 3/3 | 42.1 / 159.9 | 1.7 / 1.1 | 43.8 / 161.0 | 38.5 / 23.0 | 3.67× |
| 800 | 846 | 3/3 / 3/3 | 138.5 / 480.4 | 3.7 / 2.0 | 142.1 / 482.4 | 249.3 / 50.7 | 3.39× |

## E1: what a lab adds (over the step's reference)

| hosts | VM memory GB | per node MB | lab containers per node MB | platform's own GB | host footprint GB | footprint ratio | host cores at hold | VM cores at hold |
|---|---|---|---|---|---|---|---|---|
| 25 | 0.67 / 0.58 | 22.9 / 19.6 | 5.1 / 4.7 | 0.52 / 0.44 | 0.84 / 0.76 | 0.90× | 0.26 / 0.06 | 0.063 / 0.021 |
| 50 | 1.09 / 1.10 | 19.5 / 19.8 | 3.8 / 4.1 | 0.88 / 0.87 | 1.20 / 1.34 | 1.12× | 0.39 / 0.07 | 0.099 / 0.031 |
| 100 | 1.84 / 2.08 | 17.3 / 19.5 | 3.3 / 3.9 | 1.49 / 1.66 | 1.84 / 2.52 | 1.37× | 0.30 / 0.10 | 0.145 / 0.048 |
| 200 | 3.51 / 4.09 | 16.9 / 19.7 | 3.0 / 3.8 | 2.89 / 3.30 | 3.46 / 4.91 | 1.42× | 2.06 / 0.21 | 1.565 / 0.085 |
| 400 | 6.44 / 8.54 | 15.6 / 20.6 | 2.8 / 3.7 | 5.26 / 6.98 | 6.59 / 10.68 | 1.62× | 5.28 / 0.35 | 4.298 / 0.172 |
| 800 | 12.53 / 18.73 | 15.2 / 22.7 | 2.8 / 3.7 | 10.26 / 15.66 | 13.06 / 23.64 | 1.81× | 5.69 / 0.48 | 4.661 / 0.271 |

## E2: network on the 100-host lab

| ping | p50 ms | p95 ms | max ms |
|---|---|---|---|
| cross_core | 6.97 / 1.42 | 9.66 / 2.50 | 12.11 / 3.48 |
| same_lan | 4.12 / 0.27 | 6.43 / 1.12 | 8.58 / 2.12 |

| flat-out TCP | Gb/s | host cores | VM cores |
|---|---|---|---|
| cross_core | 0.12 / 2.23 | 9.05 / 7.56 | 8.02 / 5.92 |
| same_lan | 0.12 / 5.53 | 3.18 / 6.86 | 2.65 / 5.07 |

| load ladder | flows | highest rate passed (per flow) | total offered there, Mb/s | peak delivered, Mb/s |
|---|---|---|---|---|
| cs/tcp | 100 | 1M / 5M | 100 / 500 | 126 / 500 |
| cs/udp | 100 | 1M / 2M | 100 / 200 | 191 / 385 |
| mesh/tcp | 200 | 2M / 5M | 400 / 1000 | 660 / 1000 |
| mesh/udp | 200 | 2M / 2M | 400 / 400 | 946 / 983 |

| CPU at equal load | rate per flow | host cores per 100 Mb/s | VM cores per 100 Mb/s | RTT p95 ms |
|---|---|---|---|---|
| cs/tcp | 1M | 7.549 / 1.107 | 6.841 / 0.699 | 16.67 / 0.69 |
| cs/udp | 1M | 6.510 / 1.693 | 5.474 / 0.870 | – / – |
| mesh/tcp | 2M | 2.225 / 0.323 | 2.111 / 0.214 | 1.83 / 0.25 |
| mesh/udp | 2M | 2.131 / 0.792 | 1.868 / 0.440 | – / – |

## E3: a lab at rest once the deploy's aftermath is over

The hold starts once the VM's CPU has stayed quiet for a while after the deploy (E1's hold starts 30 s after the network is ready).

| hosts | quiet after the deploy, s | host cores | VM cores | dockerd, containerd & co | lab's containers | E1 hold: host cores |
|---|---|---|---|---|---|---|
| 400 | 1244 / 82 (capped) | 0.83 / 0.26 | 0.43 / 0.18 | 0.34 / 0.09 | 0.003 / 0.007 | 5.28 / 0.35 |

