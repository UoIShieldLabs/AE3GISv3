"""Benchmark metrics, stop criteria and the report (pure).

A benchmark's monitor records the host continuously; each step marks four
windows on that timeline (see services/benchmark):

- ``pre``: nothing of ours deployed (the reference)
- ``settle``: deployed and reachable, no traffic
- ``hold``: the step's load (traffic, or idle for idle sweeps)

Definitions (the plan's; docs/benchmarks/README.md explains them):

- marginal memory per node = (mean host memory used in ``settle`` − mean in
  ``pre``) / nodes deployed. It counts everything a node costs (its
  containerd shim, its links' VDE switches, kernel memory for its network
  namespace…), unlike a container's own cgroup figure, reported beside it.
- Docker overhead per node: the change in dockerd + containerd + shims + VDE
  switches' memory between ``pre`` and ``settle``, per node.
- nodes per host is not measured: it is the sweep's ceiling, the largest
  scale that passed at the chosen load.
"""

from __future__ import annotations

import math
from typing import Any

from domain.monitor import percentile

DOCKER_RSS = ("dockerd_rss", "containerd_rss", "containerd_shim_rss", "vde_switch_rss")
DOCKER_CPU = (
    "dockerd_cpu_pct",
    "containerd_cpu_pct",
    "containerd_shim_cpu_pct",
    "vde_switch_cpu_pct",
)
SUSTAINED = 3  # sweeps a host threshold must hold before it stops the sweep


def mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def window(rows: list[dict[str, Any]], span: tuple[float, float] | None, key: str) -> list[float]:
    if span is None:
        return []
    a, b = span
    return [r[key] for r in rows if r.get(key) is not None and a <= r["t"] <= b]


def _r(x: float | None, digits: int = 3) -> float | None:
    return None if x is None else round(x, digits)


class Watch:
    """The host-side stop criteria, checked on every monitor sweep while armed."""

    def __init__(self, stop: dict[str, Any], interval_s: float) -> None:
        self.stop = stop
        self.interval_ms = interval_s * 1000
        self.reset()

    def reset(self) -> None:
        self.counts = {"memory": 0, "memory_pressure": 0, "monitor_lag": 0}

    def _sustained(self, key: str, over: bool) -> bool:
        self.counts[key] = self.counts[key] + 1 if over else 0
        return self.counts[key] >= SUSTAINED

    def check(self, host: dict[str, Any], sweep: dict[str, Any]) -> tuple[str, str] | None:
        """(reason, detail) when a criterion is met by this sweep."""
        if sweep.get("oom"):
            return "oom", "out of memory: " + ", ".join(sorted(sweep["oom"])[:10])
        if sweep.get("missing"):
            return "node_exited", "stopped running: " + ", ".join(sweep["missing"][:10])
        pct = host.get("mem_used_pct")
        limit = self.stop.get("max_mem_pct")
        if limit is not None and self._sustained("memory", pct is not None and pct > limit):
            return "memory", f"host memory {pct:.1f}% > {limit}% for {SUSTAINED} sweeps"
        psi = host.get("psi_mem_full")
        limit = self.stop.get("max_psi_mem_full")
        if limit is not None and self._sustained(
            "memory_pressure", psi is not None and psi > limit
        ):
            return "memory_pressure", f"memory stalls {psi:.1f}% > {limit}% for {SUSTAINED} sweeps"
        ms = host.get("sweep_ms")
        if self._sustained("monitor_lag", ms is not None and ms > self.interval_ms):
            return (
                "monitor_lag",
                f"the collector needs {ms:.0f} ms per sweep, more than its interval",
            )
        return None


def projected_memory(
    rows: list[dict[str, Any]], host: dict[str, Any] | None, nodes: int, stop: dict[str, Any]
) -> tuple[str, str] | None:
    """(reason, detail) when deploying ``nodes`` would likely cross
    ``max_mem_pct``: memory used now plus ``nodes`` × the cost per node the last
    passing step measured. A deploy cannot be interrupted, so a step that would
    exhaust the host is not started (the sweep stops before, not during, it)."""
    limit = stop.get("max_mem_pct")
    if not stop.get("project_memory", True) or limit is None or not host:
        return None
    used, total = host.get("mem_used"), host.get("mem_total")
    per_node = next(
        (
            r["marginal_mem_per_node"]
            for r in reversed(rows)
            if r.get("outcome") == "ok" and (r.get("marginal_mem_per_node") or 0) > 0
        ),
        None,
    )
    if not used or not total or per_node is None:
        return None
    need = used + per_node * nodes
    if need <= total * limit / 100:
        return None
    return (
        "projected_memory",
        f"{nodes} nodes would need ~{need / 1e9:.1f} GB ({need / total * 100:.0f}% of "
        f"{total / 1e9:.1f} GB) at {per_node / 1e6:.1f} MB/node",
    )


def traffic_verdict(totals: dict[str, Any] | None, stop: dict[str, Any]) -> tuple[str, str] | None:
    """(reason, detail) when the step's traffic did not get through."""
    if not totals:
        return None
    ratio = totals.get("delivered_ratio")
    floor = stop.get("min_delivered_ratio")
    if ratio is not None and floor is not None and ratio < floor:
        return (
            "traffic_short",
            f"delivered {ratio * 100:.1f}% of what was asked (< {floor * 100:.0f}%)",
        )
    loss = totals.get("lost_percent")
    cap = stop.get("max_loss_pct")
    if loss is not None and cap is not None and loss > cap:
        return "traffic_loss", f"UDP loss {loss:.2f}% > {cap}%"
    if totals.get("flows") and totals.get("flows_without_data") == totals.get("flows"):
        return "traffic_none", "no flow delivered anything"
    return None


def deploy_phases(steps: list[dict[str, Any]]) -> dict[str, float]:
    """Seconds per step of a deploy job."""
    from datetime import datetime

    out: dict[str, float] = {}
    for s in steps or []:
        a, b = s.get("started_at"), s.get("ended_at")
        if a and b:
            out[s["name"]] = round(
                (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds(), 3
            )
    return out


def step_metrics(
    host: list[dict[str, Any]],
    agg: list[dict[str, Any]],
    windows: dict[str, tuple[float, float] | None],
    nodes: int,
) -> dict[str, Any]:
    """A step's numbers from the monitor's host rows and per-sweep node aggregates."""
    pre, settle, hold = windows.get("pre"), windows.get("settle"), windows.get("hold")
    mem_pre = mean(window(host, pre, "mem_used"))
    mem_settle = mean(window(host, settle, "mem_used"))

    def docker(span):
        rows = [r for r in host if span and span[0] <= r["t"] <= span[1]]
        vals = [
            sum(r.get(k) or 0 for k in DOCKER_RSS)
            for r in rows
            if any(r.get(k) for k in DOCKER_RSS)
        ]
        return mean(vals)

    d_pre, d_settle = docker(pre), docker(settle)
    hold_rows = [r for r in host if hold and hold[0] <= r["t"] <= hold[1]]
    docker_cpu = [
        sum(r.get(k) or 0 for k in DOCKER_CPU)
        for r in hold_rows
        if any(r.get(k) is not None for k in DOCKER_CPU)
    ]
    out: dict[str, Any] = {
        "mem_pre": _r(mem_pre, 0),
        "mem_settle": _r(mem_settle, 0),
        "marginal_mem_per_node": _r((mem_settle - mem_pre) / nodes, 0)
        if mem_pre is not None and mem_settle is not None and nodes
        else None,
        "docker_mem_per_node": _r((d_settle - d_pre) / nodes, 0)
        if d_pre is not None and d_settle is not None and nodes
        else None,
        "node_mem_mean": _r(mean(window(agg, settle, "mem_mean")), 0),
        "node_mem_p95": _r(mean(window(agg, settle, "mem_p95")), 0),
        "nodes_seen": max(window(agg, settle, "count"), default=None),
    }
    cpu = window(host, hold, "vm_cpu_pct")
    mem = window(host, hold, "mem_used")
    pct = window(host, hold, "mem_used_pct")
    out.update(
        {
            "hold_cpu_mean": _r(mean(cpu), 2),
            "hold_cpu_p95": _r(percentile(cpu, 95), 2),
            "hold_cores_mean": _r(mean(window(host, hold, "cores_used")), 3),
            "hold_mem_max": max(mem, default=None),
            "hold_mem_pct_max": _r(max(pct, default=None), 2),
            "hold_load1_mean": _r(mean(window(host, hold, "load1")), 2),
            "hold_psi_cpu_mean": _r(mean(window(host, hold, "psi_cpu_some")), 2),
            "hold_psi_mem_max": _r(max(window(host, hold, "psi_mem_some"), default=None), 2),
            "hold_psi_mem_full_max": _r(max(window(host, hold, "psi_mem_full"), default=None), 2),
            "hold_node_cpu_mean": _r(mean(window(agg, hold, "cpu_mean")), 3),
            "hold_node_cpu_p95": _r(mean(window(agg, hold, "cpu_p95")), 3),
            "hold_node_rx_bps": _r(mean(window(agg, hold, "rx_sum")), 0),
            "hold_tool_cpu_mean": _r(mean(window(host, hold, "tool_cpu_pct")), 2),
            # Docker's own processes (dockerd, containerd, shims, VDE), 100 = one core.
            "hold_docker_cpu_mean": _r(mean(docker_cpu), 1),
            "hold_tool_mem_mean": _r(mean(window(host, hold, "tool_mem_used")), 0),
        }
    )
    step = (pre or hold or settle, hold or settle or pre)
    span = (step[0][0], step[1][1]) if step[0] and step[1] else None
    out["sweep_ms_p95"] = _r(percentile(window(host, span, "sweep_ms"), 95), 1)
    return out


# ── across steps ──────────────────────────────────────────────────────

SCALE_METRICS = (
    "deploy_s",
    "ready_s",
    "destroy_s",
    "marginal_mem_per_node",
    "docker_mem_per_node",
    "node_mem_mean",
    "hold_cpu_mean",
    "hold_mem_pct_max",
    "hold_psi_mem_full_max",
    "delivered_ratio",
)


def _spread(xs: list[float]) -> dict[str, float | None]:
    if not xs:
        return {"mean": None, "std": None, "min": None, "max": None}
    m = sum(xs) / len(xs)
    std = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else 0.0
    return {"mean": _r(m), "std": _r(std), "min": _r(min(xs)), "max": _r(max(xs))}


def by_scale(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Repetitions of a scale folded into mean / std / min / max."""
    scales: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        scales.setdefault(r["scale"], []).append(r)
    out = []
    for scale in sorted(scales):
        rs = scales[scale]
        entry: dict[str, Any] = {
            "scale": scale,
            "runs": len(rs),
            "ok": sum(1 for r in rs if r["outcome"] == "ok"),
            "nodes": rs[0].get("nodes"),
        }
        for key in SCALE_METRICS:
            entry[key] = _spread([r[key] for r in rs if r.get(key) is not None])
        out.append(entry)
    return out


def ceiling(rows: list[dict[str, Any]]) -> int | None:
    """The largest scale whose every repetition passed (below the first failure)."""
    best = None
    for entry in by_scale(rows):
        if entry["ok"] != entry["runs"]:
            break
        best = entry["scale"]
    return best


# ── report ────────────────────────────────────────────────────────────


def _mb(x: float | None) -> str:
    return "–" if x is None else f"{x / 1e6:.1f}"


def _num(x: float | None, digits: int = 1) -> str:
    return "–" if x is None else f"{x:.{digits}f}"


def markdown_report(result: dict[str, Any], spec: dict[str, Any], env: dict[str, Any]) -> str:
    """The benchmark as a Markdown page (docs/benchmarks/)."""
    docker = (env.get("engine") or {}).get("docker") or {}
    kathara = (env.get("engine") or {}).get("kathara") or {}
    ae3gis = env.get("ae3gis") or {}
    host = env.get("host") or {}
    rows = result.get("rows") or []
    lines = [
        f"# Benchmark: {spec.get('label') or 'unnamed'}",
        "",
        f"- **Host:** {host.get('label') or 'unnamed (set AE3GIS_HOST_LABEL)'} · {docker.get('os', '?')} · "
        f"{docker.get('arch', '?')} · {docker.get('ncpu', '?')} CPUs · {_mb(docker.get('mem_total'))} MB",
        f"- **Kernel / Docker:** {docker.get('kernel', '?')} · Docker {docker.get('server_version', '?')} · "
        f"cgroup v{docker.get('cgroup_version', '?')}",
        f"- **Kathará:** {kathara.get('version', '?')} · network plugin "
        f"`{(kathara.get('network_plugin') or {}).get('name', '?')}`",
        f"- **AE3GIS:** `{(ae3gis.get('git_commit') or 'unknown')[:12]}`"
        f"{' (modified)' if ae3gis.get('git_dirty') else ''} · {ae3gis.get('mode') or '?'}",
        f"- **Environment fingerprint:** `{env.get('fingerprint', '?')}`",
        f"- **Topology:** {_topology_line(spec)}",
        f"- **Steps:** scale {spec.get('scale')} × {spec.get('repetitions', 1)} · pre {spec.get('cooldown_s')}s, "
        f"settle {spec.get('settle_s')}s, hold {spec.get('hold_s')}s · monitor every "
        f"{(spec.get('monitor') or {}).get('interval_s')}s",
        f"- **Load:** {_traffic_line(spec)}",
        f"- **Outcome:** ceiling {result.get('ceiling') or '–'} hosts"
        + (
            f" · stopped: {result.get('reason')} ({result.get('detail')})"
            if result.get("reason")
            else ""
        )
        + f" · {(result.get('started_at') or '')[:19]} → "
        f"{(result.get('ended_at') or 'still running')[:19]}",
        "",
        "| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node "
        "| Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max "
        "| Delivered | Outcome |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        delivered = r.get("delivered_ratio")
        outcome = r["outcome"] + (f": {r['detail']}" if r.get("detail") else "")
        lines.append(
            f"| {r['scale']} | {r['rep']} | {r.get('nodes', '–')} | {r.get('links', '–')} "
            f"| {_num(r.get('deploy_s'))} | {_num(r.get('ready_s'), 2)} | {_num(r.get('destroy_s'))} "
            f"| {_mb(r.get('marginal_mem_per_node'))} | {_mb(r.get('docker_mem_per_node'))} "
            f"| {_mb(r.get('node_mem_mean'))} / {_mb(r.get('node_mem_p95'))} "
            f"| {_num(r.get('hold_cpu_mean'))} "
            f"| {_num((r.get('hold_docker_cpu_mean') or 0) / 100 if r.get('hold_docker_cpu_mean') is not None else None, 2)} "
            f"| {_num(r.get('hold_mem_pct_max'))} "
            f"| {_num(r.get('hold_psi_mem_full_max'), 2)} "
            f"| {'–' if delivered is None else f'{delivered * 100:.1f}%'} "
            f"| {outcome} |"
        )
    lines += [
        "",
        "Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what "
        "a node costs outside its container (containerd shim, VDE switches, kernel). "
        "Node cgroup memory is the container's own figure. Ready = every host reached its "
        "gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + "
        "VDE switches) and memory are over the hold window.",
        "",
    ]
    return "\n".join(lines)


def _topology_line(spec: dict[str, Any]) -> str:
    topo = spec.get("topology") or {}
    if topo.get("topology_id"):
        return f"existing topology `{topo['topology_id']}`"
    g = topo.get("generate") or {}
    return (
        f"generated: {g.get('servers', 1)} server(s), ≤ {g.get('hosts_per_subnet', 200)} hosts per "
        f"subnet, ≤ {g.get('hosts_per_switch', 48)} per switch, hosts `{g.get('host_type', 'workstation')}`"
    )


def _traffic_line(spec: dict[str, Any]) -> str:
    t = spec.get("traffic")
    if not t:
        return "idle (no traffic)"
    parts = []
    for p in t.get("patterns") or []:
        what = "mesh" if p.get("kind") == "mesh" else "clients → servers"
        extra = f", {p.get('fanout', 1)} peer(s) each" if p.get("kind") == "mesh" else ""
        parts.append(
            f"{what}{extra}, {p.get('protocol', 'tcp').upper()} {p.get('bitrate')} per flow"
        )
    return "; ".join(parts) + f" (ramp {t.get('ramp_s', 0)}s)"
