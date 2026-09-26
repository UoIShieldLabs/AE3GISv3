"""Run a fixed traffic suite against a deployed topology and write a report.

The "before" half of a before/after: run it on today's stack, change
something (plugin, limits, pinning, host), run it again, and compare the
reports. Each run's environment (host, kernel, Docker, Kathara + network
plugin, AE3GIS commit, image ids) and its fingerprint are recorded, so two
reports with different fingerprints say what changed.

    python scripts/run_baseline.py --topology <id> --client host-a --server host-b \\
        [--base-url http://localhost:8000] [--token T] [--duration 30] \\
        [--out ../docs/baselines/<date>-<host>.md]

Stdlib only (urllib), so it runs from any Python 3.11+ without the venv.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SUITE: list[tuple[str, dict[str, Any]]] = [
    ("TCP, 1 stream", {"protocol": "tcp", "parallel": 1}),
    ("TCP, 4 streams", {"protocol": "tcp", "parallel": 4}),
    ("UDP, 100 Mb/s, 1200 B", {"protocol": "udp", "bitrate": "100M", "length": 1200}),
    ("TCP, reverse", {"protocol": "tcp", "direction": "reverse"}),
    ("TCP, both ways", {"protocol": "tcp", "direction": "bidir"}),
]


class Api:
    def __init__(self, base: str, token: str | None) -> None:
        self.base = base.rstrip("/") + "/api/v1"
        self.token = token

    def call(self, method: str, path: str, body: Any = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                raw = res.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise SystemExit(f"{method} {path}: {exc.code} {detail}") from None
        return json.loads(raw) if raw else None

    def wait(self, job_id: str, timeout: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = self.call("GET", f"/jobs/{job_id}")
            if job["status"] not in ("queued", "running"):
                return job
            time.sleep(1)
        raise SystemExit(f"job {job_id} did not finish in {timeout:.0f}s")


def run_one(api: Api, topo: str, name: str, flow: dict[str, Any], args, capture_on: str | None):
    capture = None
    if capture_on:
        capture = api.call(
            "POST",
            f"/topologies/{topo}/captures",
            {
                "target": {"kind": "interface", "node_id": args.client, "interface": capture_on},
                "snaplen": 128,
                "label": f"baseline: {name}",
            },
        )
        # Wait for tcpdump to be attached (the first capture may build its image).
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            steps = {
                x["name"]: x["status"]
                for x in api.call("GET", f"/captures/{capture['id']}")["job"]["steps"]
            }
            if steps.get("capture") == "running":
                break
            if "failed" in steps.values():
                raise SystemExit("the capture failed to start")
            time.sleep(1)
    run = api.call(
        "POST",
        f"/topologies/{topo}/traffic/runs",
        {
            "label": f"baseline: {name}",
            "flows": [{"id": "f1", "client": args.client, "server": args.server, **flow}],
            "duration_s": args.duration,
            "monitor_nodes": "all",
        },
    )
    job = api.wait(run["id"], args.duration + 120)
    if capture:
        api.call("POST", f"/jobs/{capture['id']}/stop")
        capture = api.call("GET", f"/captures/{api.wait(capture['id'], 60)['id']}")
    return job, capture


def fmt(v: Any, digits: int = 1) -> str:
    return "–" if v is None else f"{v:.{digits}f}"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--token")
    ap.add_argument("--topology", required=True)
    ap.add_argument("--client", required=True, help="node id that sends")
    ap.add_argument("--server", required=True, help="node id that receives")
    ap.add_argument("--duration", type=int, default=30)
    ap.add_argument(
        "--capture-interface", default="eth0", help="client interface for the capture test"
    )
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    api = Api(args.base_url, args.token)

    suite = [(name, flow, None) for name, flow in SUITE]
    suite.append(("TCP, 1 stream, while capturing", {"protocol": "tcp"}, args.capture_interface))
    rows = []
    env = None
    for name, flow, capture_on in suite:
        print(f"· {name} …", file=sys.stderr, flush=True)
        job, capture = run_one(api, args.topology, name, flow, args, capture_on)
        if job["status"] != "succeeded":
            rows.append((name, job, None, capture))
            continue
        if env is None:
            env = api.call("GET", f"/jobs/{job['id']}/artifacts/run.json")["environment"]
        rows.append((name, job, job["result"]["flows"][0], capture))

    lines = [f"# Traffic baseline — {datetime.now(UTC):%Y-%m-%d %H:%M} UTC", ""]
    if env:
        d, k, a = env["engine"]["docker"], env["engine"]["kathara"], env["ae3gis"]
        lines += [
            f"- **Host:** {env['host'].get('label') or 'unnamed'} · {d.get('os')} · {d.get('arch')} · "
            f"{d.get('ncpu')} CPUs · {d.get('mem_total', 0) / 1e9:.1f} GB",
            f"- **Kernel / Docker:** {d.get('kernel')} · Docker {d.get('server_version')} · cgroup v{d.get('cgroup_version')}",
            f"- **Kathará:** {k.get('version')} · network plugin `{k['network_plugin'].get('name')}`",
            f"- **AE3GIS:** `{(a.get('git_commit') or 'unknown')[:12]}`{' (modified)' if a.get('git_dirty') else ''} · {a.get('mode') or ''}",
            f"- **Tools:** {', '.join((env.get('tool') or {}).get('versions', {}).values()) or '–'}",
            f"- **Environment fingerprint:** `{env.get('fingerprint')}`",
            f"- **Flow:** `{args.client}` → `{args.server}`, {args.duration}s per test, 1 s samples",
            "",
        ]
    lines += [
        "| Test | Direction | Mean Mb/s | p50 | Min | Max | Retrans. | RTT ms | Jitter ms | Loss % | Run |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for name, job, flow, capture in rows:
        if flow is None:
            lines.append(
                f"| {name} | – | failed: {job.get('error')} | | | | | | | | `{job['id'][:8]}` |"
            )
            continue
        for direction, s in flow["summary"].items():
            bps = s.get("bps") or {}
            lines.append(
                f"| {name} | {'client → server' if direction == 'fwd' else 'server → client'} "
                f"| {fmt(bps.get('mean', 0) / 1e6)} | {fmt(bps.get('p50', 0) / 1e6)} "
                f"| {fmt(bps.get('min', 0) / 1e6)} | {fmt(bps.get('max', 0) / 1e6)} "
                f"| {s.get('retransmits', '–')} | {fmt((s.get('rtt_ms') or {}).get('mean'), 2)} "
                f"| {fmt((s.get('jitter_ms') or {}).get('mean'), 3)} | {fmt(s.get('lost_percent'), 3)} "
                f"| `{job['id'][:8]}` |"
            )
        if capture:
            st = capture["stats"]
            lines.append(
                f"| ↳ capture on {args.client} {args.capture_interface} (headers only) | | "
                f"{st.get('packets', 0):,} packets | | | | | | | "
                f"{st.get('dropped_by_kernel') or 0} dropped | `{capture['id'][:8]}` |"
            )
    report = "\n".join(lines) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report)
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
