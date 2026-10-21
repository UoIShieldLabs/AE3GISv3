"""Read a host's committed benchmark results into tidy DataFrames.

Only what is in git: each suite folder's ``manifest.json``, every benchmark's
``benchmark.json`` (its per-step rows) and the suite aggregates. The raw
``export.zip`` files (time series) stay on each machine.

A traffic cell's limit is worked out with the runner's own ``limit_result``
(``backend/scripts/bench_suite.py``), so the grids match ``summary.md``.
"""

from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import pandas as pd

from .hosts import HOSTS, Host

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "backend" / "benchmark-results"
RATES = ["1M", "500K", "250K", "100K", "50K"]  # high to low
INTERVALS = [100, 250, 500, 1000, 2000]
SCENARIOS = [("cs", "tcp"), ("cs", "udp"), ("mesh", "tcp"), ("mesh", "udp")]
FLOWS_PER_HOST = {"cs": 1, "mesh": 2}
RATE_BPS = {"1M": 1e6, "500K": 5e5, "250K": 2.5e5, "100K": 1e5, "50K": 5e4}
MB = 1e6


@cache
def runner():
    """The suite runner module (stdlib only)."""
    sys.path.insert(0, str(ROOT / "backend" / "scripts"))
    return importlib.import_module("bench_suite")


@cache
def limits_config() -> dict[str, Any]:
    bs = runner()
    item = next(i for i in bs.load_suite("traffic")["items"] if i.get("limits"))
    return {**bs.LIMIT_DEFAULTS, **item["limits"]}


def _json(path: Path) -> Any:
    return json.loads(path.read_text())


def _suite_dir(host: str, suite: str) -> Path | None:
    dirs = sorted(d for d in (RESULTS / host).glob(f"*-{suite}") if d.is_dir())
    return dirs[-1] if dirs else None


@dataclass
class RandomSuite:
    dir: Path
    manifest: dict[str, Any]
    climbs: pd.DataFrame  # one row per climb
    steps: pd.DataFrame  # one row per climb step
    census: pd.DataFrame  # one row per type · image case
    composition: pd.DataFrame  # climb x type · image counts at its ceiling step
    images: pd.DataFrame  # per climb and image at its ceiling: containers, mean container MB
    type_shares: pd.DataFrame  # mean / std share of each type at the ceiling
    across: dict[str, Any]  # the suite's own mean / std / min / max per metric
    extra_dirs: list[str] = field(default_factory=list)  # folders not in the manifest


@dataclass
class TrafficSuite:
    dir: Path
    manifest: dict[str, Any]
    cells: pd.DataFrame  # one row per traffic cell: its limit as it stands
    rows: pd.DataFrame  # one row per cell run in every probe
    deploys: pd.DataFrame  # one row per probe deployment
    probes: pd.DataFrame  # one row per probe
    dropped: pd.DataFrame  # results a re-check or repair dropped


@dataclass
class HostData:
    host: Host
    random: RandomSuite | None
    traffic: TrafficSuite | None


# ── random (idle) ─────────────────────────────────────────────────────


def _climb_rows(dir_: Path, key: str) -> list[dict[str, Any]]:
    path = dir_ / "benchmark.json"
    if not path.exists():
        return []
    rows = (_json(path).get("result") or {}).get("rows") or []
    out = []
    for i, r in enumerate(rows):
        phases = r.get("deploy_phases") or {}
        out.append(
            {
                "run": key,
                "order": i,
                "scale": r.get("scale"),
                "nodes": r.get("nodes"),
                "outcome": r.get("outcome"),
                "reason": r.get("reason"),
                "deploy_s": r.get("deploy_s"),
                "deploy_engine_s": phases.get("deploy"),
                "verify_s": phases.get("verify"),
                "ready_s": r.get("ready_s"),
                "destroy_s": r.get("destroy_s"),
                "mem_pct": r.get("hold_mem_pct_max"),
                "mem_settle_gb": (r.get("mem_settle") or 0) / 1e9 or None,
                "marginal_mb_per_node": (r.get("marginal_mem_per_node") or 0) / MB or None,
                "docker_mb_per_node": (r.get("docker_mem_per_node") or 0) / MB or None,
                "node_mb_mean": (r.get("node_mem_mean") or 0) / MB or None,
                "cpu_pct": r.get("hold_cpu_mean"),
                "psi_mem_full": r.get("hold_psi_mem_full_max"),
                "disk_mb_per_node": (r.get("disk_per_node") or 0) / MB or None,
                "composition": r.get("composition") or {},
                "by_image": r.get("by_image") or {},
            }
        )
    return out


def load_random(host: str) -> RandomSuite | None:
    dir_ = _suite_dir(host, "random")
    if dir_ is None:
        return None
    manifest = _json(dir_ / "manifest.json")
    agg_path = next(dir_.glob("random-*.json"), None)
    agg = _json(agg_path) if agg_path else {"runs": [], "across": {}, "type_shares": {}}
    by_key = {r["key"]: r for r in agg.get("runs") or []}
    annotations = HOSTS[host].annotations
    climbs, steps, comp, images = [], [], {}, []
    census = pd.DataFrame()
    for run in manifest["runs"]:
        if run["key"] == "census":
            path = dir_ / run["dir"] / "benchmark.json"
            if path.exists():
                items = (_json(path).get("result") or {}).get("census") or []
                census = pd.DataFrame(items)
                for col, src in (
                    ("host_mb_per_node", "host_mem_per_node"),
                    ("cgroup_mb_per_node", "cgroup_mem_per_node"),
                    ("disk_mb_per_node", "disk_per_node"),
                ):
                    if src in census:
                        census[col] = census[src] / MB
            continue
        a = by_key.get(run["key"], {})
        climbs.append(
            {
                "run": run["key"],
                "n": run.get("run"),
                "seed": run.get("seed"),
                "status": run.get("status"),
                "ceiling": run.get("ceiling")
                if run.get("ceiling") is not None
                else a.get("ceiling"),
                "nodes": a.get("nodes"),
                "mem_pct": a.get("mem_pct"),
                "mb_per_node": (a.get("mem_per_node") or 0) / MB or None,
                "deploy_s_per_node": a.get("deploy_s_per_node"),
                "stopped_by": run.get("stopped_by"),
                "limit": run.get("limit"),
                "attempts": run.get("attempts"),
                "note": annotations.get(run["key"], ""),
            }
        )
        rows = _climb_rows(dir_ / run["dir"], run["key"])
        steps += rows
        ok = [r for r in rows if r["outcome"] == "ok" and r["scale"] == climbs[-1]["ceiling"]]
        if ok:
            comp[run["key"]] = ok[-1]["composition"]
            for image, v in ok[-1]["by_image"].items():
                images.append(
                    {
                        "run": run["key"],
                        "image": image,
                        "count": v.get("count"),
                        "container_mb": (v.get("mem_mean") or 0) / MB,
                    }
                )
    steps_df = pd.DataFrame(steps).drop(columns=["composition", "by_image"], errors="ignore")
    shares = pd.DataFrame(agg.get("type_shares") or {}).T
    listed = {r["dir"] for r in manifest["runs"]}
    extra = sorted(d.name for d in dir_.iterdir() if d.is_dir() and d.name not in listed)
    return RandomSuite(
        dir=dir_,
        manifest=manifest,
        climbs=pd.DataFrame(climbs),
        steps=steps_df,
        census=census,
        composition=pd.DataFrame(comp).T.fillna(0).astype(int) if comp else pd.DataFrame(),
        images=pd.DataFrame(images),
        type_shares=shares,
        across=agg.get("across") or {},
        extra_dirs=extra,
    )


# ── traffic ───────────────────────────────────────────────────────────


def _cell_fields(cid: str) -> dict[str, Any]:
    pattern, protocol, rate, interval = cid.split("·")
    return {
        "cell": cid,
        "pattern": pattern,
        "protocol": protocol,
        "scenario": f"{pattern}·{protocol}",
        "rate": rate,
        "interval_ms": int(interval.removesuffix("ms")),
    }


def _dropped(run: dict[str, Any]) -> pd.DataFrame:
    """What a re-check (``reopened``) or a repair (``repaired``) dropped."""
    out = []
    for d in (run.get("reopened") or {}).get("dropped") or []:
        out.append(
            {
                "cell": d["cell"],
                "size": d["size"],
                "round": d.get("round"),
                "dir": None,
                "why": d["what"],
                "by": "re-check",
            }
        )
    for d in (run.get("repaired") or {}).get("dropped") or []:
        probe_dir, cell, why = d[0], d[1], d[2]
        size = int(probe_dir.rsplit("-", 1)[1])
        out.append(
            {
                "cell": cell,
                "size": size,
                "round": None,
                "dir": probe_dir,
                "why": why,
                "by": "repair",
            }
        )
    return pd.DataFrame(out, columns=["cell", "size", "round", "dir", "why", "by"])


def load_traffic(host: str) -> TrafficSuite | None:
    dir_ = _suite_dir(host, "traffic")
    if dir_ is None:
        return None
    manifest = _json(dir_ / "manifest.json")
    run = next(r for r in manifest["runs"] if r.get("kind") == "limits")
    bs, cfg = runner(), limits_config()
    cells = []
    for cid, state in run["cells"].items():
        r = bs.limit_result(cid, state, cfg)
        cells.append(
            {
                **_cell_fields(cid),
                "estimate": r["estimate"],
                "comfortable": r["comfortable"],
                "fails_at": r["fails_at"],
                "reason": r["reason"],
                "bound": r["bound"],
                "confirmed": r["confirmed"],
                "done": r["done"],
                "probes": r["probes"],
            }
        )
    cells_df = pd.DataFrame(cells)
    flows = cells_df["pattern"].map(FLOWS_PER_HOST)
    cells_df["carried_mbps"] = (
        cells_df["comfortable"] * cells_df["rate"].map(RATE_BPS) * flows / 1e6
    )

    dropped = _dropped(run)
    drop_rc = {(d.cell, d.size, d.round) for d in dropped.itertuples() if d.by == "re-check"}
    drop_rp = {(d.dir, d.cell) for d in dropped.itertuples() if d.by == "repair"}
    rows, deploys, probes = [], [], []
    for p in run["probes"]:
        probes.append(
            {
                "round": p["round"],
                "size": p["size"],
                "cells": len(p.get("cells") or []),
                "status": p["status"],
                "ended_at": p.get("ended_at"),
                "outcome": p.get("outcome"),
                "neigh_overflows": p.get("neigh_overflows"),
            }
        )
        path = dir_ / p["dir"] / "benchmark.json"
        if p["status"] != "done" or not path.exists():
            continue
        for r in (_json(path).get("result") or {}).get("rows") or []:
            if not r.get("cell"):
                deploys.append(
                    {
                        "round": p["round"],
                        "size": p["size"],
                        "nodes": r.get("nodes"),
                        "outcome": r.get("outcome"),
                        "reason": r.get("reason"),
                        "deploy_s": r.get("deploy_s"),
                        "ready_s": r.get("ready_s"),
                        "destroy_s": r.get("destroy_s"),
                        "mem_settle_gb": (r.get("mem_settle") or 0) / 1e9 or None,
                        "docker_mb_per_node": (r.get("docker_mem_per_node") or 0) / MB or None,
                    }
                )
                continue
            case = r["case"]
            dropped_row = (case, p["size"], p["round"]) in drop_rc or (p["dir"], case) in drop_rp
            rows.append(
                {
                    **_cell_fields(case),
                    "round": p["round"],
                    "size": p["size"],
                    "outcome": r.get("outcome"),
                    "reason": r.get("reason"),
                    "detail": r.get("detail"),
                    "flows": r.get("flows"),
                    "offered_mbps": (r.get("offered_bps") or 0) / 1e6 or None,
                    "delivered_mbps": (r.get("delivered_bps") or 0) / 1e6 or None,
                    "delivered_ratio": r.get("delivered_ratio"),
                    "loss_pct": r.get("lost_percent"),
                    "rtt_p95_ms": r.get("rtt_ms_p95"),
                    "retransmits": r.get("retransmits"),
                    "flow_ratio_p05": r.get("flow_ratio_p05"),
                    "flow_ratio_min": r.get("flow_ratio_min"),
                    "flows_with_errors": r.get("flows_with_errors"),
                    "cpu_pct": r.get("hold_cpu_mean"),
                    "idle_cpu_pct": r.get("idle_cpu_mean"),
                    "lab_cores": (r.get("hold_docker_cpu_mean") or 0) / 100 or None,
                    "mem_pct": r.get("hold_mem_pct_max"),
                    "psi_mem_full": r.get("hold_psi_mem_full_max"),
                    "node_rx_mbps": (r.get("hold_node_rx_bps") or 0) / 1e6 or None,
                    "quiet_wait_s": r.get("quiet_wait_s"),
                    "startup_s": r.get("traffic_startup_s"),
                    "not_started": r.get("flows_not_started"),
                    "driver": "fixed" if "traffic_startup_s" in r else "old",
                    "dropped": dropped_row,
                }
            )
    rows_df = pd.DataFrame(rows)
    if not rows_df.empty:
        rows_df["cores_per_100mbps"] = rows_df["lab_cores"] / (rows_df["delivered_mbps"] / 100)
        rows_df["rx_per_delivered"] = rows_df["node_rx_mbps"] / rows_df["delivered_mbps"]
    return TrafficSuite(
        dir=dir_,
        manifest=manifest,
        cells=cells_df,
        rows=rows_df,
        deploys=pd.DataFrame(deploys),
        probes=pd.DataFrame(probes),
        dropped=dropped,
    )


def load(host: str) -> HostData:
    return HostData(host=HOSTS[host], random=load_random(host), traffic=load_traffic(host))


def load_all(order: list[str] | None = None) -> dict[str, HostData]:
    from .hosts import ORDER

    return {h: load(h) for h in (order or ORDER) if (RESULTS / h).is_dir()}
