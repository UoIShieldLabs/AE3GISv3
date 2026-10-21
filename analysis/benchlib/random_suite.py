"""Idle capacity (the ``random`` suite): census and random-mix climbs."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .load import RandomSuite


def ceiling_stats(rs: RandomSuite) -> pd.Series:
    """Mean / std / min / max over every climb (all runs count)."""
    c = rs.climbs["ceiling"].dropna()
    return pd.Series(
        {"climbs": len(c), "mean": c.mean(), "std": c.std(), "min": c.min(), "max": c.max()}
    )


def climb_table(rs: RandomSuite) -> pd.DataFrame:
    cols = ["n", "seed", "ceiling", "nodes", "mem_pct", "mb_per_node", "deploy_s_per_node", "limit"]
    t = rs.climbs[cols + ["note"]].copy()
    t["limit"] = t["limit"].fillna("").str.slice(0, 70)
    return t.set_index("n").rename_axis("climb")


def stop_kind(limit: str | None) -> str:
    """What ended a climb, in one word."""
    s = (limit or "").lower()
    for word, kind in (
        ("memory", "memory"),
        ("deploy_failed", "deploy failed"),
        ("deploy_slow", "deploy slow"),
        ("destroy_failed", "teardown failed"),
        ("disk", "disk"),
    ):
        if word in s:
            return kind
    return "bracketed" if "between" in s else (s.split(" ")[0] or "–")


def census_table(rs: RandomSuite) -> pd.DataFrame:
    """Per type · image: usable or why not, and what one node costs."""
    c = rs.census
    if c.empty:
        return c
    cols = [
        "type",
        "image",
        "usable",
        "outcome",
        "reason",
        "host_mb_per_node",
        "cgroup_mb_per_node",
        "deploy_s",
        "ready_s",
        "disk_mb_per_node",
    ]
    t = c[[x for x in cols if x in c]].copy()
    return t.sort_values("host_mb_per_node", ascending=False, na_position="last").reset_index(
        drop=True
    )


def composition_cost(rs: RandomSuite) -> pd.DataFrame:
    """Per climb: its ceiling and the census-weighted memory one node of its
    mix costs (what drives the spread between climbs)."""
    if rs.composition.empty or rs.census.empty:
        return pd.DataFrame()
    cost = rs.census.set_index("case")["host_mb_per_node"]
    comp = rs.composition
    known = [c for c in comp.columns if c in cost.index]
    weights = comp[known]
    mix_mb = (weights * cost[known]).sum(axis=1) / weights.sum(axis=1)
    out = rs.climbs.set_index("run")[["n", "ceiling", "nodes", "mb_per_node", "note"]].join(
        mix_mb.rename("mix_mb_per_node")
    )
    return out


def drivers(rs: RandomSuite, top: int = 3) -> pd.DataFrame:
    """The images whose share of the mix at the ceiling moves the ceiling
    most (correlation over climbs; shares, since bigger climbs simply hold more
    of everything), with their per-node cost."""
    if rs.composition.empty:
        return pd.DataFrame()
    ceil = rs.climbs.set_index("run")["ceiling"]
    comp = rs.composition.loc[rs.composition.index.intersection(ceil.index)]
    share = comp.div(comp.sum(axis=1), axis=0)
    rows = []
    for case in share.columns:
        x = share[case]
        if x.std() == 0:
            continue
        rows.append(
            {
                "case": case,
                "corr_with_ceiling": float(np.corrcoef(x, ceil.loc[share.index])[0, 1]),
                "share_min_pct": round(100 * float(x.min()), 1),
                "share_max_pct": round(100 * float(x.max()), 1),
                "count_min": int(comp[case].min()),
                "count_max": int(comp[case].max()),
            }
        )
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    if not rs.census.empty:
        t = t.merge(rs.census[["case", "host_mb_per_node"]], on="case", how="left")
    return t.reindex(t["corr_with_ceiling"].abs().sort_values(ascending=False).index).head(top)


def type_shares(rs: RandomSuite) -> pd.DataFrame:
    t = rs.type_shares
    if t.empty:
        return t
    return (t[["mean", "std"]] * 100).sort_values("mean", ascending=False).round(1)


def image_memory(rs: RandomSuite) -> pd.Series:
    """Median container memory (MB) per image over every climb's ceiling, the
    image weighted by how many containers ran it."""
    im = rs.images
    if im.empty:
        return pd.Series(dtype=float)
    im = im[im["count"] > 0]
    return im.groupby("image").apply(
        lambda g: (g["container_mb"] * g["count"]).sum() / g["count"].sum(), include_groups=False
    )


STOP_NAMES = {
    "memory": "memory",
    "memory_pressure": "memory",
    "deploy_failed": "deploy failed",
    "deploy_slow": "deploy too slow",
    "destroy_failed": "teardown failed",
    "disk": "disk",
}


def climb_stops(rs: RandomSuite) -> pd.Series:
    """What ended each climb: the memory target, or the reason of the step
    that failed above its ceiling."""
    out = {}
    steps = rs.steps
    for c in rs.climbs.itertuples():
        lim = str(c.limit or "")
        reason = None
        if "memory peaked" in lim:
            reason = "memory"
        else:
            m = re.search(r"\(([a-z_]+)\)$", lim)
            if m:
                reason = m.group(1)
            else:
                f = steps[
                    (steps["run"] == c.run)
                    & (steps["outcome"] != "ok")
                    & (steps["scale"] > c.ceiling)
                ]
                if len(f):
                    reason = f.sort_values("scale").iloc[0]["reason"]
        out[c.run] = STOP_NAMES.get(reason, reason or "–")
    return pd.Series(out, name="stop")
