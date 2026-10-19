# Benchmark run notes: m4-macbook-air

Status as of 2026-10-19:
- **`random`:** finished.
- **`traffic`:** 90 of 100 cells final. A re-measure of 13 cells is paused, and this branch will be updated when it finishes.

Procedure: `docs/benchmarks/RUNNING.md`.

## Machine

- **Hardware:** MacBook Air 15" (Mac16,13), Apple M4 (10 cores), 32 GB, fanless; macOS 26.7.1.
- **Docker:** Docker Desktop 4.95.0 (Docker 29.8.2), resources **8 CPUs / 16.7 GB**. Restarted with `docker desktop restart`.
- **Power:** on AC with the lid open for every measurement. Runs were paused (probe cancelled, lab removed) whenever the Mac had to travel, and resumed with `--resume <folder>`.
- **Code:** the suites ran from a separate worktree on `feat/bench-suites` with its own compose project (`ae3gis-bench`), so the dev checkout and its database were untouched. Each manifest records the commit.

## `2026-10-06-random/`: idle capacity (commit `0c8ac80e`)

- **Census:** 27 of 29 image cases usable. `ae3gis.local/zeek` doesn't build on arm64 (no `zeekctl-6.0` package), and `ae3gis.local/malicious-client` is amd64-only.
- **10 random-mix climbs, every type with equal odds:** ceiling **530 ± 73 hosts** (450–700), 22.8 ± 3.3 MB/node, 0.33 s deploy per node. Every climb ended at about 90% memory.
- **What drives the spread:** how many heavy images a draw has; firefox matters most (5 → 700 hosts, 13 → 450).
- **Earlier attempt, left out:** `2026-10-06-random-aborted-disk-full` (kept on the machine). Docker's disk filled at ~270 hosts because every Wazuh manager unpacks a 2–3 GB CVE feed. Wazuh (siem) was dropped from the random mix (the census still measures it), and steps now stop at 90% disk.

## `2026-10-07-traffic/`: burst limits

100 cells: 5 rates × 5 burst intervals × TCP/UDP × clients → servers / mesh. For each, the search finds the most hosts that still deliver ≥ 95% with ≤ 1% UDP loss, and where it fails, 50 hosts apart. The search tops out at 1000 hosts.

Read `2026-10-07-traffic/findings.md` first: grids, what limits each scenario, and caveats. `summary.md` has the grids as they stand.

What happened along the way, in order:

1. **Thermal:** back-to-back heavy cells heated the fanless chip (the same traffic cost 15–60% more CPU). Every cell now waits for a quiet host (up to 20 min), then idles a minute. The unrested attempt `2026-10-07-traffic-aborted-thermal` is left out.
2. **ARP table:** Docker's VM caps neighbour entries at 1024 for all nodes together, which cut mesh off past ~250 hosts and clients → servers past ~500. The suite now raises it to 16384 after every Docker restart. The default-kernel attempt `2026-10-07-traffic-aborted-arp` is left out.
3. **Traffic driver, fixed 2026-10-12 (`43f30468`):** the old driver started ~40 processes a second, and the 50 s window began 5 s after the request. In labs of 500+ hosts much of the window ran at partial load, or with clients that never started.
   - The fixed driver starts ~2000 a second, and the window waits for every client.
   - 54 cells measured that way were searched again. A spot check reproduced 4 of the 46 kept cells exactly.
4. **Old driver's memory stalls, re-check added 2026-10-19 (`9517ee62`):** that driver also forked itself for every process, which stalled memory: full PSI ~25% median in mesh labs of 500–800 hosts at ~60% memory, against 0 now.
   - 30 results measured under those stalls were dropped, and 13 cells are being searched again (10 still open).
   - Several now pass well above their old limits.
5. **Pauses:** the search was paused several times, with the in-progress probe cancelled. A cancelled probe's cells are simply asked again.

Also left out: `2026-10-06-traffic-matrix-100hosts`, the first matrix design (every cell at 100 hosts), superseded by the limit search. The raw `export.zip` files and those older folders stay on the machine.

## Logs

- **`random-traffic.log`:** the random suite and the first traffic matrix.
- **`traffic-limits.log`:** the traffic limit search, every resume included.
