#!/usr/bin/env python3
"""Run a benchmark suite on this host, start to finish: one command per host.

A suite (``benchmarks/suites/<name>.json``) lists specs (``benchmarks/specs/``)
in order. An item may run several times (``runs``, with ``seeds``), take the
images an earlier image census found usable here (``pool_from``), and start a
climb near the previous run's ceiling (``start_from_previous``)::

    ./bench.sh full --host m4-dd16           # from the repository root
    ./bench.sh list                           # the suites
    python3 backend/scripts/bench_suite.py run random --host linux-box \\
        --restart-cmd "sudo -n systemctl restart docker"

Before the first benchmark it checks that the git tree is clean, brings the
backend up in bench mode at this commit (with the host label and commit it
records), checks that nothing is deployed and builds every image the suite
needs. It keeps the machine awake, restarts Docker before every benchmark (so
what the previous one left behind doesn't count against the next; Docker
Desktop: ``docker desktop restart``, elsewhere ``--restart-cmd``) and records
the host at rest. Everything lands in
``backend/benchmark-results/<host>/<date>-<suite>/``: ``manifest.json`` (what
ran and where the suite stands), ``run.log``, a folder per run (the spec as
submitted, the report, the export, benchmark.json) and ``summary.md``.
``--resume`` picks a stopped suite up where it left off: finished runs are
kept, a benchmark still running is followed rather than restarted.

Ctrl-C once: the running benchmark finishes its step, is saved, and the suite
stops; twice: cancel it now. Stdlib only (it imports ``bench.py`` next to it);
Python 3.11+.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import math
import os
import platform
import shlex
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BENCHMARKS = ROOT / "backend" / "benchmarks"
RESULTS = ROOT / "backend" / "benchmark-results"
COMPOSE = ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.bench.yml"]
WAIT_DOWN = ["<wait until Docker is down>"]
POOLS = ("hosts", "switches", "routers")


class SuiteError(Exception):
    """A suite that can't run (a bad file, a host that isn't ready…)."""


# ── suites (pure) ─────────────────────────────────────────────────────


def suite_file(name: str) -> Path:
    path = Path(name)
    if path.suffix == ".json" or path.is_file():
        return path
    return BENCHMARKS / "suites" / f"{name}.json"


def load_suite(name: str, specs_root: Path = BENCHMARKS / "specs") -> dict[str, Any]:
    """The suite with each item's spec loaded (``_spec``) and checked: unique
    ids, existing specs, ``seeds`` for every run, ``pool_from`` naming an
    earlier census, ``start_from_previous`` on a climb. ``_sha`` fingerprints
    the suite and its specs as they are now."""
    path = suite_file(name)
    if not path.is_file():
        raise SuiteError(f"No suite {name!r} ({path})")
    raw = path.read_text()
    try:
        suite = json.loads(raw)
    except ValueError as exc:
        raise SuiteError(f"{path}: {exc}") from None
    suite.setdefault("name", path.stem)
    suite.setdefault("restart_docker", True)
    suite.setdefault("rest_wait_s", 60)
    items = suite.get("items") or []
    if not items:
        raise SuiteError(f"Suite {suite['name']!r} has no items")
    digest = hashlib.sha256(raw.encode())
    seen: dict[str, dict[str, Any]] = {}
    for item in items:
        iid = str(item.get("id") or "")
        if not iid or iid in seen:
            raise SuiteError(f"Suite items need unique ids ({iid!r})")
        # A spec path is relative to the specs folder, or absolute (a suite of
        # your own specs kept elsewhere).
        spec_path = specs_root / str(item.get("spec") or "")
        if not spec_path.is_file():
            raise SuiteError(f"Item {iid!r}: no spec {spec_path}")
        text = spec_path.read_text()
        digest.update(text.encode())
        item["_spec"] = json.loads(text)
        runs = int(item.get("runs") or 1)
        if runs < 1:
            raise SuiteError(f"Item {iid!r}: runs must be at least 1")
        if item.get("seeds") is not None and len(item["seeds"]) != runs:
            raise SuiteError(f"Item {iid!r}: give one seed per run ({runs})")
        if item.get("pool_from"):
            source = seen.get(item["pool_from"])
            if source is None or "census" not in source["_spec"]:
                raise SuiteError(f"Item {iid!r}: pool_from must name an earlier census item")
            if not (item["_spec"].get("topology") or {}).get("generate", {}).get("random"):
                raise SuiteError(f"Item {iid!r}: pool_from needs a spec with random pools")
        if item.get("limits") is not None:
            if "matrix" not in item["_spec"] or int(item.get("runs") or 1) != 1:
                raise SuiteError(f"Item {iid!r}: limits needs a matrix spec and one run")
        frac = item.get("start_from_previous")
        if frac is not None:
            if not 0 < float(frac) <= 1:
                raise SuiteError(f"Item {iid!r}: start_from_previous must be in (0, 1]")
            if not item["_spec"].get("adaptive"):
                raise SuiteError(f"Item {iid!r}: start_from_previous needs an adaptive spec")
        seen[iid] = item
    suite["_sha"] = digest.hexdigest()
    return suite


def deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    """``over`` on top of ``base``: dicts merge, anything else (lists too) replaces."""
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def plan_runs(suite: dict[str, Any], only: set[str] | None = None) -> list[dict[str, Any]]:
    """Every run of the suite, in order (an item with ``runs`` makes several),
    as manifest entries. ``only``: just these item ids (numbering is kept)."""
    out = []
    n = 0
    for item in suite["items"]:
        runs = int(item.get("runs") or 1)
        seeds = item.get("seeds") or [None] * runs
        for k in range(1, runs + 1):
            n += 1
            key = item["id"] if runs == 1 else f"{item['id']}-run{k}"
            seed = seeds[k - 1] if seeds[k - 1] is not None else (k if runs > 1 else None)
            if only and item["id"] not in only:
                continue
            out.append(
                {
                    "key": key,
                    "item": item["id"],
                    "run": k,
                    "runs": runs,
                    "seed": seed,
                    "dir": f"{n:02d}-{key}",
                    "status": "pending",
                    **({"kind": "limits"} if item.get("limits") is not None else {}),
                }
            )
    return out


def next_start(previous_ceiling: int, fraction: float, unit: int) -> int:
    """A climb's start from the previous run's ceiling (in multiples of ``unit``)."""
    unit = max(1, int(unit))
    return max(unit, math.floor(previous_ceiling * fraction / unit) * unit)


def apply_pool(
    spec: dict[str, Any], census: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    """The spec with its random pools cut to what the census found usable on
    this host (images it didn't test are kept), and what was left out."""
    usable = {(c["type"], c["image"]) for c in census if c.get("usable")}
    tested = {(c["type"], c["image"]) for c in census}
    out = copy.deepcopy(spec)
    pools = out["topology"]["generate"]["random"]
    excluded = []
    for name in POOLS:
        if not pools.get(name):
            continue
        kept_entries = []
        for entry in pools[name]:
            images = [
                i
                for i in entry["images"]
                if (entry["type"], i) in usable or (entry["type"], i) not in tested
            ]
            excluded += [f"{entry['type']} · {i}" for i in entry["images"] if i not in images]
            if images:
                kept_entries.append({**entry, "images": images})
        if not kept_entries:
            raise SuiteError(f"The census left nothing usable in the {name} pool")
        pools[name] = kept_entries
    return out, list(dict.fromkeys(excluded))


def build_spec(
    item: dict[str, Any],
    run: dict[str, Any],
    host: str,
    *,
    previous_ceiling: int | None = None,
    census: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The spec a run submits (overrides, label, seed, start, pool) and notes
    on what changed."""
    spec = deep_merge(item["_spec"], item.get("overrides") or {})
    notes: dict[str, Any] = {}
    spec["label"] = f"{host} · {item['id']}" + (f" run {run['run']}" if run["runs"] > 1 else "")
    gen = (spec.get("topology") or {}).get("generate")
    if run.get("seed") is not None and gen is not None:
        gen["seed"] = run["seed"]
        notes["seed"] = run["seed"]
    frac = item.get("start_from_previous")
    if frac and previous_ceiling and run["run"] > 1:
        adaptive = spec["adaptive"]
        adaptive["start"] = next_start(
            previous_ceiling, float(frac), adaptive.get("min_step") or 25
        )
        notes["start"] = adaptive["start"]
    if item.get("pool_from"):
        if census is None:
            raise SuiteError(f"{run['key']}: the census {item['pool_from']!r} has no result")
        spec, excluded = apply_pool(spec, census)
        notes["excluded"] = excluded
    return spec, notes


def ceiling_row(result: dict[str, Any]) -> dict[str, Any] | None:
    """The first passing row at the result's ceiling."""
    top = result.get("ceiling")
    return next(
        (r for r in result.get("rows") or [] if r["outcome"] == "ok" and r["scale"] == top),
        None,
    )


def spread(xs: list[float]) -> dict[str, float | None]:
    """Mean, sample std, min and max."""
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0, "mean": None, "std": None, "min": None, "max": None}
    m = sum(xs) / len(xs)
    std = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else 0.0
    return {"n": len(xs), "mean": m, "std": std, "min": min(xs), "max": max(xs)}


def aggregate_random(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Several climbs of one random mix: each run's ceiling row (hosts, nodes,
    peak memory, memory and deploy time per node, the share of each type and
    type · image), then their spread across runs. Runs without a ceiling are
    listed apart."""
    per, without = [], []
    for r in runs:
        row = ceiling_row(r.get("result") or {})
        if row is None:
            without.append(r["key"])
            continue
        comp = row.get("composition") or {}
        total = sum(comp.values()) or 1
        by_type: dict[str, float] = {}
        for kind, n in comp.items():
            t = kind.split(" · ")[0]
            by_type[t] = by_type.get(t, 0) + n / total
        nodes = row.get("nodes")
        per.append(
            {
                "key": r["key"],
                "seed": r.get("seed"),
                "ceiling": row["scale"],
                "nodes": nodes,
                "mem_pct": row.get("hold_mem_pct_max"),
                "mem_per_node": row.get("marginal_mem_per_node"),
                "deploy_s_per_node": row["deploy_s"] / nodes
                if row.get("deploy_s") and nodes
                else None,
                "kinds": {k: n / total for k, n in comp.items()},
                "types": by_type,
            }
        )
    across = {
        key: spread([p[key] for p in per])
        for key in ("ceiling", "nodes", "mem_pct", "mem_per_node", "deploy_s_per_node")
    }

    def shares(field: str) -> dict[str, dict[str, float | None]]:
        keys = sorted({k for p in per for k in p[field]})
        return {k: spread([p[field].get(k, 0.0) for p in per]) for k in keys}

    return {
        "runs": per,
        "without_ceiling": without,
        "across": across,
        "type_shares": shares("types"),
        "kind_shares": shares("kinds"),
    }


# ── traffic limits (pure) ─────────────────────────────────────────────
#
# A limits item searches, for every cell of a traffic matrix, the most hosts
# at which the cell's traffic still gets through ("comfortable") and the
# fewest at which it doesn't ("fails"), ``step`` apart. Each size is one
# matrix benchmark running only the cells that want it, so cells with similar
# limits share deployments. A cell starts near its estimate (from a cost
# model: Docker's cores per Mb/s, measured once), grows while it passes,
# halves the gap once it fails, and confirms its comfortable size once more.

LIMIT_DEFAULTS: dict[str, Any] = {
    "step": 50,  # the precision: last pass and first failure this far apart (hosts)
    "growth": 0.25,  # while a cell passes, grow by this share (at least a step)
    "start_fraction": 0.8,  # start a cell at this share of its estimate
    "max_hosts": 1000,
    "cpu_budget": 0.7,  # share of the host's CPUs Docker may use before traffic degrades
    "mem_budget": 0.85,  # share of memory the nodes and the traffic tool may use
    "base_mem": 1.0e9,  # memory in use with nothing deployed
    "cost": {},  # {pattern: {protocol: [cores, cores per 100 Mb/s]}}
    "flows_per_host": {},  # {pattern: flows each host sends}
    "mem_per_host": {},  # {pattern: bytes a host costs, its flows' iperf3 processes included}
}
TRAFFIC_REASONS = ("traffic_short", "traffic_loss", "traffic_none", "traffic_failed")
_RATE = {"K": 1e3, "M": 1e6, "G": 1e9}


def rate_bps(raw: str) -> float:
    raw = str(raw).strip()
    return float(raw.rstrip("KMGkmg")) * _RATE.get(raw[-1].upper(), 1.0)


def _short(name: str, value: Any) -> str:  # as the backend names cells
    if name == "burst_interval_ms":
        return f"{value}ms"
    if name == "length":
        return f"{value}B"
    if name == "parallel":
        return f"P{value}"
    return str(value)


def matrix_cell_ids(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    """The matrix's cells as the backend makes them (domain/benchmark.matrix_cells)."""
    axes = dict(matrix.get("axes") or {})
    patterns = [str(x) for x in axes.pop("pattern", None) or [p["id"] for p in matrix["patterns"]]]
    cells: list[dict[str, Any]] = [{"pattern": pid} for pid in patterns]
    for name, values in axes.items():
        cells = [{**c, name: v} for c in cells for v in values]
    for c in cells:
        c["id"] = "·".join(_short(k, v) for k, v in c.items())
    return cells


def _grid(x: float, step: int) -> int:
    return max(step, int(round(x / step)) * step)


def estimate_limit(cell: dict[str, Any], cfg: dict[str, Any], ncpu: float, mem_total: float) -> int:
    """Where the cell should stop coping (only a starting point): Docker's CPU
    for its traffic reaching the budget, or memory running out, whichever
    comes first."""
    pattern = cell["pattern"]
    a, b = (cfg["cost"].get(pattern) or {}).get(cell.get("protocol", "tcp"), [0.0, 0.0])
    per_host = rate_bps(cell["bitrate"]) / 1e6 * cfg["flows_per_host"].get(pattern, 1)  # Mb/s
    traffic = math.inf
    if b > 0 and per_host > 0:
        traffic = max(0.0, cfg["cpu_budget"] * ncpu - a) / (b / 100) / per_host
    memory = math.inf
    if cfg["mem_per_host"].get(pattern):
        memory = (cfg["mem_budget"] * mem_total - cfg["base_mem"]) / cfg["mem_per_host"][pattern]
    return int(max(cfg["step"], min(traffic, memory, cfg["max_hosts"])))


def cell_bracket(state: dict[str, Any]) -> tuple[int | None, int | None]:
    """(largest size passed below the first failure, smallest size failed).
    A size that both passed and failed counts as failed (not reliable)."""
    fails = {int(s) for s in state["fail"]}
    hi = min(fails) if fails else None
    passed = [int(s) for s in state["pass"] if int(s) not in fails and (hi is None or int(s) < hi)]
    return (max(passed) if passed else None), hi


def next_probe(state: dict[str, Any], cfg: dict[str, Any]) -> int | None:
    """The size a cell wants next, or None when its limit is found."""
    step, top = int(cfg["step"]), int(cfg["max_hosts"])
    lo, hi = cell_bracket(state)
    passes = state["pass"]
    if lo is None and hi is None:
        return min(top, _grid(state["estimate"] * cfg["start_fraction"], step))
    if hi is None:  # passed so far: grow, or confirm at the largest size
        if lo >= top:
            return lo if passes.get(str(lo), 0) < 2 else None
        return min(top, lo + max(step, _grid(lo * cfg["growth"], step)))
    if lo is None:  # failed so far: shrink
        if hi <= step:
            return None  # fails at the smallest size
        return max(step, min(hi - step, _grid(hi * (1 - cfg["growth"]), step)))
    if hi - lo > step:
        return min(max(_grid((lo + hi) / 2, step), lo + step), hi - step)
    return lo if passes.get(str(lo), 0) < 2 else None  # confirm the comfortable size


def plan_round(states: dict[str, dict[str, Any]], cfg: dict[str, Any]) -> dict[int, list[str]]:
    """The sizes the unfinished cells want next, each with its cells."""
    plan: dict[int, list[str]] = {}
    for cid, state in states.items():
        size = next_probe(state, cfg)
        if size is not None:
            plan.setdefault(size, []).append(cid)
    return dict(sorted(plan.items()))


def record_probe(
    states: dict[str, dict[str, Any]], size: int, wanted: list[str], result: dict[str, Any]
) -> None:
    """A size's matrix result into its cells' states: a pass, a failure (its
    reason), or, for a cell the run never reached (a stop criterion ended it
    first), nothing: it asks for the size again, once."""
    rows = result.get("rows") or []
    ran = {r["case"]: r for r in rows if r.get("cell")}
    deploy = next((r for r in rows if not r.get("cell")), None)
    key = str(size)
    for cid in wanted:
        state, row = states[cid], ran.get(cid)
        if row is None:
            if deploy is not None and deploy["outcome"] != "ok":
                state["fail"][key] = deploy.get("reason") or deploy["outcome"]
            else:
                state["unrun"][key] = state["unrun"].get(key, 0) + 1
                if state["unrun"][key] >= 2:
                    state["fail"][key] = "not_run"
        elif row["outcome"] == "ok":
            state["pass"][key] = state["pass"].get(key, 0) + 1
        else:
            state["fail"][key] = row.get("reason") or row["outcome"]


def limit_result(cid: str, state: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    lo, hi = cell_bracket(state)
    reason = state["fail"].get(str(hi)) if hi is not None else None
    return {
        "id": cid,
        "cell": state["cell"],
        "estimate": state["estimate"],
        "comfortable": lo,
        "fails_at": hi,
        "reason": reason,
        "bound": None if hi is None else ("traffic" if reason in TRAFFIC_REASONS else "host"),
        "confirmed": lo is not None and state["pass"].get(str(lo), 0) >= 2,
        "done": next_probe(state, cfg) is None,
        "probes": sum(state["pass"].values()) + len(state["fail"]),
    }


def limits_markdown(item: str, results: list[dict[str, Any]], cfg: dict[str, Any]) -> list[str]:
    """Per scenario (pattern · protocol), a rate × interval grid of
    "comfortable / fails"."""
    lines = [
        "",
        f"## Traffic limits: `{item}`",
        "",
        "Hosts each cell comfortably supports / the size where it first fell below the "
        f"threshold ({cfg['step']} hosts apart, the comfortable size passed twice). "
        "`mem` marks a host limit (memory, disk…) rather than traffic; `≥ N`: it never "
        "degraded up to N.",
    ]
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in results:
        groups.setdefault((r["cell"]["pattern"], r["cell"].get("protocol", "?")), []).append(r)
    for (pattern, proto), rs in groups.items():
        rates = list(dict.fromkeys(r["cell"].get("bitrate") for r in rs))
        intervals = list(dict.fromkeys(r["cell"].get("burst_interval_ms") for r in rs))
        at = {(r["cell"].get("bitrate"), r["cell"].get("burst_interval_ms")): r for r in rs}
        lines += [
            "",
            f"**{pattern} · {proto}**",
            "",
            "| rate \\ interval | " + " | ".join(f"{i} ms" for i in intervals) + " |",
            "|---|" + "---:|" * len(intervals),
        ]
        for rate in rates:
            cells = []
            for i in intervals:
                r = at.get((rate, i))
                if r is None:
                    cells.append("–")
                elif r["fails_at"] is None:
                    cells.append(f"≥ {r['comfortable']}" if r["comfortable"] else "?")
                else:
                    text = f"{r['comfortable'] or '<' + str(r['fails_at'])} / {r['fails_at']}"
                    cells.append(
                        text
                        + (" mem" if r["bound"] == "host" else "")
                        + ("" if r["done"] else " …")
                    )
            lines.append(f"| {rate} | " + " | ".join(cells) + " |")
    return lines


def _num(x: float | None, digits: int = 1) -> str:
    return "–" if x is None else f"{x:.{digits}f}"


def _pm(s: dict[str, Any], scale: float = 1, digits: int = 1) -> str:
    if s["mean"] is None:
        return "–"
    return (
        f"{s['mean'] / scale:.{digits}f} ± {s['std'] / scale:.{digits}f} "
        f"({s['min'] / scale:.{digits}f}–{s['max'] / scale:.{digits}f})"
    )


def outcome_text(result: dict[str, Any] | None) -> str:
    result = result or {}
    if result.get("census") is not None:
        usable = sum(1 for c in result["census"] if c.get("usable"))
        return f"{usable} of {len(result['census'])} cases usable"
    if result.get("matrix") is not None:
        ok = sum(1 for c in result["matrix"] if c.get("outcome") == "ok")
        return f"{ok} of {len(result['matrix'])} cells passed"
    text = f"ceiling {result.get('ceiling') or '–'} hosts"
    if result.get("limit"):
        text += f" ({result['limit']})"
    return text


def summary_markdown(
    manifest: dict[str, Any],
    aggregates: dict[str, dict[str, Any]],
    limits: dict[str, tuple[list[dict[str, Any]], dict[str, Any]]] | None = None,
) -> str:
    """The suite on one page: what ran, how each run ended, and the random
    climbs folded together."""
    git = manifest.get("git") or {}
    lines = [
        f"# Benchmark suite `{manifest['suite']}` on `{manifest['host']}`",
        "",
        f"- **Suite:** {manifest.get('description') or ''} (sha `{(manifest.get('suite_sha') or '')[:12]}`)",
        f"- **AE3GIS:** `{(git.get('commit') or '?')[:12]}`{' (modified)' if git.get('dirty') else ''}",
        f"- **Docker restart before each benchmark:** {manifest.get('restart') or 'no'}",
        *(
            [
                "- **Kernel (set after every restart):** "
                + ", ".join(f"`{k}={v}`" for k, v in manifest["sysctls"].items())
            ]
            if manifest.get("sysctls")
            else []
        ),
        f"- **When:** {(manifest.get('started_at') or '')[:19]} → "
        f"{(manifest.get('ended_at') or 'still running')[:19]} UTC",
    ]
    if manifest.get("platform") == "Linux" and manifest.get("restart"):
        lines.append(
            "- **Note:** on Linux a Docker restart does not remove the tap devices Kathará's "
            "VDE plugin leaves behind; compare the resting memory column."
        )
    pre = manifest.get("prebuild") or {}
    if pre.get("failed") or pre.get("unavailable"):
        lines.append(
            "- **Images not built:** "
            + ", ".join(
                f"`{r}` ({why})"
                for r, why in {**pre.get("unavailable", {}), **pre.get("failed", {})}.items()
            )
        )
    lines += [
        "",
        "| # | Run | Status | Outcome | Memory used at rest | Report |",
        "|---|---|---|---|---:|---|",
    ]
    for r in manifest["runs"]:
        rest = r.get("rest") or {}
        used = (
            f"{(rest['mem_total'] - rest['mem_available']) / 1e9:.2f} of {rest['mem_total'] / 1e9:.1f} GB"
            if rest.get("mem_total") and rest.get("mem_available") is not None
            else "–"
        )
        report = f"[report]({r['dir']}/report.md)" if r.get("benchmark_id") else "–"
        extra = ""
        if r.get("notes", {}).get("excluded"):
            extra = f" · pool without {len(r['notes']['excluded'])} image(s)"
        if r.get("error"):
            extra += f" · {r['error']}"
        lines.append(
            f"| {r['dir'][:2]} | `{r['key']}` | {r['status']} | {r.get('outcome') or '–'}{extra} "
            f"| {used} | {report} |"
        )
    for item, agg in aggregates.items():
        lines += [
            "",
            f"## Random climbs: `{item}` ({len(agg['runs'])} with a ceiling"
            + (
                f", {len(agg['without_ceiling'])} without: {', '.join(agg['without_ceiling'])}"
                if agg["without_ceiling"]
                else ""
            )
            + ")",
            "",
            "| Run | Seed | Ceiling hosts | Nodes | Peak memory % | MB / node | Deploy s / node |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for p in agg["runs"]:
            lines.append(
                f"| `{p['key']}` | {p['seed']} | {p['ceiling']} | {p['nodes']} | {_num(p['mem_pct'])} "
                f"| {_num(None if p['mem_per_node'] is None else p['mem_per_node'] / 1e6)} "
                f"| {_num(p['deploy_s_per_node'], 3)} |"
            )
        a = agg["across"]
        lines += [
            "",
            "Across runs (mean ± std, min–max):",
            "",
            f"- **Ceiling:** {_pm(a['ceiling'], digits=0)} hosts, {_pm(a['nodes'], digits=0)} nodes",
            f"- **Peak memory:** {_pm(a['mem_pct'])} %",
            f"- **Memory per node:** {_pm(a['mem_per_node'], 1e6)} MB",
            f"- **Deploy per node:** {_pm(a['deploy_s_per_node'], digits=3)} s",
            "",
            "Share of nodes per type at the ceiling (mean ± std over runs):",
            "",
            "| Type | Share |",
            "|---|---:|",
        ]
        for t, s in sorted(agg["type_shares"].items(), key=lambda kv: -(kv[1]["mean"] or 0)):
            lines.append(f"| {t} | {_pm(s, 0.01)} % |")
    for item, (results, cfg) in (limits or {}).items():
        lines += limits_markdown(item, results, cfg)
    return "\n".join(lines) + "\n"


# ── the host (side effects) ───────────────────────────────────────────


class Log:
    """Print, and keep a copy in ``run.log``."""

    def __init__(self, path: Path | None) -> None:
        self.path = path

    def __call__(self, text: str = "") -> None:
        print(text, flush=True)
        if self.path is not None:
            with self.path.open("a") as f:
                f.write(text + "\n")

    def stamp(self, text: str) -> None:
        self(f"=== {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC · {text}")


def _run(argv: list[str], **kw: Any) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=kw.pop("cwd", ROOT), **kw)


def git_state() -> dict[str, Any]:
    try:
        commit = _run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        status = _run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return {"commit": "", "dirty": False}
    return {"commit": commit, "dirty": bool(status.strip())}


def docker_ok() -> bool:
    try:
        return _run(["docker", "info"], capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def has_desktop_cli() -> bool:
    try:
        return (
            _run(["docker", "desktop", "version"], capture_output=True, timeout=30).returncode == 0
        )
    except (OSError, subprocess.TimeoutExpired):
        return False


def restart_plan(system: str, cmd: str | None, desktop_cli: bool) -> list[list[str]] | None:
    """How to restart Docker here (commands in turn), or None when there is
    no safe default (Linux: give ``--restart-cmd``, it needs root)."""
    if cmd:
        return [shlex.split(cmd)]
    if desktop_cli and system in ("Darwin", "Windows"):
        return [["docker", "desktop", "restart"]]
    if system == "Darwin":
        return [["osascript", "-e", 'quit app "Docker"'], WAIT_DOWN, ["open", "-a", "Docker"]]
    return None


def restart_docker(plan: list[list[str]], log: Log, timeout: float = 900) -> None:
    log("  restarting Docker: " + " → ".join(" ".join(s) for s in plan))
    for step in plan:
        if step == WAIT_DOWN:
            deadline = time.monotonic() + 120
            while docker_ok() and time.monotonic() < deadline:
                time.sleep(3)
            continue
        _run(step, check=True, timeout=timeout)
    deadline = time.monotonic() + timeout
    while not docker_ok():
        if time.monotonic() > deadline:
            raise SuiteError("Docker did not come back after the restart")
        time.sleep(5)


# A suite's ``sysctls`` are set in Docker's kernel (on Docker Desktop: the VM's,
# reset whenever Docker restarts, so they are set again after every restart;
# on Linux: the host's own, until it reboots) from a one-shot privileged
# container on the host network. E.g. the neighbour (ARP) table: 1024 entries
# for all nodes together by default, which under traffic cuts off every host
# past ~250 (mesh) or ~500 (clients -> servers).
SYSCTL_IMAGE = "alpine:3.22"


def sysctl_argv(sysctls: dict[str, Any]) -> list[str]:
    """The docker command that sets ``sysctls`` and prints them back."""
    names = " ".join(shlex.quote(k) for k in sysctls)
    sets = " ".join(shlex.quote(f"{k}={v}") for k, v in sysctls.items())
    return [
        "docker",
        "run",
        "--rm",
        "--privileged",
        "--net=host",
        SYSCTL_IMAGE,
        "sh",
        "-c",
        f"sysctl -q -w {sets} && sysctl {names}",
    ]


def parse_sysctls(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        if " = " in line:
            k, v = line.split(" = ", 1)
            out[k.strip()] = v.strip()
    return out


def set_sysctls(sysctls: dict[str, Any]) -> dict[str, str]:
    """Set them in Docker's kernel; what the kernel now reports."""
    done = _run(sysctl_argv(sysctls), capture_output=True, text=True, timeout=300)
    if done.returncode != 0:
        raise SuiteError(f"Could not set {', '.join(sysctls)}: {done.stderr.strip()[:300]}")
    got = parse_sysctls(done.stdout)
    wrong = {k: v for k, v in sysctls.items() if got.get(k) != str(v)}
    if wrong:
        raise SuiteError(f"The kernel kept other values for {', '.join(wrong)}: {got}")
    return got


def neigh_overflows() -> int | None:
    """How many "neighbour table overflow" messages Docker's kernel logged
    (since it booted: on Docker Desktop, since the last restart)."""
    try:
        done = _run(
            ["docker", "run", "--rm", "--privileged", SYSCTL_IMAGE, "dmesg"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return done.stdout.count("neighbour table overflow")


def keep_awake_cmd(system: str, pid: int) -> list[str] | None:
    if system == "Darwin":
        return ["caffeinate", "-dimsu", "-w", str(pid)]
    if system == "Linux" and shutil.which("systemd-inhibit"):
        return [
            "systemd-inhibit",
            "--what=sleep:idle",
            "--who=ae3gis-bench",
            "--why=benchmark suite",
            "--mode=block",
            "sleep",
            "infinity",
        ]
    return None


@contextlib.contextmanager
def keep_awake(log: Log):
    """No idle or system sleep while the suite runs (a closed lid still sleeps)."""
    system = platform.system()
    proc = None
    cmd = keep_awake_cmd(system, os.getpid())
    if cmd:
        with contextlib.suppress(OSError):
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif system == "Windows":
        import ctypes

        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)  # type: ignore[attr-defined]
    if system == "Darwin":
        with contextlib.suppress(OSError):
            batt = _run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
            if "Battery Power" in batt:
                log("  warning: on battery; plug in (macOS sleeps on battery anyway)")
    try:
        yield
    finally:
        if proc is not None:
            proc.terminate()


def compose_up(env: dict[str, str], *, recreate: bool) -> None:
    """The backend in bench mode: built and recreated at the start of a suite
    (this commit's code and labels); after a Docker restart only started."""
    extra = ["--build", "--force-recreate"] if recreate else []
    _run([*COMPOSE, "up", "-d", *extra, "backend"], check=True, env={**os.environ, **env})


def wait_healthy(api: bench.Api, timeout: float = 600, sleep=time.sleep) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        health = api.ping()
        if health and health.get("status") == "ok":
            return health
        if time.monotonic() > deadline:
            raise SuiteError(f"The backend at {api.base} did not answer")
        sleep(3)


def needed_images(spec: dict[str, Any], catalog: dict[str, Any]) -> set[str]:
    """Every image a spec may deploy (the catalog resolves defaults)."""
    types = catalog.get("types") or {}

    def default(t: str | None) -> str | None:
        return (types.get(t) or {}).get("defaultImage") if t else None

    if spec.get("census"):
        cases = spec["census"].get("cases") or [
            {"type": t, "image": i}
            for t, ts in types.items()
            for i in ts.get("images") or []
            if (catalog.get("images", {}).get(i) or {}).get("stability") != "hidden"
        ]
        return {c["image"] for c in cases} | {
            default("router"),
            default("switch"),
            default("workstation"),
        } - {None}
    g = (spec.get("topology") or {}).get("generate") or {}
    refs = {default(g.get("router_type", "router")), default(g.get("switch_type", "switch"))}
    refs |= {
        default(g.get("host_type", "workstation")),
        default(g.get("server_type", "workstation")),
    }
    refs.add(g.get("core_image") or default(g.get("core_type")))
    for mix in ("host_mix", "server_mix", "switch_mix"):
        refs |= {e.get("image") or default(e["type"]) for e in g.get(mix) or []}
    for name in POOLS:
        refs |= {i for e in (g.get("random") or {}).get(name) or [] for i in e["images"]}
    return {r for r in refs if r}


# ── the runner ────────────────────────────────────────────────────────


class Runner:
    """One suite on one host: preflight, then every run in turn, with the
    manifest saved after each change."""

    def __init__(
        self,
        suite: dict[str, Any],
        api: bench.Api,
        out_dir: Path,
        *,
        host: str,
        log: Log,
        restart: Callable[[], None] | None = None,
        tune: Callable[[dict[str, Any]], dict[str, str]] | None = None,
        kernel_log: Callable[[], int | None] | None = None,
        restart_text: str | None = None,
        compose: Callable[[bool], None] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        poll: float = 15.0,
        retries: int = 1,
        retry_failed: bool = False,
        stop_on_failure: bool = False,
        allow_dirty: bool = False,
        prebuild: bool = True,
        only: set[str] | None = None,
    ) -> None:
        self.suite, self.api, self.out_dir, self.host, self.log = suite, api, out_dir, host, log
        self.restart, self.compose, self.sleep, self.poll = restart, compose, sleep, poll
        self.tune, self.kernel_log = tune, kernel_log
        self.retries, self.retry_failed, self.stop_on_failure = (
            retries,
            retry_failed,
            stop_on_failure,
        )
        self.allow_dirty, self.do_prebuild = allow_dirty, prebuild
        self.items = {i["id"]: i for i in suite["items"]}
        self.stopping = False
        path = out_dir / "manifest.json"
        if path.is_file():
            self.manifest = json.loads(path.read_text())
            if self.manifest.get("suite") != suite["name"] or self.manifest.get("host") != host:
                raise SuiteError(f"{out_dir} holds another suite or host")
            known = {r["key"] for r in self.manifest["runs"]}
            self.manifest["runs"] += [r for r in plan_runs(suite, only) if r["key"] not in known]
        else:
            self.manifest = {
                "suite": suite["name"],
                "description": suite.get("description") or "",
                "suite_sha": suite["_sha"],
                "host": host,
                "platform": platform.system(),
                "base_url": api.base,
                "restart": restart_text,
                "started_at": datetime.now(UTC).isoformat(),
                "ended_at": None,
                "runs": plan_runs(suite, only),
            }
        if only:
            self.manifest["only"] = sorted(only)

    # ── bookkeeping ──

    def save(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.out_dir / "manifest.json.tmp"
        tmp.write_text(json.dumps(self.manifest, indent=2, default=str))
        tmp.replace(self.out_dir / "manifest.json")

    def result_of(self, run: dict[str, Any]) -> dict[str, Any] | None:
        path = self.out_dir / run["dir"] / "benchmark.json"
        if path.is_file():
            return json.loads(path.read_text()).get("result")
        return None

    def latest(self, item_id: str, before: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """The result of an item's last finished run (before ``before``)."""
        found = None
        for r in self.manifest["runs"]:
            if r is before:
                break
            if r["item"] == item_id and r["status"] == "done":
                found = self.result_of(r) or found
        return found

    def summarize(self) -> Path:
        aggregates = {}
        for item_id, item in self.items.items():
            if (item["_spec"].get("topology") or {}).get("generate", {}).get("random") and int(
                item.get("runs") or 1
            ) > 1:
                runs = [
                    {"key": r["key"], "seed": r.get("seed"), "result": self.result_of(r)}
                    for r in self.manifest["runs"]
                    if r["item"] == item_id and r["status"] == "done"
                ]
                if runs:
                    aggregates[item_id] = aggregate_random(runs)
                    (self.out_dir / f"random-{item_id}.json").write_text(
                        json.dumps(aggregates[item_id], indent=2)
                    )
        limits = {}
        for r in self.manifest["runs"]:
            if r.get("kind") == "limits" and r.get("cells"):
                cfg = self.limit_config(r["item"])
                results = [limit_result(cid, st, cfg) for cid, st in r["cells"].items()]
                limits[r["item"]] = (results, cfg)
                (self.out_dir / f"limits-{r['item']}.json").write_text(
                    json.dumps(results, indent=2)
                )
        path = self.out_dir / "summary.md"
        path.write_text(summary_markdown(self.manifest, aggregates, limits))
        return path

    def limit_config(self, item_id: str) -> dict[str, Any]:
        return {**LIMIT_DEFAULTS, **(self.items[item_id].get("limits") or {})}

    # ── preflight ──

    def preflight(self) -> None:
        log = self.log
        git = git_state()
        self.manifest["git"] = git
        if git["dirty"] and not self.allow_dirty:
            raise SuiteError(
                "The git tree has uncommitted changes; commit them or pass --allow-dirty"
            )
        live = None
        if self.api.ping():
            live = next((b for b in self.api.call("GET", "/benchmarks?limit=5") if b["live"]), None)
        if self.compose is not None and live is None:
            log("  bringing the backend up in bench mode (docker compose)")
            self.compose(True)
        health = wait_healthy(self.api, sleep=self.sleep)
        if health.get("engine") != "kathara":
            msg = f"the backend's engine is {health.get('engine')!r}, not kathara"
            if self.compose is not None:
                raise SuiteError(msg)
            log(f"  warning: {msg}")
        env = self.api.call("GET", "/system/environment")
        ae3gis = env.get("ae3gis") or {}
        problems = []
        if ae3gis.get("mode") != "bench":
            problems.append(
                f"mode is {ae3gis.get('mode')!r}, not bench (a reload would kill a benchmark)"
            )
        if git["commit"] and not str(git["commit"]).startswith(
            str(ae3gis.get("git_commit") or "-")
        ):
            problems.append(
                f"it runs commit {str(ae3gis.get('git_commit'))[:12]!r}, not {git['commit'][:12]}"
            )
        if (env.get("host") or {}).get("label") != self.host:
            problems.append(
                f"its host label is {(env.get('host') or {}).get('label')!r}, not {self.host!r}"
            )
        for p in problems:
            if self.compose is not None and live is None:
                raise SuiteError(f"The backend {p}")
            log(f"  warning: the backend {p}")
        if live is not None:
            log(
                f"  benchmark {live['id'][:8]} ({live['label']}) is running: following it, not redeploying"
            )
        else:
            self.check_labs()
        self.apply_sysctls()
        if self.do_prebuild:
            self.prebuild()
        self.save()

    def apply_sysctls(self) -> dict[str, str] | None:
        """Set the suite's sysctls in Docker's kernel (again after every
        Docker restart); what the kernel reports, also in the manifest."""
        wanted = self.suite.get("sysctls")
        if not wanted or self.tune is None:
            return None
        got = self.tune(wanted)
        self.manifest["sysctls"] = got
        self.log("  kernel: " + ", ".join(f"{k}={v}" for k, v in got.items()))
        return got

    def check_labs(self) -> None:
        labs = [lab for lab in self.api.call("GET", "/system/labs")["labs"] if lab["running"]]
        if labs:
            names = ", ".join(lab.get("topology_name") or lab["lab_hash"][:8] for lab in labs)
            raise SuiteError(f"Labs are deployed ({names}); destroy them before benchmarking")

    def prebuild(self) -> None:
        """Build (or rebuild when stale) every image the suite's runs need,
        once, up front; images that can't build here are recorded."""
        catalog = self.api.call("GET", "/catalog")
        needed: set[str] = set((catalog.get("tools") or {}).values())
        for r in self.manifest["runs"]:
            needed |= needed_images(self.items[r["item"]]["_spec"], catalog)
        report = {i["ref"]: i for i in self.api.call("GET", "/images")["images"]}
        unavailable = {
            ref: report[ref]["reason"]
            for ref in needed
            if report.get(ref, {}).get("status") == "unavailable"
        }
        build = sorted(
            ref
            for ref in needed
            if report.get(ref, {}).get("kind") == "build"
            and report[ref]["status"] in ("missing", "failed", "stale")
        )
        failed: dict[str, str] = {}
        if build:
            self.log(f"  building {len(build)} image(s): {', '.join(build)}")
            jobs = self.api.call("POST", "/images/builds", {"refs": build})
            for job in jobs:
                while job["status"] in ("queued", "running"):
                    self.sleep(min(self.poll, 10))
                    job = self.api.call("GET", f"/jobs/{job['id']}")
                ref = (job.get("params") or {}).get("ref") or job.get("subject")
                if job["status"] != "succeeded":
                    failed[str(ref)] = job.get("error") or job["status"]
        for ref, why in {**unavailable, **failed}.items():
            self.log(f"  not available here: {ref} ({why})")
        self.manifest["prebuild"] = {
            "built": [b for b in build if b not in failed],
            "failed": failed,
            "unavailable": unavailable,
        }

    # ── runs ──

    def rest(self) -> dict[str, Any]:
        env = self.api.call("GET", "/system/environment")
        docker = (env.get("engine") or {}).get("docker") or {}
        host = env.get("host") or {}
        return {
            "at": datetime.now(UTC).isoformat(),
            "mem_total": docker.get("mem_total"),
            "mem_available": host.get("mem_available"),
            "loadavg": host.get("loadavg"),
        }

    def fresh_host(self) -> dict[str, Any]:
        """Restart Docker (if asked), wait for the backend and an empty host,
        let it settle, and record it at rest."""
        if self.restart is not None:
            self.restart()
            self.apply_sysctls()
            if self.compose is not None:
                self.compose(False)
            wait_healthy(self.api, sleep=self.sleep)
            self.check_labs()
            wait = float(self.suite.get("rest_wait_s") or 0)
            if wait:
                self.log(f"  letting the host settle ({wait:g}s)")
                self.sleep(wait)
        return self.rest()

    def finish(self, run: dict[str, Any], b: dict[str, Any]) -> None:
        folder = self.out_dir / run["dir"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "benchmark.json").write_text(json.dumps(b, indent=2, default=str))
        try:
            bench.save(self.api, b["id"], folder, "report")
            (folder / "report.zip").replace(folder / "export.zip")
        except (bench.ApiError, OSError) as exc:
            run["error"] = f"could not save the report: {exc}"
        result = b.get("result") or {}
        run.update(
            status={"succeeded": "done", "cancelled": "cancelled"}.get(b["status"], "failed"),
            ended_at=datetime.now(UTC).isoformat(),
            outcome=outcome_text(result),
            ceiling=result.get("ceiling"),
            stopped_by=result.get("stopped_by"),
            limit=result.get("limit"),
        )
        if b["status"] == "failed":
            run["error"] = b["job"].get("error") or "failed"
        self.log(f"  {run['key']}: {bench.outcome_line(b)}")
        self.save()

    def follow(self, run: dict[str, Any], bid: str) -> dict[str, Any]:
        """Follow a benchmark to its end, through a backend that restarts."""
        with self.interruptible(bid):
            while True:
                try:
                    return bench.follow(self.api, bid, self.poll, out=self.log)
                except OSError as exc:  # urllib's errors too: the backend went away
                    self.log(f"  lost the backend ({exc}); waiting for it")
                    wait_healthy(self.api, timeout=1800, sleep=self.sleep)

    @contextlib.contextmanager
    def interruptible(self, bid: str):
        hits = 0

        def on_sigint(_sig, _frame) -> None:
            nonlocal hits
            hits += 1
            self.stopping = True
            if hits == 1:
                self.log(
                    "\nstopping after the current step, then the suite (Ctrl-C again: cancel now)…"
                )
                self.api.call("POST", f"/jobs/{bid}/stop")
            else:
                self.log("\ncancelling…")
                self.api.call("POST", f"/jobs/{bid}/cancel")

        try:
            previous = signal.signal(signal.SIGINT, on_sigint)
        except ValueError:  # not the main thread (tests)
            previous = None
        try:
            yield
        finally:
            if previous is not None:
                signal.signal(signal.SIGINT, previous)

    def start(self, run: dict[str, Any]) -> dict[str, Any]:
        item = self.items[run["item"]]
        previous = None
        if item.get("start_from_previous") and run["run"] > 1:
            previous = (self.latest(item["id"], before=run) or {}).get("ceiling")
        census = None
        if item.get("pool_from"):
            census = (self.latest(item["pool_from"]) or {}).get("census")
        spec, notes = build_spec(item, run, self.host, previous_ceiling=previous, census=census)
        folder = self.out_dir / run["dir"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "spec.json").write_text(json.dumps(spec, indent=2))
        b = self.api.call("POST", "/benchmarks", spec)
        run.update(
            status="running",
            benchmark_id=b["id"],
            started_at=datetime.now(UTC).isoformat(),
            notes=notes,
            error=None,
        )
        self.save()
        self.log(f"  benchmark {b['id']}: {spec['label']} · {bench.describe(b)}")
        for k, v in notes.items():
            self.log(f"  {k}: {', '.join(v) if isinstance(v, list) else v}")
        return b

    def run_one(self, run: dict[str, Any]) -> None:
        self.log.stamp(f"{run['dir']} ({run['status']})")
        if run.get("kind") == "limits":
            self.run_limits(run)
            return
        if run["status"] == "running" and run.get("benchmark_id"):
            b = self.api.call("GET", f"/benchmarks/{run['benchmark_id']}")
            if b["live"]:
                self.finish(run, self.follow(run, b["id"]))
                return
            if b["status"] != "failed":
                self.finish(run, b)
                return
        for attempt in range(1 + max(0, self.retries)):
            if attempt:
                self.log(f"  retrying {run['key']} (attempt {attempt + 1})")
            run["rest"] = self.fresh_host()
            run["attempts"] = attempt + 1
            b = self.start(run)
            self.finish(run, self.follow(run, b["id"]))
            if run["status"] != "failed" or self.stopping:
                return

    # ── traffic limits ──

    def run_limits(self, run: dict[str, Any]) -> None:
        """Search every cell's limit, a round of sizes at a time (see
        ``next_probe``); each size is a matrix benchmark of the cells that
        want it, after a Docker restart."""
        item = self.items[run["item"]]
        cfg = self.limit_config(item["id"])
        template = deep_merge(item["_spec"], item.get("overrides") or {})
        states: dict[str, dict[str, Any]] = run.setdefault("cells", {})
        if not states:
            docker = (self.api.call("GET", "/system/environment").get("engine") or {}).get(
                "docker"
            ) or {}
            ncpu, mem_total = docker.get("ncpu") or 4, docker.get("mem_total") or 8e9
            for c in matrix_cell_ids(template["matrix"]):
                cell = {k: v for k, v in c.items() if k != "id"}
                states[c["id"]] = {
                    "cell": cell,
                    "estimate": estimate_limit(cell, cfg, ncpu, mem_total),
                    "pass": {},
                    "fail": {},
                    "unrun": {},
                }
            run["host"] = {"ncpu": ncpu, "mem_total": mem_total}
        run.update(status="running", error=None)
        run.setdefault("started_at", datetime.now(UTC).isoformat())
        probes: list[dict[str, Any]] = run.setdefault("probes", [])
        self.save()
        for probe in probes:  # one left running or unrecorded by an interrupted runner
            if probe["status"] in ("running", "done") and not probe.get("recorded"):
                self.run_probe(run, probe, template, states, resume=True)
        while not self.stopping:
            plan = plan_round(states, cfg)
            if not plan:
                break
            rnd = 1 + max((pr["round"] for pr in probes), default=0)
            self.log(
                f"  round {rnd}: "
                + ", ".join(f"{size} hosts × {len(ids)} cells" for size, ids in plan.items())
            )
            for size, ids in plan.items():
                if self.stopping:
                    break
                probe = {
                    "key": f"{run['key']} · {size} hosts · round {rnd}",
                    "round": rnd,
                    "size": size,
                    "cells": ids,
                    "dir": f"{run['dir']}/r{rnd:02d}-{size}",
                    "status": "pending",
                }
                probes.append(probe)
                self.save()
                self.run_probe(run, probe, template, states)
        results = [limit_result(cid, st, cfg) for cid, st in states.items()]
        done = sum(1 for r in results if r["done"])
        run.update(
            status="done" if done == len(results) else "running",
            ended_at=datetime.now(UTC).isoformat(),
            outcome=f"{done} of {len(results)} cells' limits found, in {len(probes)} probes",
        )
        self.save()

    def run_probe(
        self,
        run: dict[str, Any],
        probe: dict[str, Any],
        template: dict[str, Any],
        states: dict[str, dict[str, Any]],
        *,
        resume: bool = False,
    ) -> None:
        b = None
        if resume and probe.get("benchmark_id"):
            b = self.api.call("GET", f"/benchmarks/{probe['benchmark_id']}")
            if b["live"]:
                b = self.follow(probe, b["id"])
            if b["status"] in ("failed", "cancelled"):
                # Interrupted (e.g. cancelled to pause the search): nothing to
                # record; its cells ask for the size again.
                probe.update(status=b["status"], recorded=True)
                self.save()
                return
            self.finish(probe, b)
        attempt = 0
        while b is None or (probe["status"] == "failed" and attempt <= self.retries):
            if self.stopping:
                return
            attempt += 1
            probe["rest"] = self.fresh_host()
            spec = deep_merge(
                template, {"scale": [probe["size"]], "matrix": {"cells": probe["cells"]}}
            )
            spec["label"] = (
                f"{self.host} · {run['item']} · {probe['size']} hosts · round {probe['round']}"
            )
            folder = self.out_dir / probe["dir"]
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "spec.json").write_text(json.dumps(spec, indent=2))
            b = self.api.call("POST", "/benchmarks", spec)
            probe.update(status="running", benchmark_id=b["id"], attempts=attempt, error=None)
            self.save()
            self.log(f"  benchmark {b['id']}: {spec['label']} · {len(probe['cells'])} cells")
            b = self.follow(probe, b["id"])
            self.finish(probe, b)
        if probe["status"] != "done":
            if self.stopping:  # Ctrl-C: --resume asks for the size again
                return
            raise SuiteError(f"{probe['key']}: {probe.get('error') or probe['status']}")
        if self.kernel_log is not None and self.suite.get("sysctls"):
            probe["neigh_overflows"] = self.kernel_log()
            if probe["neigh_overflows"]:
                self.log(f"  warning: {probe['neigh_overflows']} neighbour table overflows")
        record_probe(states, probe["size"], probe["cells"], b.get("result") or {})
        probe["recorded"] = True
        passed = sum(1 for cid in probe["cells"] if str(probe["size"]) in states[cid]["pass"])
        self.log(f"  {probe['size']} hosts: {passed} of {len(probe['cells'])} cells passed")
        self.save()

    def run(self) -> int:
        """Every pending run; the exit code (0: all done)."""
        self.save()
        for run in self.manifest["runs"]:
            if self.stopping:
                break
            if run["status"] in ("done", "skipped"):
                continue
            if run["status"] in ("failed", "cancelled") and not self.retry_failed:
                continue
            try:
                self.run_one(run)
            except (SuiteError, bench.ApiError) as exc:
                run.update(status="failed", error=str(exc))
                self.save()
                self.log(f"  {run['key']} failed: {exc}")
            if run["status"] == "cancelled":
                self.stopping = True
            if run["status"] == "failed" and self.stop_on_failure:
                break
        self.manifest["ended_at"] = datetime.now(UTC).isoformat()
        self.save()
        summary = self.summarize()
        self.log.stamp(f"suite {'stopped' if self.stopping else 'finished'}: {summary}")
        return 0 if all(r["status"] == "done" for r in self.manifest["runs"]) else 1


# ── CLI ───────────────────────────────────────────────────────────────


def out_dir_for(host: str, suite: str, resume: str | None, root: Path) -> Path:
    base = root / host
    if resume and resume != "latest":
        return Path(resume)
    if resume == "latest":
        found = sorted(p for p in base.glob(f"*-{suite}*") if (p / "manifest.json").is_file())
        if not found:
            raise SuiteError(f"Nothing to resume for {suite!r} on {host!r} in {base}")
        return found[-1]
    stem = f"{datetime.now(UTC).strftime('%Y-%m-%d')}-{suite}"
    path, n = base / stem, 2
    while path.exists():
        path, n = base / f"{stem}-{n}", n + 1
    return path


def cmd_list() -> int:
    for path in sorted((BENCHMARKS / "suites").glob("*.json")):
        suite = load_suite(str(path))
        runs = plan_runs(suite)
        print(f"{suite['name']:<12} {len(runs):>2} run(s)  {suite.get('description') or ''}")
        for r in runs:
            print(f"{'':12}   {r['dir']}  {_spec_text(suite, r)}")
    return 0


def _spec_text(suite: dict[str, Any], run: dict[str, Any]) -> str:
    item = next(i for i in suite["items"] if i["id"] == run["item"])
    return item["spec"] + (f" (seed {run['seed']})" if run.get("seed") is not None else "")


def cmd_run(args: argparse.Namespace) -> int:
    suite = load_suite(args.suite)
    host = args.host.strip()
    if not host or "/" in host:
        raise SuiteError("--host names this machine (no slashes), e.g. m4-dd16")
    system = platform.system()
    plan = None
    if args.restart != "none" and suite.get("restart_docker", True):
        plan = restart_plan(
            system, args.restart_cmd, args.restart_cmd is None and has_desktop_cli()
        )
        if plan is None:
            raise SuiteError(
                'No way to restart Docker here: pass --restart-cmd (e.g. "sudo -n systemctl restart '
                'docker") or --restart none'
            )
    out_dir = out_dir_for(host, suite["name"], args.resume, Path(args.out_root))
    only = set(args.only.split(",")) if args.only else None
    if args.dry_run:
        print(f"suite {suite['name']} on {host} → {out_dir}")
        print(f"docker restart: {' → '.join(' '.join(s) for s in plan) if plan else 'no'}")
        for r in plan_runs(suite, only):
            item = next(i for i in suite["items"] if i["id"] == r["item"])
            extra = []
            if item.get("pool_from"):
                extra.append(f"pool from {item['pool_from']}")
            if item.get("start_from_previous") and r["run"] > 1:
                extra.append(f"start at {item['start_from_previous']} × the previous ceiling")
            if item.get("limits") is not None:
                cells = matrix_cell_ids(item["_spec"]["matrix"])
                step = {**LIMIT_DEFAULTS, **item["limits"]}["step"]
                extra.append(f"limit search over {len(cells)} cells, {step} hosts apart")
            print(
                f"  {r['dir']}  {_spec_text(suite, r)}"
                + (f"  [{'; '.join(extra)}]" if extra else "")
            )
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    log = Log(out_dir / "run.log")
    api = bench.Api(args.base_url, args.token)
    git = git_state()
    env = {
        "AE3GIS_HOST_LABEL": host,
        "AE3GIS_GIT_COMMIT": git["commit"],
        "AE3GIS_GIT_DIRTY": "true" if git["dirty"] else "false",
    }
    runner = Runner(
        suite,
        api,
        out_dir,
        host=host,
        log=log,
        restart=(lambda: restart_docker(plan, log)) if plan else None,
        tune=set_sysctls,
        kernel_log=neigh_overflows,
        restart_text=" → ".join(" ".join(s) for s in plan) if plan else None,
        compose=None if args.no_compose else (lambda recreate: compose_up(env, recreate=recreate)),
        poll=args.poll,
        retries=args.retries,
        retry_failed=args.retry_failed,
        stop_on_failure=args.stop_on_failure,
        allow_dirty=args.allow_dirty,
        prebuild=not args.no_prebuild,
        only=only,
    )
    log.stamp(f"suite {suite['name']} on {host} → {out_dir}")
    with keep_awake(log):
        runner.preflight()
        return runner.run()


def cmd_summarize(args: argparse.Namespace) -> int:
    out_dir = Path(args.dir)
    manifest = json.loads((out_dir / "manifest.json").read_text())
    suite = load_suite(manifest["suite"])
    runner = Runner(
        suite,
        bench.Api(manifest.get("base_url") or "http://localhost:8000", None),
        out_dir,
        host=manifest["host"],
        log=Log(None),
    )
    print(runner.summarize())
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="the suites and their runs")
    run = sub.add_parser("run", help="run a suite on this host")
    run.add_argument("suite", help="a suite name (benchmarks/suites/) or a suite file")
    run.add_argument(
        "--host", required=True, help="this machine's name in the results, e.g. m4-dd16"
    )
    run.add_argument("--base-url", default="http://localhost:8000")
    run.add_argument("--token")
    run.add_argument(
        "--resume",
        nargs="?",
        const="latest",
        help="continue a suite (default: the latest for this host)",
    )
    run.add_argument(
        "--retry-failed", action="store_true", help="with --resume: rerun failed runs too"
    )
    run.add_argument("--only", help="just these item ids, comma-separated")
    run.add_argument(
        "--restart",
        choices=("auto", "none"),
        default="auto",
        help="restart Docker before each benchmark",
    )
    run.add_argument(
        "--restart-cmd",
        help="how to restart Docker here (Linux: e.g. 'sudo -n systemctl restart docker')",
    )
    run.add_argument(
        "--no-compose", action="store_true", help="use the backend as it runs (no docker compose)"
    )
    run.add_argument(
        "--no-prebuild", action="store_true", help="don't build the suite's images up front"
    )
    run.add_argument(
        "--allow-dirty", action="store_true", help="run with uncommitted changes (recorded)"
    )
    run.add_argument("--stop-on-failure", action="store_true")
    run.add_argument(
        "--retries",
        type=int,
        default=1,
        help="reruns of a failed benchmark (after a Docker restart)",
    )
    run.add_argument("--dry-run", action="store_true", help="print what would run, then stop")
    run.add_argument("--poll", type=float, default=15.0, help="seconds between status checks")
    run.add_argument(
        "--out-root", default=str(RESULTS), help="where results go (a folder per host)"
    )
    summarize = sub.add_parser("summarize", help="rebuild a results folder's summary.md")
    summarize.add_argument("dir")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(line_buffering=True)
    try:
        if args.command == "list":
            return cmd_list()
        if args.command == "summarize":
            return cmd_summarize(args)
        return cmd_run(args)
    except SuiteError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except bench.ApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
