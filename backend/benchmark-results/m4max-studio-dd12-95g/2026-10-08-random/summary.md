# Benchmark suite `random` on `m4max-studio-dd12-95g`

- **Suite:** The image census, then 10 random-mix idle climbs (every type with equal odds), each to its own ceiling, from the images the census found usable on this host. (sha `f52ecbd59d12`)
- **AE3GIS:** `3af8219fb50f`
- **Docker restart before each benchmark:** docker desktop restart
- **When:** 2026-10-08T18:10:47 → 2026-10-27T01:32:41 UTC
- **Images not built:** `ae3gis.local/malicious-client` (Builds only for linux/amd64; this host is linux/arm64), `ae3gis.local/zeek` (BuildError: E: Couldn't find any package by regex 'zeekctl-6.0')

| # | Run | Status | Outcome | Memory used at rest | Report |
|---|---|---|---|---:|---|
| 01 | `census` | done | 27 of 29 cases usable | 1.94 of 101.9 GB | [report](01-census/report.md) |
| 02 | `random-idle-run1` | done | ceiling 2240 hosts · pool without 2 image(s) | 1.59 of 101.9 GB | [report](02-random-idle-run1/report.md) |
| 03 | `random-idle-run2` | done | ceiling 2320 hosts (2330 hosts failed (deploy_failed)) · pool without 2 image(s) | 1.83 of 101.9 GB | [report](03-random-idle-run2/report.md) |
| 04 | `random-idle-run3` | done | ceiling 2340 hosts (2350 hosts failed (deploy_failed)) · pool without 2 image(s) | 2.03 of 101.9 GB | [report](04-random-idle-run3/report.md) |
| 05 | `random-idle-run4` | done | ceiling 2280 hosts (2290 hosts failed (deploy_failed)) · pool without 2 image(s) | 1.60 of 101.9 GB | [report](05-random-idle-run4/report.md) |
| 06 | `random-idle-run5` | done | ceiling 2350 hosts (2360 hosts failed (deploy_failed)) · pool without 2 image(s) | 1.77 of 101.9 GB | [report](06-random-idle-run5/report.md) |
| 07 | `random-idle-run6` | done | ceiling 2360 hosts (2370 hosts failed (deploy_failed)) · pool without 2 image(s) | 2.09 of 101.9 GB | [report](07-random-idle-run6/report.md) |
| 08 | `random-idle-run7` | done | ceiling 2380 hosts (2390 hosts failed (deploy_failed)) · pool without 2 image(s) | 1.85 of 101.9 GB | [report](08-random-idle-run7/report.md) |
| 09 | `random-idle-run8` | done | ceiling 2320 hosts (ceiling between 2320 and 2330 hosts (2330 failed)) · pool without 2 image(s) | 2.14 of 101.9 GB | [report](09-random-idle-run8/report.md) |
| 10 | `random-idle-run9` | done | ceiling 2350 hosts (ceiling between 2350 and 2360 hosts (2360 failed)) · pool without 2 image(s) | 1.84 of 101.9 GB | [report](10-random-idle-run9/report.md) |
| 11 | `random-idle-run10` | done | ceiling 2290 hosts (ceiling between 2290 and 2300 hosts (2300 failed)) · pool without 2 image(s) | 1.85 of 101.9 GB | [report](11-random-idle-run10/report.md) |

## Random climbs: `random-idle` (10 with a ceiling)

| Run | Seed | Ceiling hosts | Nodes | Peak memory % | MB / node | Deploy s / node |
|---|---:|---:|---:|---:|---:|---:|
| `random-idle-run1` | 1 | 2240 | 2321 | 80.2 | 21.9 | 0.566 |
| `random-idle-run2` | 2 | 2320 | 2404 | 79.9 | 24.5 | 0.535 |
| `random-idle-run3` | 3 | 2340 | 2424 | 79.2 | 20.1 | 0.550 |
| `random-idle-run4` | 4 | 2280 | 2363 | 74.9 | 25.0 | 0.629 |
| `random-idle-run5` | 5 | 2350 | 2435 | 76.2 | 25.1 | 0.589 |
| `random-idle-run6` | 6 | 2360 | 2445 | 77.0 | 25.4 | 0.526 |
| `random-idle-run7` | 7 | 2380 | 2465 | 73.3 | 21.7 | 0.635 |
| `random-idle-run8` | 8 | 2320 | 2404 | 77.8 | 25.3 | 0.531 |
| `random-idle-run9` | 9 | 2350 | 2435 | 80.1 | 23.2 | 0.607 |
| `random-idle-run10` | 10 | 2290 | 2373 | 76.9 | 25.7 | 0.564 |

Across runs (mean ± std, min–max):

- **Ceiling:** 2323 ± 42 (2240–2380) hosts, 2407 ± 44 (2321–2465) nodes
- **Peak memory:** 77.5 ± 2.3 (73.3–80.2) %
- **Memory per node:** 23.8 ± 2.0 (20.1–25.7) MB
- **Deploy per node:** 0.573 ± 0.040 (0.526–0.635) s

Share of nodes per type at the ceiling (mean ± std over runs):

| Type | Share |
|---|---:|
| switch | 10.4 ± 0.3 (9.7–10.9) % |
| firewall | 7.9 ± 0.6 (6.6–8.7) % |
| dns-server | 7.7 ± 0.5 (7.1–8.5) % |
| router | 7.6 ± 0.7 (6.6–9.0) % |
| hmi | 7.5 ± 0.3 (7.0–8.0) % |
| file-server | 7.5 ± 0.3 (7.2–8.4) % |
| database-server | 7.5 ± 0.6 (6.8–8.6) % |
| ftp-server | 7.5 ± 0.6 (6.9–8.2) % |
| ids | 7.5 ± 0.4 (6.9–8.1) % |
| web-server | 7.4 ± 0.5 (6.8–8.5) % |
| workstation | 7.3 ± 0.5 (6.4–8.2) % |
| plc | 7.2 ± 0.4 (6.4–7.7) % |
| dhcp-server | 7.1 ± 0.6 (6.4–8.1) % |
