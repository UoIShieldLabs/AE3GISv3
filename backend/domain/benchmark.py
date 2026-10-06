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
import random
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


def window_mean(
    rows: list[dict[str, Any]], span: tuple[float, float] | None, key: str
) -> float | None:
    return _r(mean(window(rows, span, key)), 2)


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
        self.counts = {"memory": 0, "memory_pressure": 0, "disk": 0, "monitor_lag": 0}

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
        disk = host.get("disk_used_pct")
        limit = self.stop.get("max_disk_pct")
        if limit is not None and self._sustained("disk", disk is not None and disk > limit):
            return "disk", f"Docker's disk {disk:.1f}% > {limit}% for {SUSTAINED} sweeps"
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


# Step failures that say the host ran out (not that something is broken): a
# climb retries below them instead of ending.
HOST_LIMITS = frozenset(
    {
        "memory",
        "memory_pressure",
        "disk",
        "oom",
        "node_exited",
        "projected_memory",
        "monitor_lag",
        "deploy_slow",
        "deploy_partial",
        "deploy_failed",
        "not_ready",
    }
)


def retry_scale(best: int | None, failed: int, descend: float, unit: int) -> int | None:
    """After a climb step failed on a host limit at ``failed`` hosts: the scale
    to try instead. With no passing step yet, ``descend`` of it (a start too
    big for this host); otherwise halfway between the best passing scale and
    it. In multiples of ``unit``; None when no such scale is left (or
    ``descend`` is 0: no retries)."""
    unit = max(1, unit)
    if not descend:
        return None
    if best is None:
        nxt = math.floor(failed * descend / unit) * unit
        return nxt if unit <= nxt < failed else None
    nxt = round((best + failed) / 2 / unit) * unit
    return nxt if best < nxt < failed else None


def next_scale(
    row: dict[str, Any],
    adaptive: dict[str, Any],
    *,
    mem_total: float | None,
    nodes_for: Callable[[int], int],
    max_scale: int,
    cap: int | None = None,
) -> tuple[int | None, str, str]:
    """An adaptive sweep's next scale after a passing step: (scale or None when
    the climb is over, code, why).

    Done once the step's memory peaked at ``reach_mem_pct``. Otherwise project,
    from the step's resting memory and marginal memory per node, the hosts at
    which memory would reach ``target_mem_pct``, and close ``approach`` of the
    gap: large steps while far, smaller ones near the edge (at least
    ``min_step`` hosts, in multiples of ``min_step``, and never past
    ×``max_factor``: from a small scale the step may be less than ``min_step``).
    ``cap``: a scale that already failed; the climb stays below it and is
    over (bracketed) once no step is left between.
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
    if cap is not None and nxt >= cap:
        nxt = (cap - 1) // unit * unit
        if nxt <= last:
            return None, "bracketed", f"ceiling between {last} and {cap} hosts ({cap} failed)"
        why += f"; below {cap}, which failed"
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
    disk_pre = mean(window(host, pre, "disk_used"))
    disk_settle = mean(window(host, settle, "disk_used"))

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
        "disk_pre": _r(disk_pre, 0),
        "disk_settle": _r(disk_settle, 0),
        # What the step's nodes wrote to Docker's disk (their writable layers).
        "disk_per_node": _r((disk_settle - disk_pre) / nodes, 0)
        if disk_pre is not None and disk_settle is not None and nodes
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
            "hold_disk_pct_max": _r(max(window(host, hold, "disk_used_pct"), default=None), 2),
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


def kind_of(spec: dict[str, Any]) -> str:
    """What a benchmark does: ``sweep`` (fixed scales), ``adaptive`` (a climb),
    ``census`` (one step per catalog image) or ``matrix`` (traffic cells on one
    deployment). Specs from before ``kind`` existed are sweeps or climbs."""
    return spec.get("kind") or ("adaptive" if spec.get("adaptive") else "sweep")


def composition(kinds) -> dict[str, int]:
    """How many nodes of each ``type · image`` a step placed (most first)."""
    counts: dict[str, int] = {}
    for t, image in kinds:
        key = f"{t} · {image}"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


# ── census ──

CENSUS_REFERENCE = {"type": "workstation", "image": "kathara/base"}
# Census failures that say the host ran out, not that the image is broken: its
# nodes may still go into random mixes, a few at a time.
CENSUS_HOST_LIMITS = frozenset(
    {"memory", "memory_pressure", "disk", "projected_memory", "monitor_lag"}
)


def case_label(case: dict[str, Any]) -> str:
    return f"{case['type']} · {case['image']}"


def census_cases(
    types: dict[str, dict[str, Any]], hidden: set[str], given: list[dict[str, Any]] | None
) -> list[dict[str, str]]:
    """The census's cases in order, the reference first: ``given`` (checked
    against the catalog ``types``), or every type's images but ``hidden``
    ones. ValueError for a case the catalog can't deploy."""
    if given:
        cases = [{"type": c["type"], "image": c["image"]} for c in given]
        for c in cases:
            spec = types.get(c["type"])
            if spec is None:
                raise ValueError(f"Unknown node type {c['type']!r}")
            if c["image"] not in (spec.get("images") or []):
                raise ValueError(f"{c['type']!r} has no image {c['image']}")
    else:
        cases = [
            {"type": t, "image": image}
            for t, spec in types.items()
            for image in spec.get("images") or []
            if image not in hidden
        ]
    out = [dict(CENSUS_REFERENCE)]
    for c in cases:
        if c not in out:
            out.append(c)
    return out


def census_table(rows: list[dict[str, Any]], per_image: int) -> list[dict[str, Any]]:
    """One entry per case, its repetitions averaged: the outcome, whether its
    image is ``usable`` (it passed, or only the host ran out), deploy and ready
    seconds, the case nodes' own cgroup memory and CPU, and the host memory a
    node of it costs: the step's memory change less its base nodes (router,
    switches, server), costed at the reference step's memory per node."""
    by_case: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r.get("case"):
            by_case.setdefault(r["case"], []).append(r)

    def delta(r: dict[str, Any]) -> float | None:
        if r.get("mem_settle") is None or r.get("mem_pre") is None:
            return None
        return r["mem_settle"] - r["mem_pre"]

    ref = [
        delta(r) / r["nodes"]
        for r in by_case.get(case_label(CENSUS_REFERENCE), [])
        if r["outcome"] == "ok" and delta(r) is not None and r.get("nodes")
    ]
    ref_node = mean(ref)
    out = []
    for case, rs in by_case.items():
        ok = [r for r in rs if r["outcome"] == "ok"]
        bad = next((r for r in rs if r["outcome"] != "ok"), None)
        costs = [
            (delta(r) - (r["nodes"] - per_image) * ref_node) / per_image
            for r in ok
            if ref_node is not None and delta(r) is not None
        ]
        own = [r["by_image"][case] for r in ok if case in (r.get("by_image") or {})]
        disk = [
            (r["disk_settle"] - r["disk_pre"]) / per_image
            for r in ok
            if r.get("disk_settle") is not None and r.get("disk_pre") is not None
        ]
        out.append(
            {
                "case": case,
                "type": rs[0].get("case_type"),
                "image": rs[0].get("case_image"),
                "runs": len(rs),
                "ok": len(ok),
                "outcome": bad["outcome"] if bad else "ok",
                "reason": bad["reason"] if bad else None,
                "detail": bad["detail"] if bad else None,
                "usable": bool(ok) or (bad is not None and bad["reason"] in CENSUS_HOST_LIMITS),
                "deploy_s": _r(
                    mean([r["deploy_s"] for r in ok if r.get("deploy_s") is not None]), 2
                ),
                "ready_s": _r(mean([r["ready_s"] for r in ok if r.get("ready_s") is not None]), 2),
                "host_mem_per_node": _r(mean(costs), 0),
                "cgroup_mem_per_node": _r(
                    mean([x["mem_mean"] for x in own if x.get("mem_mean") is not None]), 0
                ),
                "cpu_pct_per_node": _r(
                    mean([x["cpu_mean"] for x in own if x.get("cpu_mean") is not None]), 3
                ),
                # What a node of it writes to Docker's disk (its base nodes write ~nothing).
                "disk_per_node": _r(mean(disk), 0),
            }
        )
    return out


# ── traffic matrix ──


def _short(name: str, value: Any) -> str:
    if name == "burst_interval_ms":
        return f"{value}ms"
    if name == "length":
        return f"{value}B"
    if name == "parallel":
        return f"P{value}"
    return str(value)


def matrix_cells(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    """Every combination of the matrix's axes, as ``{id, pattern, <axis>:
    value…}`` (``pattern``: a pattern id), in axis order. Ids read like
    ``cs·tcp·250K·500ms``."""
    axes = dict(matrix.get("axes") or {})
    patterns = [str(x) for x in axes.pop("pattern", None) or [p["id"] for p in matrix["patterns"]]]
    cells: list[dict[str, Any]] = [{"pattern": pid} for pid in patterns]
    for name, values in axes.items():
        cells = [{**c, name: v} for c in cells for v in values]
    for c in cells:
        c["id"] = "·".join(_short(k, v) for k, v in c.items())
    return cells


def matrix_order(cells: list[dict[str, Any]], seed: int, rep: int, shuffle: bool) -> list[dict]:
    """The order a repetition runs its cells in: shuffled (per seed and
    repetition) so drift over the run doesn't line up with an axis."""
    order = list(cells)
    if shuffle:
        random.Random(f"{seed}:{rep}").shuffle(order)
    return order


def matrix_pattern(matrix: dict[str, Any], cell: dict[str, Any]) -> dict[str, Any]:
    """The traffic pattern a cell runs: its pattern with the cell's values."""
    base = next(p for p in matrix["patterns"] if p["id"] == cell["pattern"])
    over = {k: v for k, v in cell.items() if k not in ("id", "pattern")}
    return {**{k: v for k, v in base.items() if v is not None}, **over}


CELL_METRICS = (
    "delivered_ratio",
    "flow_ratio_min",
    "lost_percent",
    "retransmits",
    "rtt_ms_p50",
    "rtt_ms_p95",
    "jitter_ms_p50",
    "jitter_ms_p95",
    "hold_cpu_mean",
    "idle_cpu_mean",
    "cpu_delta",
    "hold_docker_cpu_mean",
    "hold_mem_pct_max",
)


def matrix_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One entry per cell, its repetitions averaged (cell rows carry ``cell``)."""
    by_cell: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r.get("cell"):
            by_cell.setdefault(r["case"], []).append(r)
    out = []
    for cid, rs in by_cell.items():
        bad = next((r for r in rs if r["outcome"] != "ok"), None)
        entry: dict[str, Any] = {
            "id": cid,
            "cell": rs[0]["cell"],
            "runs": len(rs),
            "ok": sum(1 for r in rs if r["outcome"] == "ok"),
            "outcome": bad["outcome"] if bad else "ok",
            "reason": bad["reason"] if bad else None,
            "flows": rs[0].get("flows"),
            "offered_bps": rs[0].get("offered_bps"),
        }
        for key in CELL_METRICS:
            entry[key] = _r(mean([r[key] for r in rs if r.get(key) is not None]), 4)
        out.append(entry)
    return out


def rest_metrics(host: list[dict[str, Any]], span: tuple[float, float]) -> dict[str, Any]:
    """The host at rest before the first step, nothing of ours deployed: what
    an earlier run or a leak left behind (memory the engine never gave back,
    a busy daemon) shows up here, so runs on one host can be compared."""
    rows = [r for r in host if span[0] <= r["t"] <= span[1]]
    docker = [
        sum(r.get(k) or 0 for k in DOCKER_RSS) for r in rows if any(r.get(k) for k in DOCKER_RSS)
    ]
    totals = [r["mem_total"] for r in rows if r.get("mem_total")]
    return {
        "samples": len(rows),
        "mem_used": _r(mean(window(host, span, "mem_used")), 0),
        "mem_total": totals[-1] if totals else None,
        "mem_used_pct": _r(mean(window(host, span, "mem_used_pct")), 2),
        "vm_cpu_pct": _r(mean(window(host, span, "vm_cpu_pct")), 2),
        "docker_rss": _r(mean(docker), 0),
        "disk_used_pct": _r(mean(window(host, span, "disk_used_pct")), 2),
    }


# What a step copies from its traffic run's totals (services/traffic.totals).
TRAFFIC_ROW_KEYS = (
    "flows",
    "offered_bps",
    "delivered_bps",
    "delivered_ratio",
    "bytes_received",
    "lost_percent",
    "retransmits",
    "flows_with_errors",
    "rtt_ms_p50",
    "rtt_ms_p95",
    "rtt_ms_max",
    "jitter_ms_p50",
    "jitter_ms_p95",
    "jitter_ms_max",
    "flow_loss_pct_max",
    "flow_ratio_min",
    "flow_ratio_p05",
    "slowest_flow",
    "slowest_flow_bps",
)

SCALE_METRICS = (
    "deploy_s",
    "ready_s",
    "destroy_s",
    "marginal_mem_per_node",
    "docker_mem_per_node",
    "node_mem_mean",
    "hold_cpu_mean",
    "hold_docker_cpu_mean",
    "hold_mem_pct_max",
    "hold_psi_mem_full_max",
    "disk_per_node",
    "delivered_ratio",
    "rtt_ms_p95",
    "jitter_ms_p95",
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
        *_rest_line(result.get("rest")),
        f"- **Outcome:** {_outcome(result)}"
        + (f" · climb: {result['limit']}" if result.get("limit") else "")
        + (
            f" · stopped: {result.get('reason')} ({result.get('detail')})"
            if result.get("reason")
            else ""
        )
        + f" · {(result.get('started_at') or '')[:19]} → "
        f"{(result.get('ended_at') or 'still running')[:19]}",
    ]
    if kind_of(spec) == "census":
        return "\n".join(lines + _census_md(result.get("census") or [], spec))
    matrix = result.get("matrix")
    if matrix is not None:
        rows = [r for r in rows if not r.get("cell")]  # the deployments; cells below
    lines += [
        "",
        "| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node "
        "| Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max "
        "| Disk MB/node | Disk % max | Delivered | Outcome |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
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
            f"| {_mb(r.get('disk_per_node'))} | {_num(r.get('hold_disk_pct_max'))} "
            f"| {'–' if delivered is None else f'{delivered * 100:.1f}%'} "
            f"| {outcome} |"
        )
    if matrix is not None:
        lines += _matrix_md(matrix, spec)
        lines += _cells_md([r for r in result.get("rows") or [] if r.get("cell")])
    lines += _spread_table(result.get("by_scale") or [])
    lines += _traffic_table(rows)
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


def _cells_md(rows: list[dict[str, Any]]) -> list[str]:
    """Every cell in the order it ran (drift over the run shows here)."""
    if not rows:
        return []
    lines = [
        "",
        "Cells in run order:",
        "",
        "| # | Cell | Flows | Asked Mb/s | Delivered | Slowest flow | RTT p95 ms | Jitter p95 ms "
        "| Loss % | Host CPU % (idle → load) | Docker cores | Outcome |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        docker = r.get("hold_docker_cpu_mean")
        outcome = r["outcome"] + (f": {r['detail']}" if r.get("detail") else "")
        lines.append(
            f"| {r.get('order', '–')} | `{r['case']}` | {r.get('flows', '–')} "
            f"| {_bps(r.get('offered_bps'))} | {_pct(r.get('delivered_ratio'))} "
            f"| {_pct(r.get('flow_ratio_min'))} | {_num(r.get('rtt_ms_p95'))} "
            f"| {_num(r.get('jitter_ms_p95'), 2)} | {_num(r.get('lost_percent'), 2)} "
            f"| {_num(r.get('idle_cpu_mean'))} → {_num(r.get('hold_cpu_mean'))} "
            f"| {_num(None if docker is None else docker / 100, 2)} | {outcome} |"
        )
    return lines


def _outcome(result: dict[str, Any]) -> str:
    matrix = result.get("matrix")
    if matrix is not None:
        counts: dict[str, int] = {}
        for c in matrix:
            counts[c["outcome"]] = counts.get(c["outcome"], 0) + 1
        rest = ", ".join(f"{n} {o}" for o, n in counts.items() if o != "ok")
        return f"{counts.get('ok', 0)} of {len(matrix)} cells passed" + (
            f" ({rest})" if rest else ""
        )
    census = result.get("census")
    if census is not None:
        usable = sum(1 for c in census if c["usable"])
        return f"{usable} of {len(census)} cases usable"
    return f"ceiling {result.get('ceiling') or '–'} hosts"


def _census_md(census: list[dict[str, Any]], spec: dict[str, Any]) -> list[str]:
    k = (spec.get("census") or {}).get("per_image", 5)
    lines = [
        "",
        f"One step per case: {k} nodes of it as the client hosts of a small campus (a base "
        "router and switches, one base server). Host MB / node is estimated: the step's memory "
        "change less its base nodes, costed at the reference (workstation · kathara/base) per "
        "node. Cgroup MB is the nodes' own; CPU is over the hold (100 = one core). Usable: it "
        "passed, or only the host ran out of memory.",
        "",
        "| Case | Outcome | Deploy s | Ready s | Host MB / node (est.) | Cgroup MB / node "
        "| CPU % / node | Disk MB / node | Usable |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for c in census:
        outcome = c["outcome"] + (f": {c['detail']}" if c.get("detail") else "")
        lines.append(
            f"| `{c['case']}` | {outcome} | {_num(c.get('deploy_s'))} | {_num(c.get('ready_s'), 2)} "
            f"| {_mb(c.get('host_mem_per_node'))} | {_mb(c.get('cgroup_mem_per_node'))} "
            f"| {_num(c.get('cpu_pct_per_node'), 2)} | {_mb(c.get('disk_per_node'))} "
            f"| {'yes' if c['usable'] else 'no'} |"
        )
    return [*lines, ""]


# The matrix grids: (title, the cell's figure, which protocol it applies to).
_GRIDS: list[tuple[str, Callable[[dict[str, Any]], str], str | None]] = [
    ("Delivered (% of asked)", lambda c: _pct(c.get("delivered_ratio")), None),
    ("Slowest flow (% of asked)", lambda c: _pct(c.get("flow_ratio_min")), None),
    ("RTT p95 (ms)", lambda c: _num(c.get("rtt_ms_p95")), "tcp"),
    ("Retransmits", lambda c: _num(c.get("retransmits"), 0), "tcp"),
    ("Jitter p95 (ms)", lambda c: _num(c.get("jitter_ms_p95"), 2), "udp"),
    ("Loss %", lambda c: _num(c.get("lost_percent"), 2), "udp"),
    ("Host CPU % over idle", lambda c: _num(c.get("cpu_delta")), None),
    (
        "Docker cores",
        lambda c: _num(
            None if c.get("hold_docker_cpu_mean") is None else c["hold_docker_cpu_mean"] / 100, 2
        ),
        None,
    ),
]


def _matrix_md(cells: list[dict[str, Any]], spec: dict[str, Any]) -> list[str]:
    """A grid per group (the axes besides the grid's two) and figure, then
    every cell in the order it ran."""
    m = spec.get("matrix") or {}
    axes = list((m.get("axes") or {}).keys())
    grid = m.get("grid") or [a for a in axes if a not in ("pattern", "protocol")][:2]
    if len(grid) < 2 or not cells:
        return []
    row_axis, col_axis = grid
    rows_v, cols_v = m["axes"][row_axis], m["axes"][col_axis]
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for c in cells:
        key = tuple((k, v) for k, v in c["cell"].items() if k not in (row_axis, col_axis, "id"))
        groups.setdefault(key, []).append(c)
    rank = {k: [str(x) for x in vs] for k, vs in (m.get("axes") or {}).items()}
    if "pattern" not in rank:
        rank["pattern"] = [p["id"] for p in m.get("patterns") or []]

    def order(key: tuple) -> list[int]:  # the spec's axis order, not the run's
        return [rank.get(k, []).index(str(v)) if str(v) in rank.get(k, []) else 0 for k, v in key]

    groups = dict(sorted(groups.items(), key=lambda kv: order(kv[0])))
    lines = [
        "",
        f"Traffic matrix: {len(cells)} cells, {row_axis} (rows) × {col_axis} (columns), "
        f"per {', '.join(k for k, _ in next(iter(groups))) or 'cell'}; each cell held "
        f"{spec.get('hold_s')}s after a {m.get('ramp_s', 5)}s ramp and a {m.get('gap_s', 10)}s "
        "idle gap (host CPU over idle compares the two).",
    ]
    for key, group in groups.items():
        at = {(c["cell"].get(row_axis), c["cell"].get(col_axis)): c for c in group}
        protocol = dict(key).get("protocol") or next(
            (c["cell"].get("protocol") for c in group if c["cell"].get("protocol")), None
        )
        title = " · ".join(f"{k} {v}" for k, v in key)
        for name, fig, only in _GRIDS:
            if only and protocol and protocol != only:
                continue
            lines += [
                "",
                f"**{title} — {name}**",
                "",
                f"| {row_axis} \\ {col_axis} | "
                + " | ".join(_short(col_axis, v) for v in cols_v)
                + " |",
                "|---|" + "---:|" * len(cols_v),
            ]
            for rv in rows_v:
                cells_row = [at.get((rv, cv)) for cv in cols_v]
                lines.append(
                    f"| {_short(row_axis, rv)} | "
                    + " | ".join(fig(c) if c else "–" for c in cells_row)
                    + " |"
                )
    return lines


def _rest_line(rest: dict[str, Any] | None) -> list[str]:
    if not rest or not rest.get("samples"):
        return []
    return [
        f"- **At rest (before the first step):** {_mb(rest.get('mem_used'))} of "
        f"{_mb(rest.get('mem_total'))} MB used ({_num(rest.get('mem_used_pct'))}%) · "
        f"host CPU {_num(rest.get('vm_cpu_pct'))}% · Docker processes "
        f"{_mb(rest.get('docker_rss'))} MB · Docker's disk {_num(rest.get('disk_used_pct'))}% used"
    ]


def _steps_line(spec: dict[str, Any]) -> str:
    if spec.get("matrix"):
        n = len(matrix_cells(spec["matrix"]))
        return (
            f"traffic matrix of {n} cells on one deployment of {(spec.get('scale') or ['?'])[0]} hosts "
            f"× {spec.get('repetitions', 1)}"
        )
    if spec.get("census"):
        c = spec["census"]
        cases = len(c.get("cases") or [])
        return f"census of {cases} cases, {c.get('per_image', 5)} nodes each × {spec.get('repetitions', 1)}"
    a = spec.get("adaptive")
    if not a:
        return f"scale {spec.get('scale')} × {spec.get('repetitions', 1)}"
    return (
        f"adaptive from {a.get('start')} hosts toward {a.get('target_mem_pct', 93):g}% memory, "
        f"done at ≥ {a.get('reach_mem_pct', 90):g}% (closing {a.get('approach', 0.6):g} of the "
        f"projected gap per step, ≥ {a.get('min_step', 25)} hosts, ≤ ×{a.get('max_factor', 2):g}), "
        f"failures on a host limit retried lower (descend {a.get('descend', 0.7):g}), "
        f"ceiling rerun ×{a.get('confirm', 2)}"
    )


def _bps(x: float | None) -> str:
    return "–" if x is None else f"{x / 1e6:.2f}"


def _pct(x: float | None) -> str:
    return "–" if x is None else f"{x * 100:.1f}%"


def _pm(spread: dict[str, Any] | None, f) -> str:
    if not spread or spread.get("mean") is None:
        return "–"
    return f"{f(spread['mean'])} ± {f(spread['std'] or 0)}"


def _spread_table(entries: list[dict[str, Any]]) -> list[str]:
    """Repetitions folded per scale (mean ± sample std), when a scale ran more than once."""
    entries = [e for e in entries if e.get("runs", 0) > 1]
    if not entries:
        return []
    lines = [
        "",
        "Per scale over its repetitions (mean ± std):",
        "",
        "| Hosts | Runs (ok) | Nodes | Deploy s | Ready s | Destroy s | Marginal MB/node "
        "| Host CPU % | Docker cores | Host mem % max | Delivered |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for e in entries:
        lines.append(
            f"| {e['scale']} | {e['runs']} ({e['ok']}) | {e.get('nodes', '–')} "
            f"| {_pm(e.get('deploy_s'), _num)} | {_pm(e.get('ready_s'), lambda x: _num(x, 2))} "
            f"| {_pm(e.get('destroy_s'), _num)} | {_pm(e.get('marginal_mem_per_node'), _mb)} "
            f"| {_pm(e.get('hold_cpu_mean'), _num)} "
            f"| {_pm(e.get('hold_docker_cpu_mean'), lambda x: _num(x / 100, 2))} "
            f"| {_pm(e.get('hold_mem_pct_max'), _num)} "
            f"| {_pm(e.get('delivered_ratio'), _pct)} |"
        )
    return lines


def _traffic_table(rows: list[dict[str, Any]]) -> list[str]:
    """The network side of traffic steps, from iperf3's own measurements."""
    rows = [r for r in rows if r.get("flows")]
    if not rows:
        return []
    lines = [
        "",
        "Network (iperf3, over the whole run): RTT for TCP flows, jitter and loss for UDP; "
        "median and p95 of the flows' own medians, and the highest reading.",
        "",
        "| Hosts | # | Flows | Asked Mb/s | Delivered | Data MB | Slowest flow Mb/s "
        "| RTT ms (p50 / p95 / max) | Retransmits | Jitter ms (p50 / p95 / max) | Loss % (all / worst flow) |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        rtt = " / ".join(_num(r.get(f"rtt_ms_{k}"), 1) for k in ("p50", "p95", "max"))
        jit = " / ".join(_num(r.get(f"jitter_ms_{k}"), 2) for k in ("p50", "p95", "max"))
        lines.append(
            f"| {r['scale']} | {r['rep']} | {r['flows']} | {_bps(r.get('offered_bps'))} "
            f"| {_pct(r.get('delivered_ratio'))} | {_mb(r.get('bytes_received'))} "
            f"| {_bps(r.get('slowest_flow_bps'))} | {rtt} | {r.get('retransmits', '–')} | {jit} "
            f"| {_num(r.get('lost_percent'), 2)} / {_num(r.get('flow_loss_pct_max'), 2)} |"
        )
    return lines


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
    if g.get("random"):
        return _random_line(g, shape)
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


def _pool_text(pool: list[dict[str, Any]]) -> str:
    return ", ".join(
        f"{e['type']} ({' / '.join(i.split('/')[-1] for i in e['images'])})" for e in pool
    )


def _random_line(g: dict[str, Any], shape: str) -> str:
    r = g["random"]
    parts = [
        f"generated, random (seed {g.get('seed', 0)}), {shape}: each node draws a type of its "
        f"pool with equal odds, then one of its images. Hosts ({len(r['hosts'])} types): "
        f"{_pool_text(r['hosts'])}"
    ]
    if r.get("switches"):
        parts.append(f"Switches: {_pool_text(r['switches'])}")
    if r.get("routers"):
        parts.append(f"Routers: {_pool_text(r['routers'])}")
    servers = g.get("servers", 1) if not g.get("server_mix") else None
    if servers:
        parts.append(f"Servers: {servers} × {g.get('server_type', 'workstation')}")
    elif g.get("server_mix"):
        parts.append("Servers: " + ", ".join(_kind(e) for e in g["server_mix"]))
    return ". ".join(parts)


def _traffic_line(spec: dict[str, Any]) -> str:
    m = spec.get("matrix")
    if m:
        pats = "; ".join(
            f"{p['id']}: {'mesh' if p.get('kind') == 'mesh' else 'clients → servers'}"
            for p in m["patterns"]
        )
        axes = ", ".join(
            f"{k} {' / '.join(_short(k, v) for v in vs)}" for k, vs in (m.get("axes") or {}).items()
        )
        return f"per cell: {pats}; axes: {axes} (iperf3 report every {m.get('interval_s', 10):g}s)"
    t = spec.get("traffic")
    if not t:
        return "idle (no traffic)"
    parts = []
    for p in t.get("patterns") or []:
        what = "mesh" if p.get("kind") == "mesh" else "clients → servers"
        extra = f", {p.get('fanout', 1)} peer(s) each" if p.get("kind") == "mesh" else ""
        burst = (
            f" in bursts every {p['burst_interval_ms']} ms" if p.get("burst_interval_ms") else ""
        )
        parts.append(
            f"{what}{extra}, {p.get('protocol', 'tcp').upper()} {p.get('bitrate')} per flow{burst}"
        )
    return "; ".join(parts) + f" (ramp {t.get('ramp_s', 0)}s)"
