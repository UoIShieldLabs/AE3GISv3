# AE3GIS vs GNS3: running the comparison on a machine

This is the checklist for running the platform comparison on a machine, with
the same procedure the M4 MacBook Air ran.

The comparison is a separate study from the suites in [RUNNING.md](RUNNING.md):
AE3GIS against GNS3, both used the official way, on the same machine, with the
same labs, images and probes. Everything for it lives on the
**`benchmarking/platform-comparison`** branch, which is never merged into
`main`.

| | AE3GIS | GNS3 |
|---|---|---|
| **Platform** | AE3GIS v3 (the October benchmark code) with Kathara | GNS3 2.2.54, Docker nodes, no appliances |
| **VM** | Docker Desktop's VM (macOS: Apple's Virtualization framework; Windows: WSL 2) | the GNS3 VM (macOS: VMware Fusion; Windows: VirtualBox) |
| **Driven by** | AE3GIS's REST API: import → deploy job → destroy job | GNS3's REST API: project → nodes (in parallel) → links → start → stop → delete |

**Labs:** the campus at 25, 50, 100, 200 and 400 hosts, plus 800 when it
fits. Each is one JSON file (`backend/benchmarks/compare/labs/`), with every
node's image pinned by digest:

| Role | Image |
|---|---|
| hosts | `tollan/benign-client:v0.10` |
| servers (1 per 50 hosts) | `tollan/nginx-server:v0.3` |
| routers | `tollan/iptables:v0.6` |
| switches | `kathara/base` |

**Experiments** (`backend/benchmarks/compare/plan.json`):
- **E0:** the platform at rest, 5 min after a VM restart.
- **E1:** each lab size in 3 rounds. The VM restarts before every step. Each
  step: quiet VM → 30 s reference → deploy (45 min cap) → network ready (5 min
  cap) → settle 30 s → hold 60 s → teardown → 30 s after.
- **E2:** on one 100-host lab: ping latency, one flat-out TCP flow, then a
  load ladder of 4 patterns × 100K → 5M per flow, which stops at the first
  failure and repeats the edge.
- **E3:** one more 400-host step per platform, whose hold waits until the
  VM's CPU has stayed under 10% for 30 s (at most 20 min), then lasts 2 min:
  the lab at rest once the deploy's aftermath is over. On Docker Desktop, its
  UI re-listing every container after each container event keeps `dockerd`
  and `containerd` busy for minutes after a big deploy, so E1's hold (30 s
  after ready) still includes it from about 200 hosts up.

**Time:** about 6 h on the M4 MacBook Air (both platforms; E3 about 30 min of
it). Machines that are slower to deploy take longer; the 45 min cap bounds
each step.

## 1. Prepare the machine

**Both platforms get the same CPUs and memory, and only one VM runs at a
time** (the runner stops one before starting the other).

- **Docker Desktop:**
  - **CPUs and memory:**
    - macOS: Settings → Resources.
    - Windows (WSL 2): `%USERPROFILE%\.wslconfig`, then `wsl --shutdown`:
      ```ini
      [wsl2]
      processors=8
      memory=16GB
      ```
  - **Off:** Resource Saver (Settings → Resources), Kubernetes, extensions.
  - **Disk:** at least 30 GB free on Docker's disk.
  - **Nothing else running in Docker:** no dev backend on port 8000 (the
    runner brings up its own, compose project `ae3gis-compare`) and no other
    labs.
  - **Windows:** no other WSL distros running (`wsl -l --running`). WSL's VM
    is shared, and a restart runs `wsl --shutdown`.
- **The GNS3 VM** (2.2.54; VMware Fusion on macOS, VirtualBox on Windows):
  - **Resources:** the same CPUs and memory as Docker Desktop.
  - **SSH:** key-based, as `gns3`. The password is `gns3`; run
    `ssh-copy-id gns3@<VM address>` yourself, since the runner never types
    passwords. Windows has no `ssh-copy-id`; in PowerShell:
    `type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh gns3@<VM address> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"`
    (run `ssh-keygen -t ed25519` first if there's no key).
  - **API:** port 80 in the VM (`curl http://<VM address>/v2/version`).
  - **No GNS3 GUI** open during the run.
  - **VirtualBox:** the runner finds the VM's address through the Guest
    Additions (`VBoxManage guestproperty get "GNS3 VM"
    /VirtualBox/GuestInfo/Net/0/V4/IP`). If that's empty, set `address` (and
    `nic` or `api_port` if needed) in the config below, and keep that address
    fixed.
- **The host:**
  - **Python 3.11+** and `git`. Windows also needs `pip install psutil`, and
    runs the commands below in Git Bash (`python` where they say `python3`,
    if `python3` isn't found).
  - **On AC power** for the whole run, the lid open, and other apps closed.
    The runner keeps the machine awake. Big apps (browsers, Teams, Zoom,
    OneDrive) compete with the VMs for memory and CPU.
  - **Windows:** run the terminal as Administrator if `memcheck` (below)
    can't read the VM's process.

## 2. Get the code and configure

```bash
git fetch origin
git worktree add ../AE3GISv3-compare origin/benchmarking/platform-comparison -b benchmarking/platform-comparison
cd ../AE3GISv3-compare
cp backend/benchmarks/compare/host.example.json backend/benchmarks/compare/compare.local.json
```

Edit `compare.local.json` (it's git-ignored):

| Key | What |
|---|---|
| `host` | this machine's results folder, e.g. `m4max-studio-dd12-95g` (the same name as its other benchmarks) |
| `first` | `ae3gis` or `gns3`: which platform goes first in round 1 (rounds alternate). Use `gns3` on the second machine and `ae3gis` on the third, so the order is balanced across machines |
| `gns3.vmx` | macOS: the GNS3 VM's `.vmx` path |
| `gns3.vbox` | Windows: the VM's VirtualBox name (e.g. `"GNS3 VM"`), in place of `vmx` |
| `gns3.address` | optional: a fixed VM address, when VirtualBox can't report it |
| `gns3.security_opt` | `["apparmor=unconfined"]`: the GNS3 VM's AppArmor blocks the traffic probe otherwise (probes only; GNS3's nodes are privileged anyway) |
| `gns3.concurrency` | 16: GNS3's parallel API calls (the fastest stable setting on the Air) |

## 3. Check and prepare the VMs

Run each from `backend/`:

```bash
python3 scripts/compare.py check        # power, Docker settings, the same CPUs and memory, disk, one VM
python3 scripts/compare.py images       # both VMs: the lab images at their pinned digests, the probe image
python3 scripts/compare.py memcheck --platform ae3gis
python3 scripts/compare.py memcheck --platform gns3
```

- **`check`** must end with `ready`.
- **`images`** starts each VM in turn. Pulling the images takes a few minutes
  on each.
- **`memcheck`** touches 2 GiB inside the VM and prints the host-side samples.
  **Footprint** should rise by roughly 1–2 GiB and stay there after "freed",
  since both hypervisors keep freed guest memory. If it doesn't move on
  Windows, or the samples say `unreadable`, stop and look before running:
  that's the metric the comparison reports.

**On a new machine, or after any change to the code, do a dry run** (about
20 min; the results go to a `*-compare-quick` folder and aren't used):

```bash
python3 scripts/compare.py smoke --platform ae3gis --out /tmp/smoke-a   # E2's traffic on 25 hosts
python3 scripts/compare.py smoke --platform gns3 --out /tmp/smoke-g
python3 scripts/compare.py run --quick --sizes 25,50 --reps 1
python3 scripts/compare.py summarize --quick
```

Every step should be `ok`, readiness should be 100% on both platforms, and
`summarize` should show both platforms in every table.

## 4. Run

```bash
python3 -u scripts/compare.py run > benchmark-results/<host>/$(date +%F)-compare.log 2>&1 &
tail -f benchmark-results/<host>/*-compare.log
```

- **Resume:** if the run is interrupted (power, a crash, a reboot), run
  `python3 -u scripts/compare.py run --resume >> <log>`. Every finished step
  is a file, and existing files are skipped. Before resuming, make sure no
  half-deployed lab is left:
  - AE3GIS: `docker ps -a --filter label=app=kathara` should list nothing,
    and the backend's library should have no `compare-campus-*` topology
    still deployed;
  - GNS3: no `ae3gis-compare-campus-*` project in `curl
    http://<VM address>/v2/projects`.

  Remove leftovers through each platform's own API or UI.
- **What a step looks like in the log:**
  `ae3gis e1-h100-r2: ok in 214s`. Statuses:
  - `not_ready`: deployed, but some readiness pings failed;
  - `failed`: the deploy errored;
  - `capped`: the deploy went past 45 min;
  - `skipped`: a smaller size of that round wasn't `ok`, or 800 hosts won't
    fit in memory (projected from 400).

  All of these are results, not errors to fix. An `error` status (the
  runner itself broke) is the one to look into.
- **Don't use the machine heavily during the run.** Light use (reading,
  typing) is fine.

## 5. Results

They go to `backend/benchmark-results/<host>/<date>-compare/`:
- `manifest.json`: the host config, the plan, the commit, and the lab files'
  sha256;
- `ae3gis/` and `gns3/`, with one file per step: `e0-r1.json`,
  `e1-h100-r2.json`, `e2.json`, `e3-h400-r1.json`, … Each holds the per-phase
  metrics inside the VM and on the host, plus a compact time series. There
  are no raw exports.
- A resume (`--resume`, or `--only` for some experiments) appends its commit
  and plan to `manifest.json` under `resumes`.

```bash
python3 scripts/compare.py summarize      # summary.md + summary.json in the run's folder
```

To commit (results are git-ignored, so force-add):

```bash
git add -f backend/benchmark-results/<host>/<date>-compare/{manifest.json,summary.md,summary.json,ae3gis,gns3}
git add -f backend/benchmark-results/<host>/<date>-compare.log
git commit -m "[benchmark] results : AE3GIS vs GNS3 on <host>"
git push origin benchmarking/platform-comparison
```

Then rebuild the notebook (`analysis/platforms.ipynb`), from the repo root:

```bash
uv run --no-project --with-requirements analysis/requirements.txt python analysis/build.py
```

Its first cell checks that both platforms are present, the lab files and
images match, and every planned step exists.

## How the metrics are taken

- **Host memory:** the VM process's footprint plus its helpers': Activity
  Monitor's "Memory" on macOS, the working set on Windows. Both hypervisors
  keep memory they gave the guest, so the footprint is a high-water mark since
  the VM started. That's why the VM restarts before every step and each step
  is measured against its own 30 s reference.
- **Memory inside the VM:** `MemTotal − MemAvailable`, from the monitor
  (`ae3gis-collect`) running in a container in the VM.
- **Containers' memory:** cgroup memory minus inactive file, as
  `docker stats` reports it. Docker Desktop uses cgroup v2 and the GNS3 VM
  cgroup v1, which count differently, so per-container figures are
  indicative only.
- **CPU:** the VM's busy share (`/proc/stat`), and the VM process's and
  helpers' CPU time on the host. The gap between the two is the hypervisor's
  own cost.
- **The platforms' own processes in the VM:**
  - AE3GIS: `dockerd`, `containerd`, its shims, and Kathara's `vde_switch`;
  - GNS3: the same, plus `ubridge` and `gns3server`.

  The monitor reports them by name.
- **Readiness:** the same ping checks on both platforms, from the traffic
  driver (`ae3gis-netns`) in each node's network namespace: every host to its
  gateway and to a server across the core.

## What to know about the two setups

- **GNS3** gives every Docker node an aux console (two `busybox sh` per
  node). 2.2.54 has no way to turn it off, so it counts as GNS3's cost. Its
  nodes are privileged. Its own `init.sh` can leave a single-interface node's
  `eth0` down when many nodes start at once, so the runner's start command
  brings every interface up before the node's boot commands.
- **GNS3's node creation** sometimes stalls for ~30 s inside its compute (it
  happens even with one call at a time). That's measured as is.
- **Kathara's links on Docker Desktop** are userspace VDE switches (Docker
  Desktop's kernel has no Open vSwitch module). The GNS3 VM's are `ubridge`
  processes. That shows in E2.
- **On Windows, VirtualBox runs on top of Hyper-V** whenever WSL 2 is on,
  which Docker Desktop needs. That's slower than VirtualBox on its own, and
  it's part of what's measured there.
- **Docker Desktop's VM** on macOS is Apple's Virtualization framework, and
  its helpers (backend, services) are counted with it. VMware Fusion's
  helpers are counted with the GNS3 VM.
