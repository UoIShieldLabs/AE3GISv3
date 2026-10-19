# Benchmark run notes: microsoft-surface-7

Random idle and traffic suites, 2026-10-08 → 2026-10-14. Procedure:
`docs/benchmarks/RUNNING.md`.

## Machine

- Microsoft Surface Laptop 7, Intel Core Ultra 7 268V (8 cores), 32 GB RAM, Windows 11
- Docker Desktop 4.45.0 (Docker 28.3.3) on WSL2, kernel 6.6.87.2-microsoft-standard-WSL2.
  Resources are WSL's defaults (no `.wslconfig`): **8 CPUs / 15.8 GiB** (16.6 GB), 4 GiB swap
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

Ceilings 460, 410, 350, 360, 400, 390, 460, 350, 410, 440: **403 ± 42 hosts**.
Memory is the wall: climbs peak at 89–93% host memory, 18–26 MB/node.

- **Climbs 1–2: timings skewed.** The charger was unplugged at 18:15 UTC on
  10-08, and the laptop sat in Modern Standby from 18:19 to 00:28 UTC. Their
  deploy, destroy, ready and CPU figures are off; memory figures are fine.
  Climb 1's ceiling (460) comes from a slow deploy, not memory. They were not
  rerun.
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
