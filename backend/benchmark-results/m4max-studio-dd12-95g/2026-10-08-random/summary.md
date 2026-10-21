# Benchmark suite `random` on `m4max-studio-dd12-95g`

- **Suite:** The image census, then 10 random-mix idle climbs (every type with equal odds), each to its own ceiling, from the images the census found usable on this host. (sha `f52ecbd59d12`)
- **AE3GIS:** `ce3d1d4d6876`
- **Docker restart before each benchmark:** docker desktop restart
- **When:** 2026-10-08T18:10:47 → 2026-10-11T14:08:52 UTC
- **Images not built:** `ae3gis.local/malicious-client` (Builds only for linux/amd64; this host is linux/arm64), `ae3gis.local/zeek` (BuildError: E: Couldn't find any package by regex 'zeekctl-6.0')

| # | Run | Status | Outcome | Memory used at rest | Report |
|---|---|---|---|---:|---|
| 01 | `census` | done | 27 of 29 cases usable | 1.94 of 101.9 GB | [report](01-census/report.md) |
| 02 | `random-idle-run1` | done | ceiling 1140 hosts (1150 hosts failed (memory)) · pool without 2 image(s) | 1.90 of 101.9 GB | [report](02-random-idle-run1/report.md) |
| 03 | `random-idle-run2` | done | ceiling 1200 hosts (ceiling between 1200 and 1210 hosts (1210 failed)) · pool without 2 image(s) | 1.68 of 101.9 GB | [report](03-random-idle-run2/report.md) |
| 04 | `random-idle-run3` | done | ceiling 1140 hosts (ceiling between 1140 and 1150 hosts (1150 failed)) · pool without 2 image(s) | 1.94 of 101.9 GB | [report](04-random-idle-run3/report.md) |
| 05 | `random-idle-run4` | done | ceiling 2280 hosts (2290 hosts failed (deploy_failed)) · pool without 2 image(s) | 1.60 of 101.9 GB | [report](05-random-idle-run4/report.md) |
| 06 | `random-idle-run5` | done | ceiling 2350 hosts (2360 hosts failed (deploy_failed)) · pool without 2 image(s) | 1.77 of 101.9 GB | [report](06-random-idle-run5/report.md) |
| 07 | `random-idle-run6` | done | ceiling 1640 hosts (2050 hosts failed (destroy_failed)) · pool without 2 image(s) | 1.79 of 101.9 GB | [report](07-random-idle-run6/report.md) |
| 08 | `random-idle-run7` | done | ceiling 2380 hosts (2390 hosts failed (deploy_failed)) · pool without 2 image(s) | 1.85 of 101.9 GB | [report](08-random-idle-run7/report.md) |
| 09 | `random-idle-run8` | done | ceiling 2070 hosts (ceiling between 2070 and 2075 hosts (2075 failed)) · pool without 2 image(s) | 1.92 of 101.9 GB | [report](09-random-idle-run8/report.md) |
| 10 | `random-idle-run9` | done | ceiling 2350 hosts (ceiling between 2350 and 2360 hosts (2360 failed)) · pool without 2 image(s) | 1.84 of 101.9 GB | [report](10-random-idle-run9/report.md) |
| 11 | `random-idle-run10` | done | ceiling 2290 hosts (ceiling between 2290 and 2300 hosts (2300 failed)) · pool without 2 image(s) | 1.85 of 101.9 GB | [report](11-random-idle-run10/report.md) |

## Random climbs: `random-idle` (10 with a ceiling)

| Run | Seed | Ceiling hosts | Nodes | Peak memory % | MB / node | Deploy s / node |
|---|---:|---:|---:|---:|---:|---:|
| `random-idle-run1` | 1 | 1140 | 1182 | 49.5 | 36.9 | 1.251 |
| `random-idle-run2` | 2 | 1200 | 1244 | 59.5 | 30.3 | 1.388 |
| `random-idle-run3` | 3 | 1140 | 1182 | 55.4 | 29.3 | 1.200 |
| `random-idle-run4` | 4 | 2280 | 2363 | 74.9 | 25.0 | 0.629 |
| `random-idle-run5` | 5 | 2350 | 2435 | 76.2 | 25.1 | 0.589 |
| `random-idle-run6` | 6 | 1640 | 1700 | 51.2 | 29.6 | 0.392 |
| `random-idle-run7` | 7 | 2380 | 2465 | 73.3 | 21.7 | 0.635 |
| `random-idle-run8` | 8 | 2070 | 2146 | 65.2 | 26.1 | 0.553 |
| `random-idle-run9` | 9 | 2350 | 2435 | 80.1 | 23.2 | 0.607 |
| `random-idle-run10` | 10 | 2290 | 2373 | 76.9 | 25.7 | 0.564 |

Across runs (mean ± std, min–max):

- **Ceiling:** 1884 ± 545 (1140–2380) hosts, 1952 ± 564 (1182–2465) nodes
- **Peak memory:** 66.2 ± 11.5 (49.5–80.1) %
- **Memory per node:** 27.3 ± 4.4 (21.7–36.9) MB
- **Deploy per node:** 0.781 ± 0.354 (0.392–1.388) s

Share of nodes per type at the ceiling (mean ± std over runs):

| Type | Share |
|---|---:|
| switch | 10.4 ± 0.4 (9.4–10.9) % |
| firewall | 7.8 ± 0.7 (6.4–8.9) % |
| dns-server | 7.8 ± 0.5 (7.1–8.7) % |
| hmi | 7.6 ± 0.5 (6.6–8.5) % |
| router | 7.6 ± 1.0 (6.4–10.0) % |
| file-server | 7.5 ± 0.4 (7.1–8.4) % |
| ftp-server | 7.5 ± 0.6 (6.9–8.3) % |
| database-server | 7.5 ± 0.7 (6.5–8.6) % |
| web-server | 7.4 ± 0.5 (6.9–8.5) % |
| ids | 7.3 ± 0.3 (6.9–7.9) % |
| dhcp-server | 7.3 ± 0.5 (6.6–8.1) % |
| workstation | 7.2 ± 0.6 (6.4–8.4) % |
| plc | 7.1 ± 0.5 (6.4–7.7) % |
