# Benchmark suite `random` on `m4-macbook-air`

- **Suite:** The image census, then 10 random-mix idle climbs (every type with equal odds), each to its own ceiling, from the images the census found usable on this host. (sha `f52ecbd59d12`)
- **AE3GIS:** `0c8ac80e40b3`
- **Docker restart before each benchmark:** docker desktop restart
- **When:** 2026-10-06T03:36:39 → 2026-10-06T09:49:30 UTC
- **Images not built:** `ae3gis.local/malicious-client` (Builds only for linux/amd64; this host is linux/arm64), `ae3gis.local/zeek` (BuildError: E: Couldn't find any package by regex 'zeekctl-6.0')

| # | Run | Status | Outcome | Memory used at rest | Report |
|---|---|---|---|---:|---|
| 01 | `census` | done | 27 of 29 cases usable | 0.89 of 16.7 GB | [report](01-census/report.md) |
| 02 | `random-idle-run1` | done | ceiling 490 hosts (memory peaked at 90.7% at 490 hosts) · pool without 2 image(s) | 0.84 of 16.7 GB | [report](02-random-idle-run1/report.md) |
| 03 | `random-idle-run2` | done | ceiling 560 hosts (memory peaked at 90.1% at 560 hosts) · pool without 2 image(s) | 0.86 of 16.7 GB | [report](03-random-idle-run2/report.md) |
| 04 | `random-idle-run3` | done | ceiling 450 hosts (memory peaked at 91.2% at 450 hosts) · pool without 2 image(s) | 0.91 of 16.7 GB | [report](04-random-idle-run3/report.md) |
| 05 | `random-idle-run4` | done | ceiling 460 hosts (memory peaked at 90.4% at 460 hosts) · pool without 2 image(s) | 0.86 of 16.7 GB | [report](05-random-idle-run4/report.md) |
| 06 | `random-idle-run5` | done | ceiling 500 hosts (memory peaked at 90.1% at 500 hosts) · pool without 2 image(s) | 0.89 of 16.7 GB | [report](06-random-idle-run5/report.md) |
| 07 | `random-idle-run6` | done | ceiling 490 hosts (memory peaked at 90.1% at 490 hosts) · pool without 2 image(s) | 0.88 of 16.7 GB | [report](07-random-idle-run6/report.md) |
| 08 | `random-idle-run7` | done | ceiling 700 hosts (memory peaked at 90.4% at 700 hosts) · pool without 2 image(s) | 0.87 of 16.7 GB | [report](08-random-idle-run7/report.md) |
| 09 | `random-idle-run8` | done | ceiling 530 hosts (memory peaked at 91.2% at 530 hosts) · pool without 2 image(s) | 0.89 of 16.7 GB | [report](09-random-idle-run8/report.md) |
| 10 | `random-idle-run9` | done | ceiling 540 hosts (memory peaked at 90.3% at 540 hosts) · pool without 2 image(s) | 0.89 of 16.7 GB | [report](10-random-idle-run9/report.md) |
| 11 | `random-idle-run10` | done | ceiling 580 hosts (memory peaked at 90.3% at 580 hosts) · pool without 2 image(s) | 0.88 of 16.7 GB | [report](11-random-idle-run10/report.md) |

## Random climbs: `random-idle` (10 with a ceiling)

| Run | Seed | Ceiling hosts | Nodes | Peak memory % | MB / node | Deploy s / node |
|---|---:|---:|---:|---:|---:|---:|
| `random-idle-run1` | 1 | 490 | 510 | 90.7 | 24.2 | 0.349 |
| `random-idle-run2` | 2 | 560 | 582 | 90.1 | 20.4 | 0.358 |
| `random-idle-run3` | 3 | 450 | 470 | 91.2 | 28.0 | 0.270 |
| `random-idle-run4` | 4 | 460 | 480 | 90.4 | 26.2 | 0.381 |
| `random-idle-run5` | 5 | 500 | 521 | 90.1 | 23.6 | 0.310 |
| `random-idle-run6` | 6 | 490 | 510 | 90.1 | 24.4 | 0.284 |
| `random-idle-run7` | 7 | 700 | 728 | 90.4 | 16.3 | 0.380 |
| `random-idle-run8` | 8 | 530 | 551 | 91.2 | 23.1 | 0.319 |
| `random-idle-run9` | 9 | 540 | 561 | 90.3 | 21.7 | 0.352 |
| `random-idle-run10` | 10 | 580 | 602 | 90.3 | 20.1 | 0.314 |

Across runs (mean ± std, min–max):

- **Ceiling:** 530 ± 73 (450–700) hosts, 552 ± 75 (470–728) nodes
- **Peak memory:** 90.5 ± 0.4 (90.1–91.2) %
- **Memory per node:** 22.8 ± 3.3 (16.3–28.0) MB
- **Deploy per node:** 0.332 ± 0.038 (0.270–0.381) s

Share of nodes per type at the ceiling (mean ± std over runs):

| Type | Share |
|---|---:|
| switch | 10.4 ± 0.5 (9.8–11.1) % |
| firewall | 8.1 ± 0.8 (6.7–9.1) % |
| ftp-server | 7.8 ± 0.7 (6.3–9.1) % |
| hmi | 7.7 ± 1.1 (6.5–9.8) % |
| database-server | 7.6 ± 1.2 (6.0–10.2) % |
| dns-server | 7.5 ± 1.1 (5.0–8.9) % |
| router | 7.4 ± 1.0 (6.0–9.1) % |
| ids | 7.4 ± 0.5 (6.8–8.6) % |
| file-server | 7.3 ± 1.1 (5.7–9.0) % |
| plc | 7.3 ± 1.2 (5.7–9.0) % |
| workstation | 7.2 ± 1.1 (6.1–9.4) % |
| web-server | 7.2 ± 1.1 (5.6–8.6) % |
| dhcp-server | 7.0 ± 1.3 (5.1–8.7) % |
