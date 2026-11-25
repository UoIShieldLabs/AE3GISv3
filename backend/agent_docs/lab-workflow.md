# Running a lab

## Lifecycle
`idle → deploying → deployed → destroying → idle`; any failure → `error` (destroy
from `error` cleans up). One deploy/destroy job per topology at a time.

1. **Validate** (`validate_topology`): fix every error first.
2. **Deploy** (`deploy`): a job with steps validate → images → plan → deploy →
   verify. Missing images are built first (minutes). A student may run a limited
   number of labs at once (`lab_limit`).
3. **Verify by doing**: `run_in_node` on the devices, e.g. `ip -br addr`,
   `ip route`, `ping -c 2 -W 1 <ip>`, `nc -zv <ip> <port>`, `curl -s <url>`.
   Use device ids from `get_topology`; the IPs are in the outline.
4. **Observe**: `start_capture` (a link or `node:ethN`, BPF filter) then
   `get_packets`; `start_traffic` (iperf3 flows or patterns) then `get_job`;
   `start_monitor` then `monitor_snapshot`. Stop open-ended runs with `stop_run`.
5. **Destroy** (`destroy`) when done; `save: true` keeps each node's filesystem for
   the next deploy.

## Commands in nodes
- `run_in_node` runs `sh -lc '<command>'` in the node and waits (default 60 s).
  Don't start a server or an endless loop with it: it would hang until the timeout.
  Use `start_background` for anything that must keep running; stop it with `stop_run`.
- Nodes have no internet access and no DNS for other nodes: use IPs.
- Not every image has bash; `sh` always works.
- Boot configuration is logged in `/var/log/ae3gis-init.log` inside each node.

## Jobs
Every long operation is a job with an id: `get_job` (steps, result, log tail),
`wait_for_job` (blocks up to 10 min), `list_activity` (what's running now).

## Images
`list_images` shows each image's status (ready, missing, stale, building, failed).
`build_images` builds `ae3gis.local/…` images from their Dockerfile sources; a
deploy also builds missing ones itself.
