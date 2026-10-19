> **Superseded:** these are partial results from before the traffic driver fix (2026-10-12). See `findings.md` and `summary.md` for the final results.

# Traffic limits on the M4 MacBook Air: partial results

**Status (2026-10-09, 15:33 UTC):** paused, with **63 of 100 cells final**.

- **Run so far:** about 30 h of running over three days (started 2026-10-07 23:41 UTC). 54 lab sizes measured.
- **Remaining:** 37 cells, nearly all at 700–1000 hosts. That's another 18–24 h.
- **When it finishes:** the runner writes the final `summary.md` next to this file.

## Setup

- **Machine:** M4 MacBook Air 15" (fanless), Docker Desktop VM with 8 CPUs and 16.7 GB, Kathará.
  - AE3GIS runner `59892984`, then `9f7bf000` after the resume fix. That fix touched only the runner; the backend and specs are unchanged.
  - Neighbour (ARP) table raised to 16384 entries.
- **Lab:** a generated campus of workstation hosts (`kathara/base`), 200 per subnet and 48 per switch, plus one server per 50 hosts in a server subnet, behind routers and a core.
  - "Hosts" below counts the traffic hosts; deployed nodes are about 6% more (742 nodes at 700 hosts).
- **Traffic:** iperf3 3.19.1 paced bursts. Every interval, each flow sends *rate × interval* bytes at once.
  - **cs (clients → servers):** every host sends one flow to a server, north–south through the routers and the core.
  - **mesh:** every host sends to its next two neighbours, east–west inside its LAN (2 flows per host).
- **Each cell:** deploy N hosts; wait for a quiet host (CPU < 10%, up to 20 min); idle 60 s; then 5 s ramp-up + 50 s measured hold.
  - **Pass:** at least 95% of the offered traffic delivered, and UDP loss ≤ 1%.
  - **Host limits:** memory > 90%, memory stalls > 10% or disk > 90% stop a cell as a host limit, not a traffic one.
- **Search:** start near a cost-model estimate, grow by 25% while passing, then bisect to 50 hosts.
  - The comfortable size must pass twice.
  - Docker is restarted before every size, so pauses carry no state over.

## Headline findings

1. **At 250 kb/s per host and up, the limit is a total-throughput budget, not a host count.** Hosts × rate stays about constant: halving the rate about doubles the hosts.
   - cs TCP: 50 hosts at 1 Mb/s, 150 at 500K, 250 at 250K, 500–550 at 100K. All carry 50–75 Mb/s.
2. **North–south costs about 3× more than east–west.** Mesh carries 200–400 Mb/s; clients → servers carries 50–100 Mb/s.
   - A cs byte crosses switch → router → core → router → switch: nodes receive it about 6 times.
   - A mesh byte crosses one switch: nodes receive it about 2 times.
3. **UDP holds 1.5–2× the hosts of TCP at high rates.**
   - cs: 100 vs 50 at 1M, 200 vs 150 at 500K, 350 vs 250 at 250K.
   - mesh: 150–200 vs 100 at 1M, 250–350 vs 200 at 500K.
4. **The burst interval matters for UDP, not for TCP.**
   - TCP rows are flat across intervals. Neighbours that differ by one 50-host step, like cs TCP 100K, are within the search's resolution.
   - For UDP at ≤ 500K (mesh) or ≤ 250K (cs), longer intervals fit more hosts:
     - mesh UDP 500K: 250 → 300 → 350 hosts (100 → 250 → ≥ 500 ms);
     - mesh UDP 250K: 450 → 500 → 600 → ≥ 700;
     - cs UDP 100K: 500–550 at ≤ 500 ms vs 750 at ≥ 1 s;
     - cs UDP 50K: 700 at 100 ms vs ≥ 1000 at ≥ 500 ms.
   - The likely cause is per-burst overhead: a flow at 100 ms wakes and sends 20× as often as one at 2 s. This matches the 100-host matrix, where short bursts cost more CPU at low rates, but it hasn't been isolated.
5. **Below about 100 kb/s per host, memory takes over.** The search climbs to 700–1000 hosts.
   - Memory sits at 70–90% (an idle 1000-host lab already uses 14.4 of 16.7 GB).
   - Failures change shape: whole flows die (ratio 0) and memory stalls appear.
6. **TCP latency degrades well before delivery does.** At the comfortable size:
   - cs TCP at 1M has an RTT p95 of 6–13 ms, but 100–315 ms in most cells at ≤ 500K;
   - mesh TCP 250K at 100 ms reaches 3 s.
   - A 95%-delivered limit is generous for latency-sensitive traffic. RTT p95 is in every probe's report.
7. **The high-rate limits reproduce.** The earlier attempt on the default kernel (2026-10-07, separate Docker sessions) also bracketed 37 of these high-rate cells. 35 match exactly and 2 differ by one step.
   - Examples that match: all 15 cs TCP cells at 1M–250K (50 / 150 / 250 hosts), and mesh TCP at 1M and 500K (100 / 200).

## Limits: comfortable / fails at (hosts)

How to read the cells:
- **comfortable / fails at:** passed twice at the first number, first fell below the threshold at the second, 50 hosts apart.
- **`…`:** still being searched.
- **`mem`:** a host limit (memory stalls, or a cell a stop criterion never reached), not traffic.
- **`≥ N`:** passed at N and still climbing; 1000 is the search's cap.

**cs · tcp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 800 / 1000 … | 800 / 1000 … | 800 / 1000 … | 800 / 1000 … | ≥ 1000 … |
| 100K | 550 / 600 | 500 / 550 | 550 / 600 | 500 / 550 | 550 / 600 |
| 250K | 250 / 300 | 250 / 300 | 250 / 300 | 250 / 300 | 250 / 300 |
| 500K | 150 / 200 | 150 / 200 | 150 / 200 | 150 / 200 | 150 / 200 |
| 1M | 50 / 100 | 50 / 100 | 50 / 100 | 50 / 100 | 50 / 100 |

**cs · udp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 700 / 750 … | 800 / 1000 … | ≥ 1000 … | ≥ 1000 … | ≥ 1000 … |
| 100K | 500 / 650 … | 550 / 600 … | 500 / 650 … | 750 / 800 … | 750 / 800 … |
| 250K | 300 / 350 | 250 / 350 … | 350 / 400 | 350 / 400 | 350 / 400 |
| 500K | 200 / 250 | 200 / 250 | 150 / 200 | 200 / 250 | 200 / 250 |
| 1M | 100 / 150 | 100 / 150 | 100 / 150 | 100 / 150 | 100 / 150 |

**mesh · tcp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | 650 / 700 … | ≥ 700 … | ≥ 700 … | ≥ 700 … | ≥ 700 … |
| 100K | 700 / 900 … | ≥ 700 … | 700 / 900 mem … | 700 / 900 … | ≥ 700 … |
| 250K | 400 / 450 | 350 / 400 | 350 / 450 … | 350 / 450 … | 400 / 450 |
| 500K | 200 / 250 | 200 / 250 | 200 / 250 | 200 / 250 | 200 / 250 |
| 1M | 100 / 150 | 100 / 150 | 100 / 150 | 100 / 150 | 100 / 150 |

**mesh · udp**

| rate \ interval | 100 ms | 250 ms | 500 ms | 1000 ms | 2000 ms |
|---|---:|---:|---:|---:|---:|
| 50K | ≥ 700 … | ≥ 700 … | 650 / 700 mem | ≥ 700 … | ≥ 700 … |
| 100K | 700 / 900 … | 500 / 550 mem | 500 / 550 mem | ≥ 700 … | ≥ 700 … |
| 250K | 450 / 500 … | 500 / 550 | 500 / 550 mem | 600 / 650 | ≥ 700 … |
| 500K | 250 / 300 | 300 / 350 | 350 / 400 | 350 / 400 | 350 / 400 |
| 1M | 150 / 200 | 150 / 200 | 200 / 250 | 150 / 200 | 200 / 250 |

## Traffic carried at the comfortable size

Offered traffic in Mb/s (hosts × rate × flows per host), as a range across the five intervals. The budget effect shows as a flat row from 250K up.

| scenario | 1M | 500K | 250K | 100K | 50K |
|---|---:|---:|---:|---:|---:|
| cs · tcp | 50 | 75 | 62 | 50–55 | 40–50 … |
| cs · udp | 100 | 75–100 | 62–88 … | 50–75 … | 35–50 … |
| mesh · tcp | 200 | 200 | 175–200 … | 140 … | 65–70 … |
| mesh · udp | 300–400 | 250–350 | 225–350 … | 100–140 … | 65–70 … |

## Why: CPU per delivered megabit

The CPU the lab's containers use per 100 Mb/s delivered, from the passing cells at 1M and 500K:

| scenario | lab CPU per 100 Mb/s | node receives per delivered byte | predicted ceiling at ~6.5 cores | measured (comfortable / fails) |
|---|---:|---:|---:|---:|
| cs · tcp | 7.5 cores | 6.4× | ~85 Mb/s | 75 / 100 |
| cs · udp | 4.3 cores | 6.1× | ~150 Mb/s | 100 / 125–150 |
| mesh · tcp | 2.6 cores | 2.1× | ~250 Mb/s | 200 / 250–300 |
| mesh · udp | 1.8 cores | 1.9× | ~350 Mb/s | 300–400 / 400–500 |

At the high-rate failures, host CPU is mostly at 85–100%. The cost per megabit, times about 6.5 usable cores, puts each scenario's ceiling between or at the edge of its comfortable and failing sizes. cs UDP sits at the edge because it starts losing packets before the CPU saturates. So at high rates **this machine is CPU-bound**, and the cost is set by the number of hops and by TCP versus UDP. The burst interval doesn't change it.

## How the cells fail

- **≥ 250K per host (CPU-bound):**
  - TCP delivers 67–94% at the failing size, with no failed flows.
  - UDP loses up to 28%, or falls short on delivery.
  - Host CPU is 85–100%; cs UDP fails at 68–90%, where loss crosses 1% first. Memory stays at or under 55%.
- **≤ 100K per host (memory-bound):**
  - at 700–1000 hosts, memory reaches 70–90%;
  - memory stalls (PSI) appear;
  - some flows fail outright (ratio 0, up to 25 flows with errors).
- **The `mem` cells at 500–700 hosts** (mesh UDP 100K at 250/500 ms, 250K at 500 ms, 50K at 500 ms) are the odd ones out.
  - Each was stopped by memory stalls while memory use was only 53–64%, or never reached because another cell's stall ended the probe.
  - Neighbouring cells pass at 700 hosts, so treat these as lower bounds.
  - The stalls aren't explained yet; they're worth rechecking.

## Lab cost by size (idle, before traffic)

| hosts | nodes | deploy | destroy | memory after settle |
|---:|---:|---:|---:|---:|
| 100 | 109 | 13 s | 7 s | 2.5 GB |
| 250 | 268 | 40 s | 31 s | 4.4 GB |
| 500 | 531 | 109 s | 97 s | 7.9 GB |
| 800 | 846 | 238 s | 195 s | 12.3 GB |
| 1000 | 1057 | 379 s | 397 s | 14.4 GB |

- **Memory per node:** constant at 15.7 MB for these workstation nodes.
- **Deploy time per node:** grows from 0.12 s at 50 hosts to 0.36 s at 1000.
- **Quiet wait:** from about 750 hosts up, the idle lab alone keeps the host above the 10% "quiet" threshold. Every cell then waits the full 20 minutes, which is why the remaining cells are slow.

## Still to measure (37 cells)

| scenario | open cells |
|---|---|
| cs · tcp | all of 50K (they want 900; 2000 ms wants its second pass at 1000) |
| cs · udp | all of 50K and 100K, plus 250K · 250 ms |
| mesh · tcp | all of 50K and 100K, plus 250K · 500 and 1000 ms |
| mesh · udp | 50K at 100/250/1000/2000 ms, 100K at 100/1000/2000 ms, 250K at 100/2000 ms |

The rows from 250K to 1M are essentially complete. What's left decides where the low-rate, memory-bound limits sit, between 700 and 1000 hosts.

## Caveats

- **Resolution:** each size is measured once, plus a second pass at the comfortable size. Limits are ±50 hosts, so neighbours that differ by one step are equal within resolution.
- **Delivered above 100%** at long intervals (up to 108% at 2 s) is an artifact of the 50 s hold: the first burst goes out at once. It doesn't flip any pass or fail.
- **Lab composition:** only workstation (`kathara/base`) nodes. Heavier images lower the memory-bound limits; the random idle mix costs 22.8 MB per node vs 15.7 MB here.
- **Pauses and heat:** the run spans three days and two pauses. Docker is restarted before every size, and every cell starts from a rested, quiet host. The fanless chip throttled under back-to-back heavy cells in an earlier attempt, so cells rest first.

## Also finished on this machine: idle capacity (`random` suite, 2026-10-06)

- **Random mix of every node type (equal odds), 10 climbs:** a ceiling of **530 ± 73 hosts** (450–700), 22.8 ± 3.3 MB per node and 0.33 s deploy per node. Every climb ended at about 90% memory.
- **The spread** comes mostly from the heavy images in each draw; the firefox count matters most (5 → 700 hosts, 13 → 450).
- **Image census:** 27 of 29 images usable on arm64. `malicious-client` is amd64-only, and `zeek` doesn't build on arm64 today.
- **Full report:** `../2026-10-06-random/summary.md`.

## Files

- **This run:** `backend/benchmark-results/m4-macbook-air/2026-10-07-traffic/`.
  - `manifest.json` holds every cell's passes and failures.
  - `01-burst-limits/rNN-<hosts>/` holds each probe's `report.md`, `benchmark.json` (per-cell rows: delivered, loss, RTT, CPU, memory, PSI) and `export.zip`.
- **Log:** `backend/benchmark-results/m4-macbook-air/traffic-limits.log`.
- **Earlier attempts, kept for reference:**
  - `2026-10-07-traffic-aborted-arp`: default kernel. Low-rate limits there were capped by the ARP table.
  - `2026-10-07-traffic-aborted-thermal`: cells back to back, without the quiet wait and idle minute.
  - `2026-10-06-traffic-matrix-100hosts`: the first matrix, all cells at 100 hosts.
