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
from collections.abc import Callable
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


def next_scale(
    row: dict[str, Any],
    adaptive: dict[str, Any],
    *,
    mem_total: float | None,
    nodes_for: Callable[[int], int],
    max_scale: int,
) -> tuple[int | None, str, str]:
    """An adaptive sweep's next scale after a passing step: (scale or None when
    the climb is over, code, why).

    Done once the step's memory peaked at ``reach_mem_pct``. Otherwise project,
    from the step's resting memory and marginal memory per node, the hosts at
    which memory would reach ``target_mem_pct``, and close ``approach`` of the
    gap: large steps while far, smaller ones near the edge (at least
    ``min_step`` hosts, in multiples of ``min_step``, and never past
    ×``max_factor``: from a small scale the step may be less than ``min_step``).
    """
    last = int(row["scale"])
    reach = float(adaptive.get("reach_mem_pct") or 90)
    target = float(adaptive.get("target_mem_pct") or 93)
    approach = float(adaptive.get("approach") or 0.6)
    factor = float(adaptive.get("max_factor") or 2.0)
    unit = max(1, int(adaptive.get("min_step") or 25))
    peak = row.get("hold_mem_pct_max")
    if peak is not None and peak >= reach:
        return None, "limit_reached", f"memory peaked at {peak:.1f}% at {last} hosts"
    if last >= max_scale:
        return None, "max_scale", f"{last} hosts is the largest topology the generator makes"
    per_node, base = row.get("marginal_mem_per_node"), row.get("mem_pre")
    if not per_node or per_node <= 0 or base is None or not mem_total:
        nxt, why = round(last * min(factor, 1.5)), "no memory per node measured: ×1.5"
    else:
        budget = (mem_total * target / 100 - base) / per_node  # nodes that fit
        lo, hi = 0, max_scale  # the most hosts whose nodes fit the budget
        while lo < hi:
            mid = (lo + hi + 1) // 2
            lo, hi = (mid, hi) if nodes_for(mid) <= budget else (lo, mid - 1)
        projected = lo
        if projected <= last:
            nxt = last + unit
            why = f"~{target:g}% projected at {projected} hosts; +{unit}"
        else:
            nxt = last + min(approach * (projected - last), (factor - 1) * last)
            why = (
                f"~{target:g}% memory projected at {projected} hosts "
                f"({per_node / 1e6:.1f} MB/node, peak {peak if peak is not None else 0:.1f}% now)"
            )
    nxt = max(last + unit, round(nxt / unit) * unit)
    nxt = min(nxt, max(last + 1, math.floor(last * factor)), max_scale)
    return nxt, "next", f"next {nxt} hosts: {why}"


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


def image_sweep(
    t: float, nodes: list[dict[str, Any]], image_of: dict[str, str]
) -> list[dict[str, Any]]:
    """One sweep's node rows folded per image: count, mean memory, mean CPU."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for n in nodes:
        image = image_of.get(n["target"]) if n.get("kind") == "node" else None
        if image is not None:
            groups.setdefault(image, []).append(n)
    return [
        {
            "t": t,
            "image": image,
            "count": len(ns),
            "mem_mean": mean([n["mem_used"] for n in ns if n.get("mem_used") is not None]),
            "cpu_mean": mean([n["cpu_pct"] for n in ns if n.get("cpu_pct") is not None]),
        }
        for image, ns in groups.items()
    ]


def image_metrics(
    rows: list[dict[str, Any]], windows: dict[str, tuple[float, float] | None]
) -> dict[str, dict[str, Any]]:
    """A step's per-image numbers: nodes, cgroup memory over settle, CPU over hold."""
    settle, hold = windows.get("settle"), windows.get("hold")
    out: dict[str, dict[str, Any]] = {}
    for image in dict.fromkeys(r["image"] for r in rows):
        rs = [r for r in rows if r["image"] == image]
        out[image] = {
            "count": max(window(rs, settle, "count"), default=None),
            "mem_mean": _r(mean(window(rs, settle, "mem_mean")), 0),
            "cpu_mean": _r(mean(window(rs, hold, "cpu_mean")), 3),
        }
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
        f"- **Steps:** {_steps_line(spec)} · pre {spec.get('cooldown_s')}s, "
        f"settle {spec.get('settle_s')}s, hold {spec.get('hold_s')}s · monitor every "
        f"{(spec.get('monitor') or {}).get('interval_s')}s",
        f"- **Load:** {_traffic_line(spec)}",
        f"- **Outcome:** ceiling {result.get('ceiling') or '–'} hosts"
        + (f" · climb: {result['limit']}" if result.get("limit") else "")
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
    lines += _image_table(rows)
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


def _steps_line(spec: dict[str, Any]) -> str:
    a = spec.get("adaptive")
    if not a:
        return f"scale {spec.get('scale')} × {spec.get('repetitions', 1)}"
    return (
        f"adaptive from {a.get('start')} hosts toward {a.get('target_mem_pct', 93):g}% memory, "
        f"done at ≥ {a.get('reach_mem_pct', 90):g}% (closing {a.get('approach', 0.6):g} of the "
        f"projected gap per step, ≥ {a.get('min_step', 25)} hosts, ≤ ×{a.get('max_factor', 2):g}), "
        f"ceiling rerun ×{a.get('confirm', 2)}"
    )


def _image_table(rows: list[dict[str, Any]]) -> list[str]:
    """Per image at the largest scale whose steps all passed (mean over its runs)."""
    passing = [r for r in rows if r["outcome"] == "ok" and r.get("by_image")]
    if not passing:
        return []
    top = max(r["scale"] for r in passing)
    runs = [r["by_image"] for r in passing if r["scale"] == top]
    stats: dict[str, dict[str, float | None]] = {}
    for image in dict.fromkeys(i for run in runs for i in run):
        per = [run[image] for run in runs if image in run]
        stats[image] = {
            k: mean([x[k] for x in per if x.get(k) is not None])
            for k in ("count", "mem_mean", "cpu_mean")
        }
    total = sum((v["count"] or 0) * (v["mem_mean"] or 0) for v in stats.values()) or None
    lines = [
        "",
        f"Per image at {top} hosts (largest passing scale, mean of {len(runs)} run(s)): "
        "the container's cgroup memory over settle, its CPU over hold (100 = one core).",
        "",
        "| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |",
        "|---|---:|---:|---:|---:|",
    ]
    for image, v in sorted(
        stats.items(), key=lambda kv: -((kv[1]["count"] or 0) * (kv[1]["mem_mean"] or 0))
    ):
        share = (v["count"] or 0) * (v["mem_mean"] or 0) / total if total else None
        lines.append(
            f"| `{image}` | {_num(v['count'], 0)} | {_mb(v['mem_mean'])} "
            f"| {'–' if share is None else f'{share * 100:.1f}%'} | {_num(v['cpu_mean'], 2)} |"
        )
    return lines


def _kind(entry: dict[str, Any]) -> str:
    image = entry.get("image")
    return f"{entry['type']} · {image.split('/')[-1]}" if image else entry["type"]


def _weights(mix: list[dict[str, Any]]) -> str:
    total = sum(float(e["weight"]) for e in mix) or 1.0
    return ", ".join(f"{_kind(e)} {float(e['weight']) / total * 100:.0f}%" for e in mix)


def _topology_line(spec: dict[str, Any]) -> str:
    topo = spec.get("topology") or {}
    if topo.get("topology_id"):
        return f"existing topology `{topo['topology_id']}`"
    g = topo.get("generate") or {}
    shape = (
        f"≤ {g.get('hosts_per_subnet', 200)} hosts per subnet, "
        f"≤ {g.get('hosts_per_switch', 48)} per switch"
    )
    custom = ("host_mix", "server_mix", "switch_mix", "core_type", "core_image")
    if not any(g.get(k) for k in custom):
        return (
            f"generated: {g.get('servers', 1)} server(s), {shape}, "
            f"hosts `{g.get('host_type', 'workstation')}`"
        )
    hosts = _weights(g["host_mix"]) if g.get("host_mix") else g.get("host_type", "workstation")
    if g.get("server_mix"):
        servers = ", ".join(
            f"{_kind(e)} ×{e['count']}"
            if e.get("count") is not None
            else f"{_kind(e)} 1/{e['per_hosts']} hosts"
            for e in g["server_mix"]
        )
    else:
        servers = f"{g.get('servers', 1)} × {g.get('server_type', 'workstation')}"
    switches = _weights(g["switch_mix"]) if g.get("switch_mix") else g.get("switch_type", "switch")
    core = _kind(
        {"type": g.get("core_type") or g.get("router_type", "router"), "image": g.get("core_image")}
    )
    return (
        f"generated, mixed (seed {g.get('seed', 0)}), {shape}. Hosts: {hosts}. "
        f"Servers: {servers}. Switches: {switches}. Core: {core}"
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
