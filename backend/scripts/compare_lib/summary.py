"""One run's step files → the comparison's numbers and tables.

Pure Python over the JSON the runner writes (``<out>/<platform>/<step>.json``),
used by ``compare.py summarize`` and by the analysis notebook
(``analysis/benchlib/compare.py``).

- **E0**, the platform at rest: the last 3 min of the idle window.
- **E1**, per lab size: every rep that finished ``ok``, as mean and range.
  Memory is the growth over the step's own reference (the 30 s before the
  deploy, after the VM's restart), so platforms with different idle costs
  compare on what a lab adds; the idle cost is E0.
- **E2**: latency, flat-out TCP, and per pattern the highest rate every run
  passed (a repeat that fails turns its rate into a failure; a failure that
  passes on its repeat stays a failure), with CPU per 100 Mb/s over the
  reference before the lab's traffic.

On the host a platform is its VM process plus its helpers (Docker Desktop's
backend and services, VMware Fusion's): footprint and cores add up.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

PLATFORMS = ("ae3gis", "gns3")
GB = 2**30
MB = 2**20


# ── loading ──


def load(out: Path) -> dict[str, dict[str, dict]]:
    """{platform: {step name: record}} for one run directory."""
    recs: dict[str, dict[str, dict]] = {}
    for p in PLATFORMS:
        for f in sorted((out / p).glob("*.json")):
            recs.setdefault(p, {})[f.stem] = json.loads(f.read_text())
    return recs


def _get(d: Any, *path, default=None):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def _sum(*xs):
    vals = [x for x in xs if x is not None]
    return sum(vals) if vals else None


def _diff(a, b):
    return None if a is None or b is None else a - b


def host_footprint(host: dict, key: str = "footprint") -> float | None:
    """The VM process's and its helpers' footprint (or ``rss``, ``*_max``)."""
    return _sum(_get(host, "vm", key), _get(host, "helpers", key))


def host_cores(host: dict) -> float | None:
    return _sum(_get(host, "vm", "cores"), _get(host, "helpers", "cores"))


def stats(xs: list[float | None]) -> dict[str, float | int | None]:
    vals = [x for x in xs if x is not None]
    if not vals:
        return {"n": 0, "mean": None, "min": None, "max": None}
    return {
        "n": len(vals),
        "mean": statistics.fmean(vals),
        "min": min(vals),
        "max": max(vals),
    }


# ── E0 ──


def e0_row(rec: dict) -> dict[str, Any]:
    w = _get(rec, "phases", "settled") or _get(rec, "phases", "idle") or {}
    vm, host = w.get("vm") or {}, w.get("host") or {}
    infra = vm.get("infra") or {}
    return {
        "rep": rec.get("rep"),
        "vm_mem": vm.get("mem_used"),
        "vm_cores": vm.get("cpu_cores"),
        "other_containers_mem": _get(vm, "containers", "other_mem"),
        "infra_rss": _sum(*(v.get("rss") for v in infra.values())),
        "infra": {k: v.get("rss") for k, v in infra.items()},
        "host_footprint": host_footprint(host),
        "host_footprint_vm": _get(host, "vm", "footprint"),
        "host_footprint_helpers": _get(host, "helpers", "footprint"),
        "host_rss": host_footprint(host, "rss"),
        "host_cores": host_cores(host),
        "host_cores_vm": _get(host, "vm", "cores"),
        "vm_disk": _get(rec, "vm", "vm_disk_bytes"),
        "vm_start_s": _get(rec, "restart", "start_s"),
        "vm_stop_s": _get(rec, "restart", "stop_s"),
    }


# ── E1 ──


def _phase_s(rec: dict, name: str) -> float | None:
    t = _get(rec, "phases", name, "t")
    return t[1] - t[0] if t else None


def _timings(rec: dict) -> dict:
    # The runner's first version kept the teardown's timings in "deploy".
    return {**(rec.get("deploy") or {}), **(rec.get("destroy") or {})}


def e1_row(rec: dict) -> dict[str, Any]:
    ph = rec.get("phases") or {}
    ref, hold = ph.get("reference") or {}, ph.get("hold") or {}
    nodes = rec.get("nodes") or 0
    ref_mem, hold_mem = _get(ref, "vm", "mem_used"), _get(hold, "vm", "mem_used")
    growth = _diff(hold_mem, ref_mem)
    lab_mem = _get(hold, "vm", "containers", "lab_mem")
    ref_fp = host_footprint(ref.get("host") or {})
    busy = [ph.get(n) or {} for n in ("deploy", "ready", "settle", "hold")]
    peak_vm = max((_get(w, "vm", "mem_used_max") or 0 for w in busy), default=0) or None
    peak_fp = max(
        (host_footprint(w.get("host") or {}, "footprint_max") or 0 for w in busy), default=0
    )
    infra = _get(hold, "vm", "infra") or {}
    deploy_s = _get(rec, "deploy", "deploy_s")
    ready_s = _phase_s(rec, "ready")
    return {
        "size": rec.get("size"),
        "rep": rec.get("rep"),
        "nodes": nodes,
        "status": rec.get("status"),
        "deploy_s": deploy_s,
        "ready_s": ready_s,
        "usable_s": _sum(deploy_s, ready_s) if deploy_s is not None else None,
        "teardown_s": rec.get("destroy_s"),
        "timings": _timings(rec),
        "vm_mem_ref": ref_mem,
        "vm_mem_hold": hold_mem,
        "vm_mem_growth": growth,
        "vm_mem_per_node": growth / nodes if growth is not None and nodes else None,
        "vm_mem_peak_growth": _diff(peak_vm, ref_mem),
        "lab_mem": lab_mem,
        "lab_mem_per_node": lab_mem / nodes if lab_mem is not None and nodes else None,
        # What the platform itself added for the lab: shims, switches/bridges, …
        "platform_mem_growth": _diff(growth, lab_mem),
        "vm_mem_after": _diff(_get(ph, "after", "vm", "mem_used"), ref_mem),
        "host_footprint_ref": ref_fp,
        "host_footprint_growth": _diff(host_footprint(hold.get("host") or {}), ref_fp),
        "host_footprint_peak_growth": _diff(peak_fp or None, ref_fp),
        "host_cores_ref": host_cores(ref.get("host") or {}),
        "host_cores_deploy": host_cores(_get(ph, "deploy", "host") or {}),
        "host_cores_hold": host_cores(hold.get("host") or {}),
        "vm_cores_deploy": _get(ph, "deploy", "vm", "cpu_cores"),
        "vm_cores_hold": _get(hold, "vm", "cpu_cores"),
        "lab_cores_hold": _get(hold, "vm", "containers", "lab_cores"),
        "infra_cores_hold": _sum(*(v.get("cores") for v in infra.values())),
        "infra_rss_hold": _sum(*(v.get("rss") for v in infra.values())),
        "roles": rec.get("roles"),
        "vm_disk_growth": _diff(rec.get("disk_hold"), rec.get("disk_before")),
        "vm_disk_left": _diff(rec.get("disk_after"), rec.get("disk_before")),
        "docker_disk_growth": _diff(_get(hold, "vm", "disk_used"), _get(ref, "vm", "disk_used")),
        "retried": len(rec.get("retried") or []),
        "error": rec.get("error") or rec.get("reason"),
    }


E1_METRICS = (
    "deploy_s",
    "ready_s",
    "usable_s",
    "teardown_s",
    "vm_mem_growth",
    "vm_mem_per_node",
    "vm_mem_peak_growth",
    "lab_mem_per_node",
    "platform_mem_growth",
    "vm_mem_after",
    "host_footprint_growth",
    "host_footprint_peak_growth",
    "host_cores_deploy",
    "host_cores_hold",
    "vm_cores_deploy",
    "vm_cores_hold",
    "lab_cores_hold",
    "infra_cores_hold",
    "vm_disk_growth",
    "docker_disk_growth",
)


def e1_table(recs: dict[str, dict[str, dict]]) -> dict[str, dict[int, dict[str, Any]]]:
    """{platform: {size: {"reps", "ok", "statuses", metric: stats}}}."""
    out: dict[str, dict[int, dict[str, Any]]] = {}
    for p, steps in recs.items():
        rows: dict[int, list[dict]] = {}
        for name, rec in steps.items():
            if name.startswith("e1-") and rec.get("size") is not None:
                rows.setdefault(rec["size"], []).append(e1_row(rec))
        for size, rs in sorted(rows.items()):
            ok = [r for r in rs if r["status"] == "ok"]
            cell: dict[str, Any] = {
                "reps": len(rs),
                "ok": len(ok),
                "nodes": next((r["nodes"] for r in rs if r["nodes"]), None),
                "statuses": sorted({r["status"] for r in rs}),
                "errors": [r["error"] for r in rs if r["error"]][:3],
            }
            for m in E1_METRICS:
                cell[m] = stats([r[m] for r in ok])
            out.setdefault(p, {})[size] = cell
    return out


# ── E2 ──


def _rate(rate: str) -> float:
    mult = {"K": 1e3, "M": 1e6, "G": 1e9}
    return float(rate[:-1]) * mult[rate[-1]] if rate[-1] in mult else float(rate)


def _step_cpu(s: dict, ref: dict) -> dict[str, float | None]:
    """Cores during a traffic window, and over the lab's idle reference per
    100 Mb/s delivered."""
    host = host_cores(s.get("host") or {})
    vm = _get(s, "vm", "cpu_cores")
    host0 = host_cores(ref.get("host") or {})
    vm0 = _get(ref, "vm", "cpu_cores")
    per = (s.get("delivered_bps") or 0) / 1e8
    return {
        "host_cores": host,
        "vm_cores": vm,
        "host_cores_per_100m": (host - (host0 or 0)) / per if host is not None and per else None,
        "vm_cores_per_100m": (vm - (vm0 or 0)) / per if vm is not None and per else None,
    }


def ladder_result(steps: list[dict]) -> dict[str, Any]:
    """One pattern/protocol's ladder: the highest rate every run at it (and
    at every rate below) passed."""
    by_rate: dict[str, list[dict]] = {}
    for s in steps:
        by_rate.setdefault(s["rate"], []).append(s)
    best = None
    for rate in sorted(by_rate, key=_rate):
        if all(s["passed"] for s in by_rate[rate]):
            best = rate
        else:
            break
    peak = max(steps, key=lambda s: s.get("delivered_bps") or 0, default=None)
    return {
        "max_rate": best,
        "max_rate_bps": _rate(best) if best else None,
        "flows": steps[0].get("flows") if steps else None,
        "max_offered_bps": _rate(best) * (steps[0].get("flows") or 0) if best else None,
        "peak_delivered_bps": peak.get("delivered_bps") if peak else None,
        "rates_run": sorted(by_rate, key=_rate),
    }


def e2_summary(rec: dict) -> dict[str, Any]:
    ref = rec.get("reference") or {}
    flat: dict[str, list[dict]] = {}
    for s in rec.get("flatout") or []:
        flat.setdefault(s.get("kind"), []).append({**s, **_step_cpu(s, ref)})
    ladder: dict[str, list[dict]] = {}
    for s in rec.get("ladder") or []:
        ladder.setdefault(f"{s['pattern']}/{s['protocol']}", []).append({**s, **_step_cpu(s, ref)})
    return {
        "status": rec.get("status"),
        "error": rec.get("error"),
        "latency": rec.get("latency") or {},
        "flatout": {
            k: {
                "gbps": stats([(s.get("delivered_bps") or 0) / 1e9 for s in v]),
                "host_cores": stats([s["host_cores"] for s in v]),
                "vm_cores": stats([s["vm_cores"] for s in v]),
                "retransmits": stats([s.get("retransmits") for s in v]),
            }
            for k, v in flat.items()
        },
        "ladder": {k: {**ladder_result(v), "steps": v} for k, v in ladder.items()},
    }


def e2_common(e2: dict[str, dict]) -> dict[str, dict[str, Any]]:
    """Per pattern, the highest rate both platforms passed, and each one's
    CPU per 100 Mb/s there (the first run at it): CPU cost at equal load."""
    out: dict[str, dict[str, Any]] = {}
    keys = set.intersection(*(set(v["ladder"]) for v in e2.values())) if e2 else set()
    for k in sorted(keys):
        rates = [e2[p]["ladder"][k]["max_rate"] for p in e2]
        if None in rates:
            continue
        rate = min(rates, key=_rate)
        row: dict[str, Any] = {"rate": rate}
        for p, v in e2.items():
            s = next(
                (s for s in v["ladder"][k]["steps"] if s["rate"] == rate and not s["repeat"]),
                None,
            )
            row[p] = (
                {
                    k2: s.get(k2)
                    for k2 in (
                        "delivered_bps",
                        "host_cores",
                        "vm_cores",
                        "host_cores_per_100m",
                        "vm_cores_per_100m",
                        "rtt_p95_ms",
                        "jitter_ms",
                        "loss",
                    )
                }
                if s
                else None
            )
        out[k] = row
    return out


# ── everything ──


def summarize(out: Path) -> dict[str, Any]:
    recs = load(out)
    manifest = (
        json.loads((out / "manifest.json").read_text()) if (out / "manifest.json").exists() else {}
    )
    e0 = {
        p: [
            e0_row(r)
            for n, r in sorted(steps.items())
            if n.startswith("e0-") and r.get("status") == "ok"
        ]
        for p, steps in recs.items()
    }
    e0_mean = {
        p: {k: stats([r[k] for r in rows])["mean"] for k in rows[0] if k not in ("rep", "infra")}
        for p, rows in e0.items()
        if rows
    }
    e2 = {p: e2_summary(steps["e2"]) for p, steps in recs.items() if "e2" in steps}
    return {
        "host": _get(manifest, "host", "host"),
        "commit": manifest.get("commit"),
        "quick": manifest.get("quick"),
        "steps": {p: {n: r.get("status") for n, r in s.items()} for p, s in recs.items()},
        "vm": {
            p: next((r.get("vm") for r in s.values() if r.get("vm")), None) for p, s in recs.items()
        },
        "e0": {"reps": e0, "mean": e0_mean},
        "e1": e1_table(recs),
        "e2": e2,
        "e2_common": e2_common(e2),
    }


# ── tables ──


def _fmt(x, unit: str = "", nd: int = 1) -> str:
    if x is None:
        return "–"
    if unit == "GB":
        return f"{x / GB:.{nd}f}"
    if unit == "MB":
        return f"{x / MB:.{nd}f}"
    return f"{x:.{nd}f}"


def _pair(cells: dict[str, Any], unit="", nd=1, metric=None) -> str:
    vals = []
    for p in PLATFORMS:
        c = cells.get(p)
        if c is None:
            vals.append("–")
        elif metric and not c["ok"]:
            vals.append("/".join(c["statuses"]))
        else:
            v = c[metric]["mean"] if metric else c
            vals.append(_fmt(v, unit, nd))
    return " / ".join(vals)


def _ratio(a, g) -> str:
    return f"{g / a:.2f}×" if a and g is not None else "–"


def markdown(s: dict[str, Any]) -> str:
    """The summary as Markdown tables: every cell is ``AE3GIS / GNS3``, and
    the ratio column is GNS3 ÷ AE3GIS (above 1: GNS3 uses or takes more)."""
    lines = [
        f"# AE3GIS vs GNS3 on {s.get('host')}" + (" (quick dry run)" if s.get("quick") else ""),
        "",
        f"Commit `{(s.get('commit') or '')[:10]}`. Cells are **AE3GIS / GNS3**; "
        "ratios are GNS3 ÷ AE3GIS.",
        "",
    ]
    for p in PLATFORMS:
        vm = (s.get("vm") or {}).get(p) or {}
        if vm:
            lines.append(
                f"- **{p}:** {_get(vm, 'platform', 'version')}, Docker {vm.get('docker')}, "
                f"kernel {vm.get('kernel')}, {vm.get('ncpu')} CPUs, "
                f"{(vm.get('mem') or 0) / GB:.1f} GB, cgroup v{vm.get('cgroup')}"
            )
    lines.append("")

    # E0
    e0 = s["e0"]["mean"]
    if e0:
        lines += ["## E0: at rest (mean of reps, last 3 min)", ""]
        lines += ["| metric | AE3GIS / GNS3 | ratio |", "|---|---|---|"]
        rows = [
            ("host footprint, GB (VM + helpers)", "host_footprint", "GB", 2),
            ("  VM process", "host_footprint_vm", "GB", 2),
            ("  helpers", "host_footprint_helpers", "GB", 2),
            ("host cores (VM + helpers)", "host_cores", "", 3),
            ("memory used inside the VM, GB", "vm_mem", "GB", 2),
            ("CPU cores inside the VM", "vm_cores", "", 3),
            ("VM disk on the host, GB", "vm_disk", "GB", 1),
            ("VM start, s", "vm_start_s", "", 1),
        ]
        for label, k, unit, nd in rows:
            a, g = (e0.get(p, {}).get(k) for p in PLATFORMS)
            lines.append(
                f"| {label} | {_fmt(a, unit, nd)} / {_fmt(g, unit, nd)} | {_ratio(a, g)} |"
            )
        lines.append("")

    # E1
    e1 = s["e1"]
    sizes = sorted({size for v in e1.values() for size in v})
    if sizes:
        lines += [
            "## E1: lab lifecycle (mean of ok reps)",
            "",
            "| hosts | nodes | ok reps | deploy s | ready s | usable s | teardown s | usable ratio |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for size in sizes:
            cells = {p: e1.get(p, {}).get(size) for p in PLATFORMS}
            nodes = next((c["nodes"] for c in cells.values() if c and c["nodes"]), None)
            oks = " / ".join(
                str(c["ok"]) + "/" + str(c["reps"]) if c else "–" for c in cells.values()
            )
            a, g = (
                (cells[p] or {}).get("usable_s", {}).get("mean")
                if cells[p] and cells[p]["ok"]
                else None
                for p in PLATFORMS
            )
            lines.append(
                f"| {size} | {nodes} | {oks} | {_pair(cells, metric='deploy_s')} | "
                f"{_pair(cells, metric='ready_s')} | {_pair(cells, metric='usable_s')} | "
                f"{_pair(cells, metric='teardown_s')} | {_ratio(a, g)} |"
            )
        lines += [
            "",
            "## E1: what a lab adds (over the step's reference)",
            "",
            "| hosts | VM memory GB | per node MB | lab containers per node MB | platform's own GB | "
            "host footprint GB | footprint ratio | host cores at hold | VM cores at hold |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for size in sizes:
            cells = {p: e1.get(p, {}).get(size) for p in PLATFORMS}
            a, g = (
                (cells[p] or {}).get("host_footprint_growth", {}).get("mean")
                if cells[p] and cells[p]["ok"]
                else None
                for p in PLATFORMS
            )
            lines.append(
                f"| {size} | {_pair(cells, 'GB', 2, 'vm_mem_growth')} | "
                f"{_pair(cells, 'MB', 1, 'vm_mem_per_node')} | "
                f"{_pair(cells, 'MB', 1, 'lab_mem_per_node')} | "
                f"{_pair(cells, 'GB', 2, 'platform_mem_growth')} | "
                f"{_pair(cells, 'GB', 2, 'host_footprint_growth')} | {_ratio(a, g)} | "
                f"{_pair(cells, '', 2, 'host_cores_hold')} | {_pair(cells, '', 3, 'vm_cores_hold')} |"
            )
        lines.append("")

    # E2
    e2 = s["e2"]
    if e2:
        lines += ["## E2: network on the 100-host lab", ""]
        kinds = sorted({k for v in e2.values() for k in v["latency"]})
        if kinds:
            lines += ["| ping | p50 ms | p95 ms | max ms |", "|---|---|---|---|"]
            for k in kinds:
                lat = {p: (e2.get(p) or {}).get("latency", {}).get(k) or {} for p in PLATFORMS}
                cols = [
                    " / ".join(_fmt(lat[p].get(m), "", 2) for p in PLATFORMS)
                    for m in ("p50_ms", "p95_ms", "max_ms")
                ]
                lines.append(f"| {k} | " + " | ".join(cols) + " |")
            lines.append("")
        kinds = sorted({k for v in e2.values() for k in v["flatout"]})
        if kinds:
            lines += ["| flat-out TCP | Gb/s | host cores | VM cores |", "|---|---|---|---|"]
            for k in kinds:
                fo = {p: (e2.get(p) or {}).get("flatout", {}).get(k) or {} for p in PLATFORMS}
                cols = [
                    " / ".join(_fmt(_get(fo[p], m, "mean"), "", nd) for p in PLATFORMS)
                    for m, nd in (("gbps", 2), ("host_cores", 2), ("vm_cores", 2))
                ]
                lines.append(f"| {k} | " + " | ".join(cols) + " |")
            lines.append("")
        pats = sorted({k for v in e2.values() for k in v["ladder"]})
        if pats:
            lines += [
                "| load ladder | flows | highest rate passed (per flow) | total offered there, Mb/s | "
                "peak delivered, Mb/s |",
                "|---|---|---|---|---|",
            ]
            for k in pats:
                lad = {p: (e2.get(p) or {}).get("ladder", {}).get(k) or {} for p in PLATFORMS}
                flows = next((v.get("flows") for v in lad.values() if v.get("flows")), None)
                lines.append(
                    f"| {k} | {flows} | "
                    + " / ".join(lad[p].get("max_rate") or "none" for p in PLATFORMS)
                    + " | "
                    + " / ".join(
                        _fmt((lad[p].get("max_offered_bps") or 0) / 1e6 or None, "", 0)
                        for p in PLATFORMS
                    )
                    + " | "
                    + " / ".join(
                        _fmt((lad[p].get("peak_delivered_bps") or 0) / 1e6 or None, "", 0)
                        for p in PLATFORMS
                    )
                    + " |"
                )
            lines.append("")
        common = s.get("e2_common") or {}
        if common:
            lines += [
                "| CPU at equal load | rate per flow | host cores per 100 Mb/s | VM cores per 100 Mb/s | "
                "RTT p95 ms |",
                "|---|---|---|---|---|",
            ]
            for k, row in common.items():
                cols = [
                    " / ".join(_fmt((row.get(p) or {}).get(m), "", nd) for p in PLATFORMS)
                    for m, nd in (
                        ("host_cores_per_100m", 3),
                        ("vm_cores_per_100m", 3),
                        ("rtt_p95_ms", 2),
                    )
                ]
                lines.append(f"| {k} | {row['rate']} | " + " | ".join(cols) + " |")
            lines.append("")
    bad = {
        p: {n: st for n, st in steps.items() if st not in ("ok", None)}
        for p, steps in s["steps"].items()
    }
    if any(bad.values()):
        lines += ["## Steps not ok", ""]
        for p, steps in bad.items():
            for n, st in sorted(steps.items()):
                lines.append(f"- {p} {n}: {st}")
        lines.append("")
    return "\n".join(lines)
