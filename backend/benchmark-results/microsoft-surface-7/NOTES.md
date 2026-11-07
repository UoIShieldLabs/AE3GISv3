# Benchmark run notes: microsoft-surface-7

Random idle and traffic suites, 2026-10-08 → 2026-10-14; random climbs 1–2
rerun on 2026-10-25. Procedure:
`docs/benchmarks/RUNNING.md`.

## Machine

- Microsoft Surface Laptop 7, Intel Core Ultra 7 268V (8 cores), 32 GB RAM, Windows 11
- Docker Desktop 4.45.0 (Docker 28.3.3) on WSL2, kernel 6.6.87.2-microsoft-standard-WSL2.
  Resources are WSL's defaults (no `.wslconfig`): **8 CPUs / 15.8 GiB** (16.6 GB), 4 GiB swap.
  Everything but random climbs 1–2 ran on these versions; the reruns of climbs
  1–2 ran on Docker Desktop 4.96.3 (Docker 29.9.2), with the same WSL 2.5.10
  and kernel.
- Docker restart: `docker desktop restart`
- Run from Git Bash with Windows Python, branch `benchmarking/windows`
  (fixes on top of `1a66f9c`):
  - `d3ccc92` run the suites from a Windows checkout (LF line endings, UTF-8 output)
  - `5e9fe22` the traffic suite on Docker Desktop for Windows (ARP limits set from the `docker-desktop` distro)
  - `20c8b9e` a failed Docker restart is tried again; the suite stops if Docker stays down
  - `f6638a8` traffic `quiet_timeout_s` 1200 → 180 s (see below)
- `ae3gis.local/zeek` doesn't build (its Zeek 6.0 packages are gone), so the
  random pool has one image less. Every other image, malicious-client
  included, ran (amd64).

## Random (`2026-10-08-random/`)

**Docker 28.3.3, climbs 3–10: 395 ± 41 hosts** (350, 360, 400, 390, 460, 350,
410, 440). Memory is the wall: climbs peak at 89–93% host memory, 21–29 MB/node.
With October's standby-skewed climbs 1–2 (460, 410) it is 403 ± 42 over 10.

Climbs 1–2 rerun on Docker 29.9.2: 490 and 630 hosts. They're a separate set:
`summary.md` splits the climbs by engine (its runner-made mean over all 10,
428 ± 85, mixes the two).

- **Climbs 1–2: timings skewed.** The charger was unplugged at 18:15 UTC on
  10-08, and the laptop sat in Modern Standby from 18:19 to 00:28 UTC. Their
  deploy, destroy, ready and CPU figures are off; memory figures are fine.
  Climb 1's ceiling (460) comes from a slow deploy, not memory. Kept as
  `02-random-idle-run1-standby/`, `03-random-idle-run2-standby/` and the
  manifest's `standby` records; rerun on 2026-10-25 (below).
- **Climb 10 took four attempts:**
  - Attempt 1: dockerd panicked at 470 hosts on 10-09.
  - Attempt 2: started after a Windows Update reboot on 10-10, with the crashed
    lab's 466 stopped containers still there (2.64 GB at rest). Cancelled as
    invalid (`11-random-idle-run10-invalid`).
  - Attempt 3: com.docker.backend.exe crashed (access violation) during
    teardown at 23:37 UTC on 10-10 (`-crashed`). A hung orphan `wsl.exe` had
    also blocked `docker desktop restart` and crashed the runner (`-cancelled`).
  - Attempt 4: the counted result, ceiling 440.

  The manifest records each attempt; `manifest.before-run10-rerun{,2,3}.json`
  are the manifests before each retry.
- Climbs 1–9 ran at `d3ccc92`, climb 10's last attempt at `20c8b9e` (the
  runner fix only; the measurement is unchanged).

## Rerun of random climbs 1–2 (2026-10-25)

- **First try, Docker 28.3.3:** climb 1 lost the backend while deploying its
  200-host step. Docker held 1371 leftover empty Kathara networks from the
  earlier crashes and 2.4 GB at rest, and deployed 3× slower than in October.
  The runner then started climb 2 on climb 1's 56 stopped containers (3.2 GB at
  rest), so it was cancelled (`02-…-failed`, `03-…-cancelled`). The leftover lab
  and 1055 empty networks were removed, and Docker was back to 0.9 GB at rest.
- **Second try, Docker 28.3.3:** climb 1 crashed Docker again at 200 hosts:
  dockerd and the VM's init died in the same second with Go's `fatal error:
  runtime: name offset base pointer out of range`, the error of the 10-09
  dockerd panic (`02-…-crashed`). Two programs failing alike at once points to
  memory corruption in the WSL VM; Windows logged no hardware errors.
- **Third try, Docker 29.9.2** (Docker Desktop updated to 4.96.3; WSL stayed
  2.5.10): both climbs finished, ceiling 490 (seed 1) and 630 (seed 2). Docker
  29 needs about a fifth less memory per node (20.8 vs 25.6 MB at the
  ceiling), deploys about 4× faster per node, and the climbs stop on memory
  stalls at ~82% memory instead of near 91%. Kept as a separate set, not
  averaged with climbs 3–10.
- Each try's manifest is kept as `manifest.before-run1-2-rerun{,2,3}.json`, and
  each failed attempt as a `rerun_*` record on its run. The runner recorded
  `b14a3c4`, which has the same code as `f6638a8`.

## Traffic (`2026-10-11-traffic/`)

All 100 cells' limits found in 59 probes (10-11 10:09 → 10-14 01:31 UTC).
Grids and notes in `summary.md`.

- **450 hosts is a deploy wall.** Every probe of 450 hosts or more (479–690
  nodes) stopped at deploy after 1876–3604 s, before any cell ran. So
  `400 / 450 mem` means "never degraded up to the most this host deploys in
  time", not a memory limit.
- **Quiet wait shortened from round 4 on.** `quiet_timeout_s` was 1200 s
  through round 3's 100-host probe and 180 s after (suite override in
  `suites/traffic.json`; each probe's `spec.json` records it). With fans, the
  host settled within 2 minutes after deploys and cells. From about 260 hosts
  up, its CPU floor stays above the 10% threshold, so the longer wait only
  added idle time. The 60 s idle gap before each cell is unchanged.
- **Docker's VM hung** (out of memory at 16.2 GB, no VM log after 23:01 UTC on
  10-12) while tearing down round 4's 500-host probe. The runner was stopped,
  the VM terminated (`wsl -t docker-desktop`), Docker Desktop restarted by
  hand, the leftover lab destroyed, and the suite resumed at 04:52 UTC on
  10-13. The interrupted probe's cells were asked again in round 5.
- No "Not running" false failures (the bug fixed by `f7d795d` on
  `benchmarking/m4-max-mac-studio`) appear in this run.

## Left out

- `aborted-2026-10-08-random/`, `aborted-run.log`: a cancelled first start of
  the random suite.
- `2026-10-09-traffic/`, `aborted-2026-10-10-traffic/`: run logs only, from
  traffic starts that stopped while bringing the backend up (the random suite
  wasn't finished yet).
- The `export.zip` files (raw samples): kept on the machine.
