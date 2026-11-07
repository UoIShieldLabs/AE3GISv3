# Benchmark run notes: m4max-studio-dd12-95g

Status as of 2026-10-09 ~21:15 UTC. Procedure: `docs/benchmarks/RUNNING.md`.

## Machine

- Mac Studio, Apple M4 Max, 16 cores, 128 GB RAM, macOS (Darwin 24.6.0)
- Docker Desktop 4.47.0 (Docker 28.4.0), resources: **12 CPUs / 94.9 GiB**
- Docker restart: `docker desktop restart` (tested: back in ~7 s, no password, settings kept)
- Branch `feat/registry-images`, local commits on top of `1a66f9c` (not pushed):
  - `d98028b` traffic `max_hosts` 1000 → 3000 (since reverted, see below)
  - `ce3d1d4` traffic `max_hosts` back to 1000; random climb `max_factor` 2.0 → 1.25

## Pre-flight (2026-10-08)

- `./bench.sh check`: all OK after raising Docker memory (was 7.7 GiB) and
  removing Docker's `welcome-to-docker` demo container.
- Sanity run (`baseline/idle-sweep.json --scale 10`): 3 × 10 hosts, all ok,
  17–22 MB/node.
- Suites started 2026-10-08 18:10 UTC:
  `./bench.sh random --host m4max-studio-dd12-95g; ./bench.sh traffic --host m4max-studio-dd12-95g`

## Results so far (`2026-10-08-random/`)

| Run | Status | Ceiling (hosts) | Notes |
|---|---|---:|---|
| 01-census | done | – | 27 of 29 cases usable |
| 02-random-idle-run1 | done | **1140** | deploys failed at 1150–1340; stopped: memory 96.4% > 95% for 3 sweeps |
| 03-random-idle-run2 | done | **1200** | bracketed 1200 / 1210 |
| 04-random-idle-run3 | done | **1140** | bracketed 1140 / 1150 |
| 05-random-idle-run4 | failed | – | passed 790, 1100; jumped to 1630 hosts → Docker wedged |
| 06–08 (runs 5–7) | failed | – | "backend did not answer" (Docker broken by leftovers) |
| 09–11 (runs 8–10) | pending | – | run 8 crashed the runner at preflight |
| traffic suite | not started | – | preflight failed: Docker down |

Mean of the 3 finished climbs: ~1160 hosts. Memory peaked at only ~50–55%
on the steps that passed: **on this machine the ceiling is Docker/Kathara
deploying ~1200+ nodes (deploys time out after 45–60 min or the connection
drops), not memory.** Each climb takes 4–6 h (1200-node deploys take
2500–3500 s).

Images not available on this host (arm64): `ae3gis.local/zeek` (build fails:
no `zeekctl-6.0` package), `ae3gis.local/malicious-client` (amd64 only).
Both expected per RUNNING.md.

Census highlights (host MB/node): workstation/kathara-base 5.9, frr 25–27,
open-vswitch 38, suricata 93, firefox 434, wazuh-manager 573 (and 2.9 GB
disk/node; left out of the random mix), everything else 14–76.

## What went wrong

1. Climb 4 passed 1100 hosts, projected from memory, and stepped ×1.48 to
   1630 hosts (1690 nodes). dockerd hung mid-deploy; the step never cleaned up.
2. Left behind: **1967 exited containers and ~4737 Kathara networks**
   (`katharanp_vde` plugin) in 4 labs:
   `DDxocGtRuuF7j4yRJYTEXQ` (1440), `vsYtqNoxPDkMOGCa8DoXgw` (360),
   `zGddZTEFYV0OodkVY1eA` (84), `T0WfyT0eJ9RVa3zHwPkqA` (83).
3. With those loaded, dockerd grows to ~98 GB and the VM OOM-kills it
   (seen at 42 s and at 80 min after a restart, with nothing running), so
   every later run failed and the traffic suite couldn't start.
4. My earlier change of traffic `max_hosts` to 3000 was a mistake: this
   machine can't deploy much past ~1200 hosts, so probes at 2000+ would wedge
   Docker the same way. Reverted to 1000 (also comparable with the M4 Air).

## Fixes applied

- `random/random-idle.json`: `adaptive.max_factor` 2.0 → **1.25**, so a step
  overshoots the ~1200-host wall by ≤25% (climbs 1–3 failed cleanly at
  1150–1340; only the 1630 jump wedged Docker). Ceilings are still bracketed
  the same way.
- `suites/traffic.json`: `max_hosts` back to **1000**.
- The API purge of the 4 labs was blocked by Claude Code's auto-mode
  permission check; a CLI purge isn't possible because dockerd won't stay up.

## Resume (2026-10-09)

- Deleted the 1967 leftover Kathara containers (and their anonymous volumes)
  from the CLI. The 4737 leftover Kathara networks are **still there**
  (deleting them was blocked by the permission check; the user left before
  running it). If dockerd keeps dying, remove them:
  `docker network ls -q --filter label=app=kathara | xargs -n 100 docker network rm`
  or Docker Desktop → Troubleshoot → Clean / Purge data.
- Docker Desktop updated itself in between: engine **28.4.0 → 29.8.2**, so
  climbs 4–10 run on a newer engine than census + climbs 1–3.
- `./bench.sh check`: ready. Resumed detached at ~21:30 UTC:
  `random --resume --retry-failed`, then `traffic`.

## Next steps (as planned before the resume)

1. **Docker Desktop → Troubleshoot (bug icon) → Clean / Purge data**, all data
   stores. (Not "Reset to factory defaults": that resets resources.) Loses
   only images (rebuilt by the suite, ~10 min) and the backend DB volume (UI
   history). Results here are untouched; resume reads only these folders.
2. Check Docker is empty and still 12 CPUs / 95 GiB; `./bench.sh check`.
3. Resume, detached:
   ```bash
   H=m4max-studio-dd12-95g
   nohup sh -c "./bench.sh random --host $H --resume --retry-failed; ./bench.sh traffic --host $H" \
     >> backend/benchmark-results/$H/run.log 2>&1 &
   ```
   Keeps census + climbs 1–3, reruns climbs 4–10 (~30+ h), then traffic.
4. Watch climb 4 until its first step passes. If a failed step leaves labs
   behind again, purge them (`POST /api/v1/system/labs/{hash}/purge`) before
   the next restart.

## Progress 2026-10-12 17:40 UTC

- Random suite finished 2026-10-11 14:08 UTC. Ceilings: 1140, 1200, 1140
  (runs 1–3, Docker 28.4, before cleanup: not comparable), 2280, 2350,
  1640 (run 6: destroy_failed at 2050, not capacity), 2380, 2070, 2350, 2290.
  Clean runs 4,5,7–10: mean ≈ 2290 hosts; wall = deploys timing out at
  ~2400 hosts (~2450 nodes) with memory at ~75%.
- Traffic suite started 2026-10-11 14:11 UTC; at 17:40 next day 35 probes,
  14/100 cells done. Only ~12–15 cells look capped at ≥1000 (cs 50K row
  mostly); most low-rate cells fail at 1000 on traffic_short.
- To check after: 18 cell results "Not running: hX" (a node gone, delivered
  0%) are counted as traffic_failed; they look host-side and may understate
  some cells. Follow-ups: rerun climbs 1–3 and 6; capped cells with
  max_hosts ~2200.

## Traffic suite finished 2026-10-14 10:37 UTC

- 100/100 cells' limits found in 88 probes (~68 h). Grids in
  `2026-10-11-traffic/summary.md`. 15 cells ≥ 1000 (cs 50K row ×10, plus a
  few low-rate cells at 2000 ms / 250 ms).
- **18 cells' "fails at" come from a false failure**, not traffic:
  `RuntimeError: Not running: hX…` (services/traffic.py `prepare`: a
  client/server missing from `engine.node_pids`). 31 such rows in total; in
  26 of them later cells on the *same deployment with the same hosts* ran
  normally (e.g. r01-800: failed as cell 1, the next 42 cells all ok). So it
  is a transient miss in `node_pids` (Docker summaries / inspect under load),
  counted as `traffic_failed`. Affected cells (comfortable / fails):
  cs·tcp·250K·{100,250}ms, cs·udp·100K·{500,2000}ms,
  cs·udp·250K·{100,500,1000,2000}ms, cs·udp·500K·1000ms,
  mesh·tcp·50K·100ms, mesh·tcp·100K·2000ms, mesh·tcp·250K·{250,2000}ms,
  mesh·tcp·1M·500ms, mesh·udp·500K·{250,500}ms, mesh·udp·1M·{250,1000}ms.
  Their limits are lower bounds; re-measure after making the check retry.

## Repair + resume 2026-10-14

- Fix on branch `fix/traffic-node-check`, commit `ab6c037` (not pushed):
  traffic prepare looks a missing node up again (2 s, 5 s, 10 s) before
  "Not running"; `node_pids` retries a failed inspect once; a limit search asks
  a size again once when its whole deployment fails. 349 backend tests pass.
- Repaired `2026-10-11-traffic/manifest.json` (backup:
  `manifest.before-repair.json`): dropped 34 false failures (31 "Not running"
  rows + the cells of r05-350 and r09-550, whose deploys lost the Docker
  connection), reopening 24 cells; the dropped list is in the run's `repaired`
  field. Script: kept outside the repo (one-off).
- Resumed with `./bench.sh traffic --host m4max-studio-dd12-95g --resume`
  (max_hosts still 1000). The manifest's `git` now names `ab6c037`; probes
  before it ran at `ce3d1d4`.
- Random climbs were not affected (readiness skips nodes without a pid).

## Re-search after the repair — finished 2026-10-15 20:04 UTC

- 49 new probes (rounds 11–18, 137 in all), all 100 cells' limits found, `summary.md` regenerated (AE3GIS `ab6c037`).
- **No "Not running" rows** in any new probe: the node-lookup retry fixed it.
- 3 deployments still lost to `ConnectionError: Connection aborted` (r12-450, r12-600, r13-450). The new rule retried them:
  - r12-600 (mesh·udp·500K·250ms) passed on the retry.
  - cs·tcp·250K·100ms lost 450 twice, so it reads `400 / 450 mem`. It also failed 500 on traffic, and all its row neighbours are 400/450 on traffic, so the number stands but the `mem` label is a Docker glitch, not memory.
- 17 cells changed (before-repair → now, comfortable/fails-at):
  cs·tcp·250K·250ms 350/400→400/450, cs·tcp·250K·500ms 300/350→400/450, cs·udp·100K·500ms 550/600→950/1000,
  cs·udp·100K·2000ms 700/750→≥1000, cs·udp·250K·100ms 450/500→550/600, cs·udp·250K·500ms 600/650→650/700,
  cs·udp·250K·1000ms 650/700→700/750, mesh·tcp·50K·100ms 750/800→900/950, mesh·tcp·250K·2000ms 500/550→800/850,
  mesh·tcp·500K·1000ms 500/550→600/650, mesh·tcp·1M·500ms 250/300→300/350, mesh·udp·500K·100ms 750/800→800/850,
  mesh·udp·500K·250ms 400/450→850/900, mesh·udp·500K·500ms 600/650→900/950, mesh·udp·1M·250ms 350/400→500/550,
  mesh·udp·1M·1000ms 350/400→450/500, mesh·udp·1M·2000ms 450/500→500/550.

The commits were later rewritten without the co-author line: `ab6c037`, named in the traffic results, is the same code as `f7d795d` on `benchmarking/m4-max-mac-studio`.

## Random climbs 1, 2, 3, 6, 8 rerun — 2026-10-24 00:03 → 2026-10-25 01:48 UTC

Rerun because runs 1–3 ran on Docker 28.4 with thousands of leftover containers, run 6 stopped on destroy_failed, and run 8 on one dropped connection. They ran on a copy of the suite folder (the results are tracked, so writing into them would dirty the tree), and were copied back. Each rerun climb's old outcome is in the manifest under `previous`.

| Climb | Before | Rerun |
|---|---:|---|
| 1 | 1140 | 2240 |
| 2 | 1200 | 2320 (deploy timeout) |
| 3 | 1140 | 1620: destroy_failed at 2020 ("Still running: h4_48"), not capacity |
| 6 | 1640 (destroy_failed) | 2360 (deploy timeout) |
| 8 | 2070 (dropped connection) | 2320 |

Ceiling across all 10 is now 2251 ± 226 hosts. Excluding climb 3, it is about 2320 (2240–2380). destroy_failed has now stopped 2 of about 15 climbs: a destroy that leaves a node running ends the climb instead of being retried.

## Climb 3 rerun after the destroy fix — 2026-10-26 17:54 → 2026-10-27 01:32 UTC

The fix: `3af8219`, destroy removes leftovers again before failing. Climb 3 reached **2340 hosts**: 2340 passed, 2350 timed out on deploy, and every teardown went through. Its earlier outcomes are in the manifest under `previous` and `previous_2`.

All 10 climbs are now clean. The ceiling is **2323 ± 42 hosts** (2240–2380), 2407 ± 44 nodes. Peak memory is 77.5 ± 2.3%. Every climb stops on deploys timing out (Docker Desktop's wall), not on memory.

The summary's AE3GIS commit (`3af8219`) is the last one the suite ran on. Climbs 4, 5, 7, 9 and 10 ran on `ce3d1d4` (code since rewritten as `7494467`), climbs 1, 2, 6 and 8 on `dc84707`, and climb 3 on `3af8219`. The differences only touch traffic runs and teardown retries.
