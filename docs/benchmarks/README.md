# Benchmarking AE3GIS, Kathará and Docker

How much does a node cost, how many fit on a machine, how long do they take to
deploy, and what happens under load? AE3GIS answers with three tools that work
alone or together:

| Tool | What it does | Where |
|---|---|---|
| **Monitor** | Records CPU, memory and network of chosen nodes, the host (on Docker Desktop: its Linux VM) and Docker's own processes, every N seconds | Dock tab (⌘K → *Start monitor*, or right-click a node) · `POST /topologies/{id}/monitors` |
| **Traffic** | Generates iperf3 load: picked flows, clients → servers, or a mesh; hundreds of flows from one driver container | Dock tab (⌘K → *New traffic run*) · `POST /topologies/{id}/traffic/runs` |
| **Benchmark** | Sweeps generated topologies of growing size (deploy → check the network → settle → load → destroy), measuring each step, until the host stops coping | Headless: `backend/scripts/bench.py` · results on the Library page (*Benchmarks*) |

This page is about benchmarks: how to run one, what the numbers mean, and how
to get numbers you can trust and compare between machines.

## Run a benchmark

1. **Start AE3GIS without auto-reload** (a reload stops a running benchmark),
   and name the machine:

   ```bash
   export AE3GIS_HOST_LABEL=my-laptop
   export AE3GIS_GIT_COMMIT=$(git rev-parse HEAD)
   docker compose -f docker-compose.yml -f docker-compose.bench.yml up -d --build
   ```

2. **Pick a spec** from `backend/benchmarks/specs/` (or write one):

   | Spec | Load | Answers |
   |---|---|---|
   | `idle-sweep.json` | none | memory per node, deploy/destroy time, how many idle nodes fit |
   | `client-server-sweep.json` | each host → one of two servers, 1 Mb/s TCP | the same under many-to-few traffic, and whether it still gets through |
   | `mesh-sweep.json` | each host → the next two hosts, 1 Mb/s UDP | east-west load across subnets |

3. **Run it** (from `backend/`, any Python 3.11+, no venv needed):

   ```bash
   python scripts/bench.py benchmarks/specs/idle-sweep.json --label my-laptop-idle --out-dir ../docs/benchmarks
   ```

   It prints a line per step and, at the end, saves `<date>-<label>.md` (the
   report) and `<date>-<label>.zip` (everything recorded). Ctrl-C once finishes
   the current step and stops; twice cancels now. Either way the benchmark
   removes what it deployed. `--scale 10,25,50` overrides the spec's steps.

The benchmark refuses to start while other labs run or other jobs load the
host (`allow_busy_host: true` overrides, and is recorded with the results).

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

## When a sweep stops

The first criterion met ends the sweep (after removing the step's lab):

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
- **Close the Docker Desktop window.** With a few hundred containers something
  kept dockerd and containerd busy (~3.5 cores) while the lab sat idle; the
  dashboard's per-container stats are the likely cause. The *Docker cores* column shows what Docker itself used.
- **Docker Desktop:** the host is its Linux VM. Give it the memory and CPUs you
  want to measure (Settings → Resources) and note them; they appear in the
  report (`8 CPUs · 8215 MB`). macOS itself is not measured: it runs the VM plus
  whatever else you have open.
- **Linux:** the host is the machine. For the steadiest numbers fix the CPU
  governor (`performance`) and keep the machine otherwise idle.
- **Repeat.** `repetitions: 3` runs each scale three times; the results carry
  mean, std, min and max per scale (`by_scale` in `benchmark.json`).
- **Compare like with like.** Every report carries an environment
  fingerprint (Docker, kernel, Kathará and its network plugin, AE3GIS commit,
  images). Same fingerprint, same stack.
- **Memory is returned slowly.** After a destroy the host does not get all its
  memory back at once, so each step measures against its own `pre` window;
  raise `cooldown_s` if `mem_pre` keeps climbing between steps.
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
