"""Monitor sweeps → rates, groups and aggregates (pure).

The collector helper (``tools/nettools/ae3gis_collect.py``) prints cumulative
counters for the host and every container, one JSON line per sweep. This
module turns two consecutive sweeps into what the monitor records and shows:

- host: VM CPU % (0–100 of all cores) and cores used, memory used
  (``MemTotal - MemAvailable``), load, PSI stall % over the interval (share of
  wall time some/all tasks waited on CPU, memory or IO), Docker's own
  processes (dockerd, containerd, shims, VDE switches: count, RSS, CPU %)
- containers: CPU (100 = one core), memory without page cache, pids, OOM
  kills, interface rates (``domain/telemetry.rates``)

Containers are classified into groups (``Target.kind``): ``node`` (the watched
lab's nodes), ``tool`` (AE3GIS sidecars and helpers), ``other_lab`` (another
Kathara lab), ``other`` (anything else: the backend, BuildKit…). Interface
counters only count for nodes: sidecars share a node's network namespace and
would count the same bytes twice.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any

from domain import telemetry
from engine.base import ContainerRef, IfaceCounters, RawStats

# Labels (see engine/docker_sidecar.py and Kathara's own).
_SIDECAR = "ae3gis.sidecar"
_PURPOSE = "ae3gis.purpose"
_JOB = "ae3gis.job"

HOST_FIELDS = (
    "vm_cpu_pct",
    "cores_used",
    "mem_total",
    "mem_used",
    "mem_available",
    "mem_used_pct",
    "slab",
    "load1",
    "psi_cpu_some",
    "psi_mem_some",
    "psi_mem_full",
    "psi_io_some",
    "procs",
    "sweep_ms",
)
INFRA_NAMES = ("dockerd", "containerd", "containerd-shim", "vde_switch")
GROUPS = ("node", "tool", "other_lab", "other")


@dataclass
class Sweep:
    """One collector line."""

    t: float  # unix seconds
    sweep_ms: float
    ncpu: int
    clk_tck: int
    host: dict[str, Any]
    infra: dict[str, list[int]]
    containers: dict[str, RawStats]  # short (12-char) container id -> counters


def parse_line(line: str | bytes) -> Sweep | None:
    """A collector line, or None for anything else (blank, an error report)."""
    try:
        raw = json.loads(line)
    except ValueError:
        return None
    if not isinstance(raw, dict) or raw.get("v") != 1:
        return None
    t = float(raw["t"])
    ncpu = int(raw.get("ncpu") or 1)
    containers: dict[str, RawStats] = {}
    for cid, v in (raw.get("c") or {}).items():
        usage, mem, inactive, mem_max, pids, oom, ifaces = v
        containers[cid] = RawStats(
            target=cid,
            kind="other",
            ts=t,
            cpu_total_ns=int(usage) * 1000,
            system_cpu_ns=None,
            online_cpus=ncpu,
            mem_usage=int(mem or 0),
            mem_inactive_file=inactive,
            mem_limit=mem_max,
            pids=pids,
            oom_kills=oom,
            ifaces={
                name: IfaceCounters(
                    rx_bytes=c[0],
                    rx_packets=c[1],
                    rx_errors=c[2],
                    rx_dropped=c[3],
                    tx_bytes=c[4],
                    tx_packets=c[5],
                    tx_errors=c[6],
                    tx_dropped=c[7],
                )
                for name, c in (ifaces or {}).items()
            },
        )
    return Sweep(
        t=t,
        sweep_ms=float(raw.get("sweep_ms") or 0.0),
        ncpu=ncpu,
        clk_tck=int(raw.get("clk_tck") or 100),
        host=raw.get("host") or {},
        infra=raw.get("infra") or {},
        containers=containers,
    )


# ── host ──────────────────────────────────────────────────────────────


def _psi_pct(prev: Sweep, cur: Sweep, res: str, kind: str, dt: float) -> float | None:
    try:
        a = prev.host["psi"][res][kind][1]
        b = cur.host["psi"][res][kind][1]
    except (KeyError, IndexError, TypeError):
        return None
    return round(max(b - a, 0) / (dt * 1e6) * 100, 2)


def host_rates(prev: Sweep | None, cur: Sweep) -> dict[str, Any]:
    """The host row for ``cur`` (rates need ``prev``; the first sweep has none)."""
    mem = cur.host.get("mem") or {}
    total = mem.get("MemTotal")
    available = mem.get("MemAvailable")
    used = total - available if total is not None and available is not None else None
    load = cur.host.get("load") or [None]
    row: dict[str, Any] = {
        "vm_cpu_pct": None,
        "cores_used": None,
        "mem_total": total,
        "mem_used": used,
        "mem_available": available,
        "mem_used_pct": round(used / total * 100, 2) if used is not None and total else None,
        "slab": mem.get("Slab"),
        "load1": load[0],
        "psi_cpu_some": None,
        "psi_mem_some": None,
        "psi_mem_full": None,
        "psi_io_some": None,
        "procs": cur.host.get("procs"),
        "sweep_ms": cur.sweep_ms,
        "infra": {
            name: {"count": v[0], "rss": v[1], "cpu_pct": None} for name, v in cur.infra.items()
        },
    }
    if prev is None:
        return row
    dt = cur.t - prev.t
    if dt <= 0:
        return row
    a, b = prev.host.get("cpu") or [], cur.host.get("cpu") or []
    if len(a) >= 5 and len(b) >= 5:
        d_total = sum(b) - sum(a)
        d_idle = (b[3] + b[4]) - (a[3] + a[4])
        if d_total > 0:
            busy = d_total - d_idle
            row["vm_cpu_pct"] = round(busy / d_total * 100, 2)
            row["cores_used"] = round(busy / cur.clk_tck / dt, 3)
    row["psi_cpu_some"] = _psi_pct(prev, cur, "cpu", "some", dt)
    row["psi_mem_some"] = _psi_pct(prev, cur, "memory", "some", dt)
    row["psi_mem_full"] = _psi_pct(prev, cur, "memory", "full", dt)
    row["psi_io_some"] = _psi_pct(prev, cur, "io", "some", dt)
    for name, v in cur.infra.items():
        p = prev.infra.get(name)
        if p is not None and v[2] >= p[2]:
            row["infra"][name]["cpu_pct"] = round((v[2] - p[2]) / cur.clk_tck / dt * 100, 2)
    return row


# ── classification ────────────────────────────────────────────────────


@dataclass
class Target:
    kind: str  # node | tool | other_lab | other
    name: str  # node id for nodes, container name otherwise
    purpose: str | None = None
    job_id: str | None = None


@dataclass
class Scope:
    """What a monitor watches: one lab's nodes (``lab_hash`` + machine → node
    id), of which ``selected`` are recorded one by one (None = all of them)."""

    lab_hash: str | None = None
    node_for_machine: dict[str, str] = field(default_factory=dict)
    selected: set[str] | None = None
    step: str = ""

    def records(self, node_id: str) -> bool:
        return self.selected is None or node_id in self.selected


def classify(refs: list[ContainerRef], scope: Scope) -> dict[str, Target]:
    """Short container id → what it is, for this scope."""
    out: dict[str, Target] = {}
    for ref in refs:
        labels = ref.labels or {}
        sid = ref.id[:12]
        if labels.get(_SIDECAR) == "1":
            out[sid] = Target(
                "tool", ref.name, purpose=labels.get(_PURPOSE), job_id=labels.get(_JOB)
            )
        elif labels.get("app") == "kathara":
            node = scope.node_for_machine.get(labels.get("name", ""))
            if scope.lab_hash and labels.get("lab_hash") == scope.lab_hash and node:
                out[sid] = Target("node", node)
            else:
                out[sid] = Target("other_lab", labels.get("name") or ref.name)
        else:
            out[sid] = Target("other", ref.name)
    return out


# ── aggregates ────────────────────────────────────────────────────────


def percentile(values: list[float], q: float) -> float | None:
    """Linear-interpolated percentile (q in 0..100) of ``values``."""
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * q / 100
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"sum": None, "mean": None, "p50": None, "p95": None, "max": None}
    return {
        "sum": round(sum(values), 3),
        "mean": round(sum(values) / len(values), 3),
        "p50": round(percentile(values, 50), 3),
        "p95": round(percentile(values, 95), 3),
        "max": round(max(values), 3),
    }


def node_row(sample: dict[str, Any]) -> dict[str, Any]:
    """A ``telemetry.rates`` sample → one flat row with the interfaces summed."""
    ifaces = sample.get("ifaces") or {}
    return {
        "target": sample["target"],
        "kind": sample["kind"],
        "cpu_pct": sample.get("cpu_percent"),
        "mem_used": sample.get("mem_used"),
        "mem_limit": sample.get("mem_limit"),
        "pids": sample.get("pids"),
        "oom_kills": sample.get("oom_kills"),
        "rx_bps": sum(i["rx_bps"] for i in ifaces.values()) if ifaces else None,
        "tx_bps": sum(i["tx_bps"] for i in ifaces.values()) if ifaces else None,
        "rx_pps": round(sum(i["rx_pps"] for i in ifaces.values()), 1) if ifaces else None,
        "tx_pps": round(sum(i["tx_pps"] for i in ifaces.values()), 1) if ifaces else None,
        "drops": sum(i["rx_dropped"] + i["tx_dropped"] for i in ifaces.values())
        if ifaces
        else None,
        "errors": sum(i["errors"] for i in ifaces.values()) if ifaces else None,
    }


@dataclass
class SweepResult:
    """Everything one sweep produced."""

    t: float  # seconds since the monitor started
    host: dict[str, Any]
    groups: dict[str, dict[str, Any]]
    nodes: list[dict[str, Any]]  # rows for recorded nodes and tools
    ifaces: list[dict[str, Any]]  # per-interface rows for recorded nodes
    oom: list[str]  # nodes with a new OOM kill since the last sweep
    seen_nodes: set[str]


def process(
    prev: Sweep | None,
    cur: Sweep,
    targets: dict[str, Target],
    scope: Scope,
    t0: float,
) -> SweepResult:
    """Rates, rows and group totals for one sweep."""
    t = round(cur.t - t0, 3)
    host = host_rates(prev, cur)
    groups: dict[str, dict[str, Any]] = {
        g: {"count": 0, "cpu_pct": 0.0, "mem_used": 0} for g in GROUPS
    }
    nodes: list[dict[str, Any]] = []
    ifaces: list[dict[str, Any]] = []
    oom: list[str] = []
    seen: set[str] = set()
    for cid, raw in cur.containers.items():
        target = targets.get(cid) or Target("other", cid)
        raw.kind = target.kind  # type: ignore[assignment]
        raw.target = target.name
        if target.kind != "node":
            raw.ifaces = {}
        before = prev.containers.get(cid) if prev else None
        sample = telemetry.rates(before, raw, t)
        g = groups[target.kind]
        g["count"] += 1
        g["cpu_pct"] += sample["cpu_percent"] or 0.0
        g["mem_used"] += sample["mem_used"] or 0
        if target.kind == "node":
            seen.add(target.name)
            if (
                before is not None
                and raw.oom_kills is not None
                and before.oom_kills is not None
                and raw.oom_kills > before.oom_kills
            ):
                oom.append(target.name)
            if not scope.records(target.name):
                continue
            for name, rates in sample["ifaces"].items():
                ifaces.append({"target": target.name, "iface": name, **rates})
        elif target.kind != "tool":
            continue
        row = node_row(sample)
        if target.kind == "tool":
            row["purpose"] = target.purpose
        nodes.append(row)
    for g in groups.values():
        g["cpu_pct"] = round(g["cpu_pct"], 2)
    return SweepResult(t, host, groups, nodes, ifaces, oom, seen)


def selection_summary(rows: list[dict[str, Any]], top: int = 5) -> dict[str, Any]:
    """Aggregates and top-N over the recorded nodes of one sweep."""
    nodes = [r for r in rows if r["kind"] == "node"]

    def col(key: str) -> list[float]:
        return [r[key] for r in nodes if r.get(key) is not None]

    def top_by(key: str) -> list[list[Any]]:
        ranked = sorted(
            (r for r in nodes if r.get(key) is not None), key=lambda r: r[key], reverse=True
        )
        return [[r["target"], r[key]] for r in ranked[:top]]

    net = [
        {**r, "net_bps": (r.get("rx_bps") or 0) + (r.get("tx_bps") or 0)}
        for r in nodes
        if r.get("rx_bps") is not None
    ]
    net_top = sorted(net, key=lambda r: r["net_bps"], reverse=True)[:top]
    return {
        "count": len(nodes),
        "cpu_pct": stats(col("cpu_pct")),
        "mem_used": stats(col("mem_used")),
        "rx_bps": stats(col("rx_bps")),
        "tx_bps": stats(col("tx_bps")),
        "top": {
            "cpu_pct": top_by("cpu_pct"),
            "mem_used": top_by("mem_used"),
            "net_bps": [[r["target"], r["net_bps"]] for r in net_top],
        },
    }


class RunningStats:
    """Count / mean / max of one metric without keeping the values."""

    __slots__ = ("n", "total", "peak")

    def __init__(self) -> None:
        self.n = 0
        self.total = 0.0
        self.peak: float | None = None

    def add(self, value: float | None) -> None:
        if value is None:
            return
        self.n += 1
        self.total += value
        self.peak = value if self.peak is None else max(self.peak, value)

    def to_dict(self) -> dict[str, float | None]:
        return {
            "mean": round(self.total / self.n, 3) if self.n else None,
            "max": round(self.peak, 3) if self.peak is not None else None,
        }


def series_summary(values: list[float]) -> dict[str, float | None]:
    """mean / p50 / p95 / max of a host series."""
    s = stats(values)
    return {k: s[k] for k in ("mean", "p50", "p95", "max")}
