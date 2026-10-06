# Benchmarking AE3GIS, Kathará and Docker

How much does a node cost, how many fit on a machine, how long do they take to
deploy, and what happens under load? AE3GIS answers with three tools that work
alone or together:

| Tool | What it does | Where |
|---|---|---|
| **Monitor** | Records CPU, memory and network of chosen nodes, the host (on Docker Desktop: its Linux VM) and Docker's own processes, every N seconds | Dock tab (⌘K → *Start monitor*, or right-click a node) · `POST /topologies/{id}/monitors` |
| **Traffic** | Generates iperf3 load: picked flows, clients → servers, or a mesh; hundreds of flows from one driver container | Dock tab (⌘K → *New traffic run*) · `POST /topologies/{id}/traffic/runs` |
| **Benchmark** | Generated topologies deployed, checked, loaded and measured step by step: sweeps of growing size, climbs to the host's limit, image censuses, traffic matrices | Headless: `./bench.sh` (a suite per host) or `backend/scripts/bench.py` (one spec) · results on the Library page (*Benchmarks*) |

This page is about benchmarks: how to run them on a machine, what the numbers
mean, and how to get numbers you can trust and compare between machines.

## Run the suites on a host

A **suite** (`backend/benchmarks/suites/`) is a list of specs run one after
the other. The same suites run on every machine, so their results compare:

| Suite | Runs | Answers |
|---|---|---|
| `baseline` | `baseline/idle-sweep`, `clients-servers-sweep`, `mesh-sweep` (3 repetitions each) | memory per node, deploy/destroy time, how many idle nodes fit; when 1 Mb/s per host stops getting through (TCP to two servers, UDP mesh) |
| `realistic` | `realistic/realistic-idle-sweep` | how many nodes of a chosen mixed campus fit (a climb to over 90% memory) |
| `random` | `random/image-census`, then 10 × `random/random-idle` | which images run here and what each costs; how many nodes of a random mix of every type fit, and how much that varies with the mix |
| `traffic` | `traffic/burst-matrix` | how 100 hosts cope with bursty traffic: 5 rates × 5 burst intervals × TCP/UDP × clients → servers / mesh |
| `full` | all of the above | two days or more on a 16 GB Docker Desktop VM |

From the repository root:

```bash
./bench.sh list                          # the suites and their runs
./bench.sh full --host m4-dd16           # name the machine (and its Docker setup)
./bench.sh random --host m4-dd16 --dry-run
./bench.sh random --host m4-dd16 --resume   # continue after a crash or reboot
```

`bench.sh` needs Docker and Python 3.11+ (stdlib only; on Windows run
`python backend\scripts\bench_suite.py run full --host …`). It:

1. checks the git tree is clean (`--allow-dirty` records it instead), brings
   the backend up without auto-reload at this commit with the host label
   (`docker compose -f docker-compose.yml -f docker-compose.bench.yml up -d`),
   checks the engine is Kathará and nothing is deployed, and builds every image
   the suite needs once, up front (images that can't build here, like
   `malicious-client` on arm64, are recorded);
2. keeps the machine awake while it runs (`caffeinate`, `systemd-inhibit`, or
   the Windows equivalent; a closed laptop lid still sleeps);
3. **restarts Docker before every benchmark** and records the host at rest:
   Kathará's VDE plugin leaves tap devices and memory behind after every
   destroy (5 GB after one sweep on macOS), which would count against the next
   benchmark. Docker Desktop: `docker desktop restart` (4.37+; older macOS
   versions quit and reopen the app). Linux has no safe default: pass
   `--restart-cmd "sudo -n systemctl restart docker"` (a sudoers rule), or
   `--restart none`. On Linux a Docker restart doesn't remove the leaked taps;
   compare the resting memory the summary shows;
4. runs each spec through the API, follows it, and saves everything in
   `backend/benchmark-results/<host>/<date>-<suite>/` (kept out of git):

   | File | What it is |
   |---|---|
   | `manifest.json` | the suite and its fingerprint, the commit, the prebuild, and per run: status, benchmark id, seed, resting memory, outcome |
   | `run.log` | the console output |
   | `NN-<run>/` | `spec.json` (exactly what was submitted), `report.md`, `export.zip`, `benchmark.json` |
   | `summary.md` | one line per run, and the random climbs folded together |

A failed benchmark gets one retry after a Docker restart (`--retries`). Ctrl-C
once: the running benchmark finishes its step, is saved, and the suite stops;
twice: cancel now. `--resume` keeps finished runs, follows a benchmark still
running, and reruns failed ones with `--retry-failed`. A suite item can run
several times (`runs`, `seeds`), take the images a census found usable
(`pool_from`), start a climb near the previous run's ceiling
(`start_from_previous`), and override spec fields (`overrides`). A suite of
your own can live anywhere (`./bench.sh path/to/suite.json …`); its specs are
paths under `backend/benchmarks/specs/`, or absolute.

**A new host, before the first run:** give Docker Desktop the CPUs and memory
you want to measure and note them (the report records what Docker sees; the
macOS baseline is 8 CPUs / 16 GB); plug in and leave the lid open; close other
heavy apps; check `./bench.sh <suite> --host … --dry-run`.

## Run one benchmark

Start the backend without auto-reload (a reload stops a running benchmark),
then run a spec from `backend/` with any Python 3.11+:

```bash
export AE3GIS_HOST_LABEL=my-laptop AE3GIS_GIT_COMMIT=$(git rev-parse HEAD)
docker compose -f docker-compose.yml -f docker-compose.bench.yml up -d --build
cd backend && python scripts/bench.py benchmarks/specs/baseline/idle-sweep.json --label my-laptop-idle
```

It prints a line per step and saves `<date>-<label>.md` (the report) and
`<date>-<label>.zip` (everything recorded) in `--out-dir`. Ctrl-C once
finishes the current step and stops; twice cancels now; either way the
benchmark removes what it deployed. `--scale 10,25,50` overrides the spec's
steps. The benchmark runs in the backend, not in the script: `python
scripts/bench.py --attach <id>` follows it again.

The benchmark refuses to start while other labs run or other jobs load the
host (`allow_busy_host: true` overrides, and is recorded with the results).
`rest_s` measures the host at rest before the first step (the report's *At
rest* line).

## What a step does

Each step deploys the generated topology of N hosts and marks its phases on
one continuous monitor timeline:

```
quiet ─► pre ─────────► deploy ─► ready ─► settle ─────► hold ─────────► destroy
wait for  nothing of ours         every host pings        idle        traffic (or idle)
the last  deployed (reference)    its gateway and a
teardown                          host in another subnet
```

Docker keeps tearing the previous step's lab down after its destroy job ends,
so a step first waits until host CPU stays under `quiet_cpu_pct` (up to
`quiet_timeout_s`; recorded as `quiet_wait_s`).

The generated topology is a small campus: a servers subnet (`10.0.0.0/24`)
behind a core router; client subnets (`10.1.k.0/24`, up to 230 hosts each)
behind their own routers, each linked to the core; per subnet a distribution
switch and access switches of up to `hosts_per_switch` hosts. `POST
/topologies/generate` makes the same topology in the library, to look at a
small one in the editor.

### Adaptive sweeps: climb to the limit

Instead of a `scale` list, `adaptive` picks each step's size from the last
one, to find the edge without guessing it:

```jsonc
"adaptive": {
  "start": 400,            // first step (hosts)
  "target_mem_pct": 93,    // aim: memory this full
  "reach_mem_pct": 90,     // done once a step's memory peaks here
  "approach": 0.6,         // close this share of the projected gap per step
  "max_factor": 2.0,       // never more than double
  "min_step": 25,          // steps in multiples of this, at least this
  "confirm": 2,            // then rerun the highest passing scale this often
  "descend": 0.7           // a failed first step: retry at this share of it
},
"stop": { "max_mem_pct": 95, "project_memory": false, … }
```

After each step it projects, from that step's resting memory and marginal
memory per node, the hosts at which memory would reach the target, and takes
`approach` of the way there: large steps far from the edge, smaller ones near
it. The climb ends at a step whose memory peaked at `reach_mem_pct` (it passes
and is the ceiling), at a failing step, or at the generator's largest topology;
the report says which (*climb: …*). Keep `max_mem_pct` above `reach_mem_pct`
as the safety stop, and `project_memory` off (the climb never jumps past its
own projection).

A step that fails because the host ran out (memory, memory pressure, an OOM,
a node gone, a slow, partial or failed deploy, hosts not ready) is retried
lower instead of ending the climb: at `descend` (default 0.7) of a first step
that was too big, or halfway down to the best passing scale. The climb then
stays below the lowest failed scale and ends as *bracketed* when no step is
left between. `descend: 0` ends the climb at the first failure.

### Mixed topologies

By default every host is one type on its type's default image. A spec can
instead mix types and images, as `realistic-idle-sweep.json` does:

```jsonc
"generate": {
  "seed": 1,                                   // placement; same seed, same topology
  "host_mix": [                                // the scale's hosts, split by weight
    { "type": "workstation", "image": "ae3gis.local/benign-client", "weight": 60 },
    { "type": "workstation", "weight": 20 }    // no image: the type's default
  ],
  "server_mix": [                              // the servers subnet (replaces "servers")
    { "type": "dns-server", "count": 1 },      // a fixed number
    { "type": "web-server", "image": "ae3gis.local/nginx", "per_hosts": 50 }  // 1 per 50 hosts, at least 1
  ],
  "switch_mix": [{ "type": "switch", "weight": 3 }, { "type": "switch", "image": "ae3gis.local/open-vswitch", "weight": 1 }],
  "core_type": "firewall", "core_image": "ae3gis.local/iptables"    // the core router
}
```

Weights split the hosts (and switches) exactly (largest remainder), so every
scale has the same composition and the memory projection between steps holds;
only *where* each kind lands is shuffled. Small scales round small shares away
(5% of 10 hosts is none). The report adds a per-image table (cgroup memory,
CPU, share of node memory) for the largest scale that passed. Build the mix's
images beforehand (Images sheet, or `POST /api/v1/images/builds`); otherwise
the benchmark's `images` step builds them before the first step, which only
delays the start.

### Random mixes

`random` draws every node instead of splitting by weight (`random/random-idle.json`):

```jsonc
"generate": {
  "seed": 1,
  "random": {
    "hosts":    [{ "type": "workstation", "images": ["kathara/base", "ae3gis.local/firefox"] }, …],  // client hosts
    "switches": [{ "type": "switch", "images": ["kathara/base", "ae3gis.local/open-vswitch"] }],
    "routers":  [{ "type": "router", "images": ["kathara/frr"] }, { "type": "firewall", "images": ["kathara/frr", "ae3gis.local/iptables"] }]
  }
}
```

Each node draws an entry with equal odds (every type as likely as any other,
however many images it has), then one of its images with equal odds,
independently of the other nodes. Networking types can be client hosts too;
`routers` covers the core and every subnet's router, which must forward
(default-drop firewalls belong in `hosts` only). The seed decides the mix: run
several seeds and compare the spread, since some mixes come out heavier than
others. Draws are prefix-stable, so a climb's larger steps keep the smaller
ones' hosts. Rows record their `composition` (nodes per type · image). The
`random` suite runs 10 seeds, each climb starting at 70% of the previous
ceiling, and its summary gives each run's ceiling and their mean ± std,
min–max, plus the share of each type at the ceiling. Some images (the
benign client, the Wazuh agent) run their own activity, so "idle" means no
traffic AE3GIS generates.

### Image census

`census: {per_image: 5}` runs one step per catalog type · image (hidden ones
aside; `cases` picks a list): 5 nodes of it as the client hosts of a small
campus (a base router and switches, one base server), deployed, checked and
measured alone. `workstation · kathara/base` runs first as the reference. An
image that can't run here (platform) or doesn't build is recorded and its
case skipped; no outcome stops the census. Its table gives each case's
outcome, whether it is *usable* (it passed, or only the host ran out), deploy
and ready time, the nodes' own cgroup memory and CPU, and the host memory a
node of it costs (the step's change less its base nodes, at the reference's
cost per node; rough at 5 nodes). The suite runner drops what isn't usable
from the random pools on that host, and records what it dropped.

### Traffic matrix

`matrix` deploys one topology (`scale: [100]`) and runs every combination of
its `axes` on it, one cell after another:

```jsonc
"matrix": {
  "patterns": [{ "id": "cs", "kind": "clients_to_servers", "servers": ["srv-1", "srv-2"] },
               { "id": "mesh", "kind": "mesh", "fanout": 2, "nodes": { "roles": ["host"], "exclude": ["srv-1", "srv-2"] } }],
  "axes": { "pattern": ["cs", "mesh"], "protocol": ["tcp", "udp"],
            "bitrate": ["50K", "100K", "250K", "500K", "1M"], "burst_interval_ms": [100, 250, 500, 1000, 2000] },
  "grid": ["bitrate", "burst_interval_ms"],   // the report's rows and columns
  "interval_s": 10, "ramp_s": 5, "gap_s": 10, "shuffle": true, "seed": 1
}
```

Axes are `pattern` and any of a pattern's `bitrate`, `burst_interval_ms`,
`protocol`, `length`, `parallel`, `direction`. Every cell is checked before
anything deploys. Each cell waits for a quiet host, idles `gap_s` (its CPU
reference), then runs its traffic for `ramp_s` + `hold_s`. Cells run in a
seeded shuffled order so slow drift doesn't line up with an axis; a degraded
or failed cell doesn't stop the matrix, a stop criterion does. The report
draws, per pattern × protocol, a rate × interval grid of: delivered, slowest
flow, RTT p95 and retransmits (TCP), jitter p95 and loss (UDP), host CPU over
idle and Docker cores; then the cells in run order. Each cell's `run.json`
(every flow's summary) is in the export under `traffic/`.

**Paced bursts.** `burst_interval_ms` on a pattern (or flow) makes each flow
send `bitrate × interval` bytes at once, every interval, keeping the mean
rate: at 1 Mb/s and 2000 ms, 250 KB every 2 s. iperf3 3.16+ ignores
`--pacing-timer` for this; AE3GIS uses `-b <rate>/<N> -l <len>`, N writes of
`len` bytes per interval (UDP: datagrams of at most 1400 B, so no IP
fragments; TCP: writes up to 64 KiB). `-l` is always set, because iperf3's
default 128 KB TCP write would turn a small cell into one write every few
seconds. Shapes iperf3 can't send (more than 1000 writes per burst) are
refused. Keep the iperf3 report interval a multiple of every burst interval
(the matrix uses 10 s). The first burst goes out at once, so a run carries one
burst more than its duration asks for: *delivered* can read a few percent over
100% for long intervals and short runs (1 Mb/s every 2 s over 13 s: 108%; over
a 65 s cell: ~103%). Checked on a real lab: the bursts leave a node intact
(2.001 s apart, 250,063 bytes in 179 datagrams within 1.1 ms).

## What the numbers mean

| Column | Definition |
|---|---|
| **Nodes / Links** | Containers and Kathará collision domains (each a Docker network with a userspace VDE switch) |
| **Deploy s** | The deploy job, from request to all containers running (its phases are in `results.csv`: `deploy_deploy_s` is Kathará's part) |
| **Ready s** | After deploy, until every host reached its gateway and a far host |
| **Destroy s** | The destroy job |
| **Marginal MB/node** | (host memory used in `settle` − in `pre`) ÷ nodes: **what a node really costs**, including its containerd shim, its links' VDE switches and kernel memory for its network namespace |
| **Docker MB/node** | The change in dockerd + containerd + shims + VDE switches' memory, per node |
| **Node cgroup MB** | The container's own memory (what `docker stats` shows). An idle node shows ~1 MB here and costs 10–15 MB in fact |
| **Host CPU %** | The host (VM) busy over the `hold` window, 0–100 of all cores |
| **Docker cores** | dockerd + containerd + shims + VDE switches over `hold`, in cores |
| **Host mem % max** | Peak host memory used over `hold` |
| **Mem stall % max** | PSI "memory full": the share of time every task waited for memory. Anything above 0 means the host is short of memory |
| **Delivered** | Received ÷ asked over all flows (traffic sweeps) |
| **Ceiling** | The largest scale whose every repetition passed. *Nodes per host* is this number, for the load the spec applied |

Traffic steps add a network table, from iperf3's own measurements over the
whole run: flows, asked Mb/s, delivered, data received, the slowest flow, RTT
(TCP) and jitter (UDP) as the median and p95 of the flows' own medians and the
highest reading, retransmits, and loss (all flows / the worst flow). With
repetitions, a per-scale table gives mean ± std.

## When a sweep stops

The first criterion met ends a sweep (after removing the step's lab); a climb
retries lower when the reason is the host running out (see *Adaptive sweeps*);
a census and a matrix go on past failed cases and cells:

| Reason | When |
|---|---|
| `projected_memory` | By the last step's memory per node, this step would cross `max_mem_pct`. It is **not deployed**: a deploy cannot be interrupted, and running the host out of memory can take Docker down with it |
| `memory` / `memory_pressure` | Host memory over `max_mem_pct`, or memory stalls over `max_psi_mem_full`, for 3 sweeps in a row |
| `oom` / `node_exited` | A node lost a process to the OOM killer, or stopped running |
| `monitor_lag` | The collector needed longer than its interval for 3 sweeps (raise `monitor.interval_s`) |
| `deploy_failed` / `deploy_partial` / `deploy_slow` | The deploy failed, left nodes not running, or took longer than `deploy_timeout_s` |
| `not_ready` | Some host could not reach its gateway or a far host within `ready_timeout_s` |
| `traffic_short` / `traffic_loss` / `traffic_none` | Delivered below `min_delivered_ratio`, UDP loss above `max_loss_pct`, or nothing arrived (with `stop_on_degraded: false` these are noted and the sweep goes on) |

## Getting numbers you can trust

- **One benchmark per machine at a time, nothing else running.** Close what
  you can; the report records other labs and jobs if you allowed them.
- **Docker Desktop:** the host is its Linux VM. Give it the memory and CPUs you
  want to measure (Settings → Resources) and note them; they appear in the
  report (`8 CPUs · 8215 MB`). macOS itself is not measured: it runs the VM plus
  whatever else you have open.
- **Linux:** the host is the machine. For the steadiest numbers fix the CPU
  governor (`performance`) and keep the machine otherwise idle.
- **Repeat.** `repetitions: 3` runs each scale three times; the results carry
  mean, std, min and max per scale (`by_scale` in `benchmark.json`).
- **Compare like with like.** Every report carries an environment
  fingerprint (Docker version, kernel, CPUs, memory, cgroup version, Kathará
  and its network plugin, AE3GIS commit; not the node images). Same
  fingerprint, same stack. Suite manifests record the suite's own fingerprint
  (its file and specs) and, for random climbs, the pool each run used.
- **Start from a clean engine.** The suite runner restarts Docker before each
  benchmark for this; the *At rest* line and the summary's resting memory show
  what was left over.
- **Memory is returned slowly.** After a destroy the host does not get all its
  memory back at once, so each step measures against its own `pre` window;
  raise `cooldown_s` if `mem_pre` keeps climbing between steps.
- **Large labs are slow to list.** AE3GIS waits up to `AE3GIS_DOCKER_TIMEOUT_S`
  (300 s) for a Docker API call; around a thousand containers, listing them can
  take over a minute on Docker Desktop's containerd image store.
- **The tools cost something too.** The collector (~1% of a core, ~8 MB) and
  the traffic driver (its iperf3 processes: ~15% of a core for 12 flows at
  5 Mb/s here) are containers of their own; the monitor reports them as
  `tool`, never as node load.

## What needs privileges, and why

Both helpers are ordinary (not privileged) containers started through the
Docker socket AE3GIS already uses:

- the **collector** shares the host's PID and cgroup namespaces and mounts the
  host cgroup tree read-only: it reads files, it changes nothing;
- the **traffic driver** shares the host's PID namespace with `CAP_SYS_ADMIN`
  (to enter a node's network namespace with `setns`) and `CAP_SYS_PTRACE` (to
  open that namespace: Kathará nodes hold capabilities the driver does not).

On hosts whose AppArmor or SELinux policy blocks `setns` for containers, the
first traffic run or readiness check fails with *Cannot enter node network
namespaces*; set `AE3GIS_DRIVER_SECURITY_OPT='["apparmor=unconfined"]'` (or
`'["label=disable"]'` for SELinux) on the backend.

## Limits of the generator (for now)

- At most 64 client subnets of 230 hosts (router links come from one `/24`),
  so 14 720 hosts; the host will stop you well before.
- Every host has its own link to its switch (Kathará's model of a cable). A
  mode where a subnet is one shared collision domain would cost less per node;
  it is a planned benchmark variable.
- Nodes have no CPU or memory limits: an idle node uses almost nothing, so
  *nodes per host* depends on the load you apply. Per-node limits are planned.
- The servers subnet holds at most 230 servers, which caps how far a
  `server_mix` with `per_hosts` entries can scale (the spec is refused beyond).
