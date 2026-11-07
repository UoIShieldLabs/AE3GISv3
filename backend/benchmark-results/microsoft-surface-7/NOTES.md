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

## AE3GIS vs GNS3 (`2026-11-06-compare/`)

2026-11-06, 10:42 → 19:15 local, procedure `docs/benchmarks/COMPARE.md`,
`first: gns3` (the Air went `ae3gis` first). Log: `2026-11-06-compare.log`.

- **Setup:** Docker Desktop with Docker 29.9.2 (updated since the suites
  above), `.wslconfig` 8 CPUs / 16 GB; the GNS3 VM in VirtualBox 7.1.12 (on
  Hyper-V, since WSL 2 is on), resized from 6 CPUs / 10 GB to the same 8 /
  16 GB. Both report 15.6 GB.
- **GNS3 2.2.56.1**, not the Air's 2.2.54 (the VM installed here).
- **Host memory on WSL 2 isn't a high-water mark.** `memcheck`: VirtualBox's
  footprint rose by 2.0 GiB and stayed after "freed", as on macOS; Docker
  Desktop's rose by 2.0 GiB and went back to Windows within ~10 s. So E1's
  "host footprint" at hold is memory in use for AE3GIS but the peak since the
  VM started for GNS3; peak growth (`host_footprint_peak_growth`) is the
  like-for-like figure here. WSL was left at its defaults (Docker Desktop as
  it ships).
- **Runner fixes for Windows**, found in the checks and the dry run
  (`2026-11-06-compare-quick`, not committed): `ff12f7f` (the probe's build
  context as ustar, a GNS3 VM whose Docker hangs over SSH while booting, the
  ARP limits set from the `docker-desktop` distro since Docker's host network
  on WSL isn't the initial namespace, summary.md as UTF-8). The run started at
  `ff12f7f`.
- **`ae3gis e1-h800-r2`: error.** The lab deployed (464 s) and was ready
  (1632/1632), but its teardown hung dockerd: 472 `docker ps` handlers stuck
  refreshing images through ~3,800 containerd `content.Info` calls (the
  containerd image store is on), with 4 GB of 16 used and no OOM. The destroy
  hit the 45 min cap, then the runner blocked on `docker info` (no timeout).
  The runner was stopped, Docker restarted, the leftover lab (231 containers
  back up with the VM) destroyed and deleted through the backend, and the run
  resumed at `19356a4` (14:08): `docker info` with a timeout, and leftovers
  cleared after every AE3GIS VM restart. Rounds 1 and 3 at 800 hosts were ok
  (1128 s and 1148 s).

  **Re-run on 2026-11-07** (10:44 → 11:02, `run --resume --only e1` at
  `7f93128`, the same runner code as `e936e7a`): ok in 1088 s (deploy 398 s,
  ready 1632/1632, teardown 430 s). The failed attempt's record is kept in
  `attempts/ae3gis-e1-h800-r2-attempt1.json`, outside the step folders, so the
  summary's 800-host row is now 3/3. The re-run went after every other step,
  a day later, and not between its round's neighbours as the plan orders it.
- **GNS3 at 800 hosts:** skipped in every round (projected memory over 85%
  of the VM), as on the Air.
- Every other step is ok, with readiness 100% on both platforms.
- **Commit ids:** the run's `manifest.json` and `summary.md` name `ff12f7f`
  and `19356a4`, the commits as they were on this machine. They were rebased
  before the push and are `f49a32b` and `e936e7a` on the branch, with the same
  code (the rebase only added the Air's `REPORT.md` underneath).

## Left out

- `aborted-2026-10-08-random/`, `aborted-run.log`: a cancelled first start of
  the random suite.
- `2026-10-09-traffic/`, `aborted-2026-10-10-traffic/`: run logs only, from
  traffic starts that stopped while bringing the backend up (the random suite
  wasn't finished yet).
- The `export.zip` files (raw samples): kept on the machine.
- `2026-11-06-compare-quick/`: the comparison's dry run.
- The dockerd goroutine dump from the 800-host teardown hang (31 MB): not kept.
