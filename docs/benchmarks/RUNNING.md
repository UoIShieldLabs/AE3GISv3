# Running the benchmarks on a machine

How to run the two benchmark suites the project compares across machines, on
a fresh clone, so the results line up with the ones already recorded. The
method behind them is in [README.md](README.md); this page is the checklist.

| Suite | What it measures | Took on an M4 MacBook Air (Docker Desktop 8 CPUs / 16 GB) |
|---|---|---|
| `random` | **Idle capacity.** An image census (which node images run here, and what each costs), then 10 climbs of a random mix of every node type, each to the most nodes this machine holds, Docker restarted before each | ~8.5 h |
| `traffic` | **Capacity under traffic.** For 100 traffic cells (5 rates × 5 burst intervals × TCP/UDP × clients → servers / mesh), the most hosts each comfortably supports and where it starts to fail, 50 hosts apart | ~25–30 h |

Both are started by one command each and keep going on their own; the
results land in `backend/benchmark-results/<host>/` (kept out of git).

## 1. Prepare the machine

- **Docker.** macOS and Windows: Docker Desktop; give it the CPUs and memory
  you want measured (Settings → Resources), and keep those settings for every
  run on this machine. Linux: Docker Engine (the suites restart it, see
  below). Close other Docker work: nothing else should run while a suite runs.
- **Disk.** At least 30 GB free on Docker's disk (`./bench.sh check` shows
  it; `docker system df` shows what uses it). Build caches and old builders
  fill it quietly.
- **Python 3.11+** and **git** on the host (the runner is stdlib-only).
- **Power and sleep.** Plugged in for the whole run. Laptops: lid open (a
  closed lid sleeps whatever the runner does). The runner keeps the machine
  awake otherwise.
- **Port 8000** free: the suites run their own backend there.

## 2. Get the code and check

```bash
git clone git@github.com:UoIShieldLabs/AE3GISv3.git && cd AE3GISv3
git checkout feat/registry-images       # or main, once merged
./bench.sh check                       # Linux: ./bench.sh check --restart-cmd "sudo -n systemctl restart docker"
```

`check` reports everything that would stop or skew a run (git, Docker, disk,
power, how Docker gets restarted, port 8000, leftover labs, other containers)
as OK / INFO / WARN / FAIL with what to do. Fix every FAIL before starting.

Optional sanity run (about 5 minutes: a 10-host step, three times): it
proves the stack deploys and measures on this machine before you commit a day
to it.

```bash
docker compose -f docker-compose.yml -f docker-compose.bench.yml up -d --build backend
python3 backend/scripts/bench.py backend/benchmarks/specs/baseline/idle-sweep.json --scale 10 --out-dir /tmp/ae3gis-sanity
```

## 3. Run

Pick a host label that names the machine and its Docker setup, e.g.
`m4-macbook-air`, `xeon32-linux-engine`, `i7-win-dd16` (it names the results
folder and is written into every report). Then run the suites detached, one
after the other:

```bash
H=<host label>
mkdir -p backend/benchmark-results/$H
nohup sh -c "./bench.sh random --host $H; ./bench.sh traffic --host $H" \
  > backend/benchmark-results/$H/run.log 2>&1 &
```

Linux adds `--restart-cmd "sudo -n systemctl restart docker"` to both (a
sudoers rule such as `<user> ALL=(root) NOPASSWD: /usr/bin/systemctl restart docker`
lets it run unattended). Each suite brings the backend up in bench mode at
this commit, builds the images it needs, restarts Docker before every
benchmark, and writes a manifest after every step.

- **Progress:** `tail -f backend/benchmark-results/$H/run.log`, or the
  *Benchmarks* sheet in the UI once a suite runs.
- **Stop:** `pkill -f bench_suite.py` stops the runner (the benchmark running
  in the backend finishes on its own); **resume** with the same command plus
  `--resume`: finished runs are kept, a running benchmark is followed.
- **Kernel setting:** the `traffic` suite raises the neighbour (ARP) table in
  Docker's kernel (from 1024 entries for all nodes together to 16384) with a
  privileged one-shot container, after every Docker restart. On Linux that
  changes the host's own kernel until it reboots.

## 4. Results

`backend/benchmark-results/<host>/<date>-random/` and `<date>-traffic/`:
`summary.md` (the 10 climbs' mean ± std, and the traffic grids of
*comfortable / fails* per scenario), `manifest.json`, `run.log`, and a folder
per benchmark with its report and full export. Zip the host folder to share
it; results never go into git.

## What has bitten earlier runs

- **A full Docker disk** fails builds and container starts (the Wazuh manager
  alone unpacks 2–3 GB per node; it is left out of the random mix, and steps
  stop at 90% disk).
- **Battery and sleep**: a run on battery or with the lid closed is not
  comparable, or not finished.
- **Heat** on fanless laptops: traffic cells rest (a quiet host, then an idle
  minute) before running, so back-to-back heavy cells don't slow the chip.
- **The ARP table** (1024 entries by default) cut off hosts past ~250 (mesh)
  and ~500 (clients → servers) under traffic; the traffic suite raises it.
- **Images a platform can't build** are recorded and left out on that machine
  (malicious-client is amd64-only; zeek doesn't build on arm64 today), so the
  random mix differs slightly per machine; the manifest records the pool.
- **Big machines**: the traffic search stops at 1000 hosts (`max_hosts` in
  `backend/benchmarks/suites/traffic.json`); if many cells report `≥ 1000`,
  raise it.
- **Windows** is untested: run in WSL2 against Docker Desktop, and check that
  `docker desktop restart` works there (else `--restart none`).

## For Claude, when asked to run these benchmarks

1. Read this page and run `./bench.sh check` (with `--restart-cmd` on Linux).
   Report every WARN and FAIL to the user and fix FAILs **only with their OK**:
   never delete images, volumes, caches or containers, stop containers you
   didn't start, change system settings, or commit/stash their changes
   without asking. If the tree is dirty, ask (don't pass `--allow-dirty` on
   your own).
2. Agree on the host label with the user, confirm the machine is plugged in
   (lid open on a laptop) and that Docker can be restarted repeatedly.
3. Optionally do the sanity run; then start both suites detached as in §3,
   and watch the first benchmark until its first step passes.
4. Report progress when asked: the run log's `round N:` / step lines, the
   manifest (`backend/benchmark-results/<host>/<date>-<suite>/manifest.json`),
   and `summary.md` when a suite finishes. If something fails, read the
   failing benchmark's `benchmark.json` (rows, reasons) before changing
   anything, and ask before deviating from this procedure.
5. Never edit the code or switch branches while a suite runs: the backend
   runs from this checkout and reloads it after every Docker restart.
