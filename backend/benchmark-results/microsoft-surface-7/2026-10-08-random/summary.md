# Benchmark suite `random` on `microsoft-surface-7`

- **Suite:** The image census, then 10 random-mix idle climbs (every type with equal odds), each to its own ceiling, from the images the census found usable on this host. (sha `f52ecbd59d12`)
- **AE3GIS:** `b14a3c4efcbf`
- **Docker restart before each benchmark:** docker desktop restart
- **When:** 2026-10-08T17:19:58 → 2026-10-25T22:52:30 UTC
- **Images not built:** `ae3gis.local/zeek` (BuildError: E: Couldn't find any package by regex 'zeekctl-6.0')

| # | Run | Status | Outcome | Memory used at rest | Report |
|---|---|---|---|---:|---|
| 01 | `census` | done | 28 of 29 cases usable | 0.91 of 16.6 GB | [report](01-census/report.md) |
| 02 | `random-idle-run1` | done | ceiling 490 hosts (ceiling between 490 and 500 hosts (500 failed)) · pool without 1 image(s) | 0.87 of 16.6 GB | [report](02-random-idle-run1/report.md) |
| 03 | `random-idle-run2` | done | ceiling 630 hosts (ceiling between 630 and 640 hosts (640 failed)) · pool without 1 image(s) | 0.99 of 16.6 GB | [report](03-random-idle-run2/report.md) |
| 04 | `random-idle-run3` | done | ceiling 350 hosts (memory peaked at 93.3% at 350 hosts) · pool without 1 image(s) | 0.95 of 16.6 GB | [report](04-random-idle-run3/report.md) |
| 05 | `random-idle-run4` | done | ceiling 360 hosts (ceiling between 360 and 370 hosts (370 failed)) · pool without 1 image(s) | 0.94 of 16.6 GB | [report](05-random-idle-run4/report.md) |
| 06 | `random-idle-run5` | done | ceiling 400 hosts (memory peaked at 91.0% at 400 hosts) · pool without 1 image(s) | 0.98 of 16.6 GB | [report](06-random-idle-run5/report.md) |
| 07 | `random-idle-run6` | done | ceiling 390 hosts (memory peaked at 91.9% at 390 hosts) · pool without 1 image(s) | 0.99 of 16.6 GB | [report](07-random-idle-run6/report.md) |
| 08 | `random-idle-run7` | done | ceiling 460 hosts (memory peaked at 91.2% at 460 hosts) · pool without 1 image(s) | 1.04 of 16.6 GB | [report](08-random-idle-run7/report.md) |
| 09 | `random-idle-run8` | done | ceiling 350 hosts (memory peaked at 90.0% at 350 hosts) · pool without 1 image(s) | 1.16 of 16.6 GB | [report](09-random-idle-run8/report.md) |
| 10 | `random-idle-run9` | done | ceiling 410 hosts (memory peaked at 91.5% at 410 hosts) · pool without 1 image(s) | 1.03 of 16.6 GB | [report](10-random-idle-run9/report.md) |
| 11 | `random-idle-run10` | done | ceiling 440 hosts (memory peaked at 90.8% at 440 hosts) · pool without 1 image(s) | 0.97 of 16.6 GB | [report](11-random-idle-run10/report.md) |

## Random climbs: `random-idle` (10 with a ceiling)

| Run | Seed | Ceiling hosts | Nodes | Peak memory % | MB / node | Deploy s / node |
|---|---:|---:|---:|---:|---:|---:|
| `random-idle-run1` | 1 | 490 | 510 | 80.9 | 23.1 | 0.523 |
| `random-idle-run2` | 2 | 630 | 655 | 82.8 | 18.5 | 0.621 |
| `random-idle-run3` | 3 | 350 | 365 | 93.3 | 25.9 | 1.768 |
| `random-idle-run4` | 4 | 360 | 375 | 88.7 | 26.0 | 1.806 |
| `random-idle-run5` | 5 | 400 | 416 | 91.0 | 21.3 | 2.131 |
| `random-idle-run6` | 6 | 390 | 405 | 91.9 | 26.9 | 2.379 |
| `random-idle-run7` | 7 | 460 | 480 | 91.2 | 25.1 | 2.570 |
| `random-idle-run8` | 8 | 350 | 365 | 90.0 | 28.9 | 2.369 |
| `random-idle-run9` | 9 | 410 | 428 | 91.5 | 26.2 | 2.929 |
| `random-idle-run10` | 10 | 440 | 458 | 90.8 | 24.4 | 3.305 |

Across runs (mean ± std, min–max):

- **Ceiling:** 428 ± 85 (350–630) hosts, 446 ± 88 (365–655) nodes
- **Peak memory:** 89.2 ± 4.1 (80.9–93.3) %
- **Memory per node:** 24.6 ± 3.0 (18.5–28.9) MB
- **Deploy per node:** 2.040 ± 0.903 (0.523–3.305) s

**Two Docker engines: don't average these 10 together.** Climbs 3–10 ran on Docker Desktop 4.45.0 (Docker 28.3.3) in October. Climbs 1–2 were rerun on 2026-10-25 on Docker Desktop 4.96.3 (Docker 29.9.2): the October ones were skewed by Modern Standby, and their reruns on 28.3.3 crashed Docker (see `../NOTES.md`). Docker 29 needs about a fifth less memory per node, deploys about 4× faster, and its climbs stop on memory stalls at ~82% memory instead of near 91%. The mean above mixes the two engines.

| Set | Climbs | Ceiling hosts | Nodes | Peak memory % | MB / node | Deploy s / node |
|---|---|---:|---:|---:|---:|---:|
| **Docker 28.3.3** (the result for this host) | 3–10 | **395 ± 41** (350–460) | 412 ± 43 | 91.0 ± 1.3 | 25.6 ± 2.2 | 2.40 ± 0.52 |
| Docker 29.9.2 | 1–2 | 560 ± 99 (490–630) | 583 ± 103 | 81.8 ± 1.3 | 20.8 ± 3.3 | 0.57 ± 0.07 |

Same seeds on both engines: seed 1 reached 460 on Docker 28 (October; a slow-deploy stop during standby) and 490 on Docker 29; seed 2 reached 410 (October, memory-bound) and 630. With October's climbs 1–2 included, Docker 28 gives 403 ± 42 hosts over 10 climbs. Those October results are kept in `02-random-idle-run1-standby/`, `03-random-idle-run2-standby/` and the manifest's `standby` records.

Share of nodes per type at the ceiling (mean ± std over runs):

| Type | Share |
|---|---:|
| switch | 10.1 ± 1.1 (8.2–11.5) % |
| plc | 7.4 ± 1.1 (6.1–9.3) % |
| database-server | 7.3 ± 1.2 (5.2–9.2) % |
| dns-server | 7.2 ± 0.8 (6.1–8.5) % |
| ftp-server | 7.2 ± 0.8 (6.1–8.3) % |
| router | 7.2 ± 0.9 (6.0–8.8) % |
| ids | 7.1 ± 1.2 (4.9–8.4) % |
| firewall | 7.0 ± 0.9 (5.7–8.2) % |
| web-server | 6.9 ± 1.1 (4.5–8.5) % |
| workstation | 6.7 ± 1.1 (5.1–8.4) % |
| file-server | 6.7 ± 1.2 (4.6–9.0) % |
| hmi | 6.6 ± 0.7 (5.9–8.3) % |
| attacker | 6.4 ± 0.8 (5.1–7.7) % |
| dhcp-server | 6.4 ± 1.1 (4.5–7.9) % |
