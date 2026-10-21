"""Traffic limits (the ``traffic`` suite): grids, cost, failure reasons, data
quality."""

from __future__ import annotations

import pandas as pd

from .load import INTERVALS, RATES, SCENARIOS, TrafficSuite

SIZE_BINS = [(0, 250), (250, 450), (450, 650), (650, 850), (850, 1100)]
TRAFFIC_REASONS = ("traffic_short", "traffic_loss", "traffic_none", "traffic_failed")


def scenario_name(pattern: str, protocol: str) -> str:
    return f"{'clients → servers' if pattern == 'cs' else 'mesh'} · {protocol.upper()}"


def grid(cells: pd.DataFrame, scenario: str, value: str = "comfortable") -> pd.DataFrame:
    """A rate × interval table of ``value`` for one scenario (``cs·tcp``…)."""
    g = cells[cells["scenario"] == scenario].pivot(
        index="rate", columns="interval_ms", values=value
    )
    return g.reindex(index=RATES, columns=INTERVALS)


def label(r: pd.Series) -> str:
    """A cell as the runner's summary writes it: ``comfortable / fails``, with
    ``mem`` / ``tool`` for a host or tool limit, ``≥`` and ``…`` while open."""
    lo, hi = r["comfortable"], r["fails_at"]
    lo = None if pd.isna(lo) else int(lo)
    if pd.isna(hi):
        text = f"≥ {lo}" if lo else "?"
    else:
        text = f"{lo if lo else '<' + str(int(hi))} / {int(hi)}"
        text += {"host": " mem", "tool": " tool"}.get(r["bound"], "")
    return text + ("" if r["done"] else " …")


def label_grid(cells: pd.DataFrame, scenario: str) -> pd.DataFrame:
    c = cells[cells["scenario"] == scenario].copy()
    c["label"] = c.apply(label, axis=1)
    return c.pivot(index="rate", columns="interval_ms", values="label").reindex(
        index=RATES, columns=INTERVALS
    )


def kept(rows: pd.DataFrame) -> pd.DataFrame:
    """Rows that still count (not dropped by a re-check or a repair)."""
    return rows[~rows["dropped"]] if not rows.empty else rows


def at_limit(ts: TrafficSuite, which: str = "comfortable") -> pd.DataFrame:
    """Each cell's latest counted row at its comfortable size (a pass) or at
    the size it fails at (a failure)."""
    rows = kept(ts.rows)
    want_ok = which == "comfortable"
    out = []
    for c in ts.cells.itertuples():
        size = c.comfortable if want_ok else c.fails_at
        if pd.isna(size):
            continue
        r = rows[(rows["cell"] == c.cell) & (rows["size"] == size)]
        r = r[r["outcome"] == "ok"] if want_ok else r[r["outcome"] != "ok"]
        if len(r):
            out.append(r.sort_values("round").iloc[-1])
    return pd.DataFrame(out)


def size_bin(size: float) -> str:
    for a, b in SIZE_BINS:
        if a <= size < b:
            return f"{a}–{b}"
    return "?"


def cost_by_size(rows: pd.DataFrame, min_mbps: float = 20.0) -> pd.DataFrame:
    """Median lab CPU cores per 100 Mb/s delivered, per scenario and lab size,
    over passing counted rows (enough traffic to measure)."""
    r = kept(rows)
    r = r[(r["outcome"] == "ok") & (r["delivered_mbps"] > min_mbps) & r["lab_cores"].notna()]
    if r.empty:
        return pd.DataFrame()
    r = r.assign(bin=r["size"].map(size_bin))
    t = r.pivot_table(index="scenario", columns="bin", values="cores_per_100mbps", aggfunc="median")
    order = [f"{a}–{b}" for a, b in SIZE_BINS]
    return t.reindex(columns=[c for c in order if c in t.columns])


def cost_summary(rows: pd.DataFrame, max_size: int = 450, min_mbps: float = 20.0) -> pd.Series:
    """Median cores per 100 Mb/s per scenario over labs up to ``max_size``
    hosts, where every driver kept up (a like-for-like efficiency figure)."""
    r = kept(rows)
    r = r[
        (r["outcome"] == "ok")
        & (r["delivered_mbps"] > min_mbps)
        & r["lab_cores"].notna()
        & (r["size"] <= max_size)
    ]
    return r.groupby("scenario")["cores_per_100mbps"].median()


def reasons(cells: pd.DataFrame) -> pd.DataFrame:
    """What set each cell's limit, per scenario."""

    def kind(r: pd.Series) -> str:
        if pd.isna(r["fails_at"]):
            return "never failed (≥)"
        if r["bound"] == "traffic":
            return "loss" if r["reason"] == "traffic_loss" else "delivery"
        if r["bound"] == "tool":
            return "tool"
        return {
            "deploy_slow": "deploy too slow",
            "deploy_failed": "deploy failed",
            "not_run": "not reached",
        }.get(r["reason"], "memory" if "memory" in str(r["reason"]) else str(r["reason"]))

    c = cells.assign(kind=cells.apply(kind, axis=1))
    return (
        c.pivot_table(index="scenario", columns="kind", values="cell", aggfunc="count")
        .fillna(0)
        .astype(int)
    )


def interval_effect(cells: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """Comfortable hosts per rate (rows) across burst intervals (columns)."""
    return grid(cells, scenario)


def search_history(ts: TrafficSuite, scenario: str) -> pd.DataFrame:
    """Every counted probe of a scenario's cells: size, pass or fail, round."""
    r = kept(ts.rows)
    r = r[r["scenario"] == scenario]
    r = r[["cell", "rate", "interval_ms", "round", "size", "outcome"]]
    order = r["rate"].map({rate: i for i, rate in enumerate(RATES)})
    return r.assign(_o=order).sort_values(["_o", "interval_ms", "round"]).drop(columns="_o")


def quality_by_size(rows: pd.DataFrame, pattern: str = "mesh") -> pd.DataFrame:
    """Per driver and lab size: runs, the share where ≥5% of flows delivered
    nothing, the median full memory stalls and the median memory use."""
    r = rows[rows["pattern"] == pattern].copy()
    if r.empty:
        return pd.DataFrame()
    r["bin"] = r["size"].map(size_bin)
    r["dead"] = r["flow_ratio_p05"] == 0
    t = r.groupby(["driver", "bin"]).agg(
        runs=("cell", "size"),
        dead_flows_pct=("dead", "mean"),
        psi_mem_full_median=("psi_mem_full", "median"),
        mem_pct_median=("mem_pct", "median"),
    )
    t["dead_flows_pct"] *= 100
    order = [f"{a}–{b}" for a, b in SIZE_BINS]
    t = t.reindex([(d, b) for d in ("old", "fixed") for b in order if (d, b) in t.index])
    return t.round(1)


def overview(ts: TrafficSuite) -> pd.Series:
    run = next(r for r in ts.manifest["runs"] if r.get("kind") == "limits")
    rows = ts.rows
    return pd.Series(
        {
            "cells final": f"{int(ts.cells['done'].sum())} of {len(ts.cells)}",
            "probes (lab sizes measured)": len(ts.probes),
            "rounds": int(ts.probes["round"].max()) if len(ts.probes) else 0,
            "cell runs": len(rows),
            "cell runs by the fixed driver": int((rows["driver"] == "fixed").sum())
            if len(rows)
            else 0,
            "results dropped (re-check / repair)": len(ts.dropped),
            "re-check rules applied": ", ".join((run.get("reopened") or {}).get("rules") or [])
            or "–",
            "started": str(run.get("started_at", ""))[:16].replace("T", " "),
            "last update": str(
                max(
                    [str(x) for x in ts.probes["ended_at"].dropna()]
                    + [str(run.get("ended_at") or "")]
                )
            )[:16].replace("T", " "),
        }
    )


SCENARIO_ORDER = [f"{p}·{q}" for p, q in SCENARIOS]
