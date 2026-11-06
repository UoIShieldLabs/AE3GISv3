"""AE3GIS vs GNS3 (the platform comparison) → DataFrames for ``platforms.ipynb``.

Each host's latest ``<date>-compare/`` run is read through the runner's own
summarizer (``backend/scripts/compare_lib/summary.py``), so the notebook's
numbers are the ones in that run's ``summary.md``. Step files hold per-phase
metrics and a compact time series; there are no raw exports.
"""

from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass
from functools import cache, cached_property
from pathlib import Path
from typing import Any

import pandas as pd

from .load import RESULTS, ROOT

PLATFORMS = ("ae3gis", "gns3")
NAMES = {"ae3gis": "AE3GIS", "gns3": "GNS3"}
COLORS = {"ae3gis": "#1f77b4", "gns3": "#ff7f0e"}
GB = 2**30
MB = 2**20


@cache
def summary():
    """The runner's summarizer module (stdlib only)."""
    sys.path.insert(0, str(ROOT / "backend" / "scripts"))
    return importlib.import_module("compare_lib.summary")


def runs(quick: bool = False) -> dict[str, Path]:
    """{host: its latest comparison run}."""
    out = {}
    suffix = "-compare-quick" if quick else "-compare"
    for host in sorted(p for p in RESULTS.iterdir() if p.is_dir()):
        dirs = sorted(d for d in host.glob(f"*{suffix}") if (d / "manifest.json").exists())
        if dirs:
            out[host.name] = dirs[-1]
    return out


@dataclass
class Run:
    host: str
    dir: Path

    @cached_property
    def records(self) -> dict[str, dict[str, dict]]:
        return summary().load(self.dir)

    @cached_property
    def s(self) -> dict[str, Any]:
        return summary().summarize(self.dir)

    @cached_property
    def manifest(self) -> dict[str, Any]:
        return json.loads((self.dir / "manifest.json").read_text())

    # ── E0 ──

    @cached_property
    def e0(self) -> pd.DataFrame:
        rows = [
            {"platform": p, **{k: v for k, v in r.items() if k != "infra"}}
            for p, reps in self.s["e0"]["reps"].items()
            for r in reps
        ]
        return pd.DataFrame(rows)

    @cached_property
    def e0_infra(self) -> pd.DataFrame:
        """RSS of each platform process inside the VM, mean over reps."""
        rows = [
            {"platform": p, "process": k, "rss": v}
            for p, reps in self.s["e0"]["reps"].items()
            for r in reps
            for k, v in (r.get("infra") or {}).items()
        ]
        df = pd.DataFrame(rows)
        return df.groupby(["platform", "process"], as_index=False)["rss"].mean() if len(df) else df

    # ── E1 ──

    @cached_property
    def e1(self) -> pd.DataFrame:
        """One row per platform, size and rep (every status)."""
        sm = summary()
        rows = []
        for p, steps in self.records.items():
            for name, rec in steps.items():
                if name.startswith("e1-") and rec.get("size") is not None:
                    r = sm.e1_row(rec)
                    r.pop("timings", None)
                    r.pop("roles", None)
                    rows.append({"platform": p, **r})
        df = pd.DataFrame(rows)
        return df.sort_values(["platform", "size", "rep"]).reset_index(drop=True) if len(df) else df

    @cached_property
    def e1_ok(self) -> pd.DataFrame:
        return self.e1[self.e1["status"] == "ok"] if len(self.e1) else self.e1

    def e1_stat(self, metric: str) -> pd.DataFrame:
        """mean / min / max of a metric per platform and size (ok reps)."""
        g = self.e1_ok.groupby(["platform", "size"])[metric]
        return g.agg(["mean", "min", "max", "count"]).reset_index()

    @cached_property
    def roles(self) -> pd.DataFrame:
        """Containers' memory per node by role at hold (ok reps, mean)."""
        rows = [
            {"platform": p, "size": rec["size"], "role": role, **v}
            for p, steps in self.records.items()
            for name, rec in steps.items()
            if name.startswith("e1-") and rec.get("status") == "ok"
            for role, v in (rec.get("roles") or {}).items()
        ]
        df = pd.DataFrame(rows)
        if not len(df):
            return df
        return df.groupby(["platform", "size", "role"], as_index=False)[
            ["nodes", "mem_per_node"]
        ].mean()

    def ratio(self, metric: str) -> pd.Series:
        """GNS3 ÷ AE3GIS of a metric's mean, per size both finished."""
        m = self.e1_ok.groupby(["size", "platform"])[metric].mean().unstack("platform")
        if not set(PLATFORMS) <= set(m.columns):
            return pd.Series(dtype=float)
        return (m["gns3"] / m["ae3gis"]).dropna()

    def series(self, platform: str, name: str) -> pd.DataFrame:
        """One step's time series: seconds from its first sweep, VM cores,
        VM memory used, the lab's memory and the VM's host footprint."""
        rec = self.records.get(platform, {}).get(name) or {}
        df = pd.DataFrame(
            rec.get("series") or [], columns=["rt", "vm_cores", "vm_mem", "lab_mem", "footprint"]
        )
        if len(df):
            df["s"] = df["rt"] - df["rt"].iloc[0]
        return df

    def phases(self, platform: str, name: str) -> dict[str, tuple[float, float]]:
        """Phase windows in seconds from the step's first sweep."""
        rec = self.records.get(platform, {}).get(name) or {}
        ser = rec.get("series") or []
        if not ser:
            return {}
        t0 = ser[0][0]
        return {k: (v["t"][0] - t0, v["t"][1] - t0) for k, v in (rec.get("phases") or {}).items()}

    # ── E2 ──

    @cached_property
    def latency(self) -> pd.DataFrame:
        rows = [
            {"platform": p, **v, "kind": k}
            for p, e in self.s["e2"].items()
            for k, v in e["latency"].items()
        ]
        return pd.DataFrame(rows)

    @cached_property
    def flatout(self) -> pd.DataFrame:
        rows = []
        for p, steps in self.records.items():
            ref = (steps.get("e2") or {}).get("reference") or {}
            for s in (steps.get("e2") or {}).get("flatout") or []:
                cpu = summary()._step_cpu(s, ref)
                rows.append(
                    {
                        "platform": p,
                        "kind": s.get("kind"),
                        "trial": s.get("trial"),
                        "gbps": (s.get("delivered_bps") or 0) / 1e9,
                        "retransmits": s.get("retransmits"),
                        "rtt_p95_ms": s.get("rtt_p95_ms"),
                        **cpu,
                    }
                )
        return pd.DataFrame(rows)

    @cached_property
    def ladder(self) -> pd.DataFrame:
        """Every ladder run, with CPU over the lab's idle reference."""
        rows = []
        for p, e in self.s["e2"].items():
            for key, lad in e["ladder"].items():
                for s in lad["steps"]:
                    rows.append(
                        {
                            "platform": p,
                            "scenario": key,
                            "rate": s["rate"],
                            "rate_bps": summary()._rate(s["rate"]),
                            "repeat": s["repeat"],
                            "passed": s["passed"],
                            "flows": s.get("flows"),
                            "offered_mbps": (s.get("offered_bps") or 0) / 1e6,
                            "delivered_mbps": (s.get("delivered_bps") or 0) / 1e6,
                            "delivered_ratio": s.get("delivered_ratio"),
                            "loss": s.get("loss"),
                            "jitter_ms": s.get("jitter_ms"),
                            "rtt_p95_ms": s.get("rtt_p95_ms"),
                            "retransmits": s.get("retransmits"),
                            "host_cores": s.get("host_cores"),
                            "vm_cores": s.get("vm_cores"),
                            "host_cores_per_100m": s.get("host_cores_per_100m"),
                            "vm_cores_per_100m": s.get("vm_cores_per_100m"),
                        }
                    )
        return pd.DataFrame(rows)

    @cached_property
    def ladder_best(self) -> pd.DataFrame:
        rows = [
            {
                "platform": p,
                "scenario": k,
                **{x: v[x] for x in v if x not in ("steps", "rates_run")},
            }
            for p, e in self.s["e2"].items()
            for k, v in e["ladder"].items()
        ]
        return pd.DataFrame(rows)


def load(quick: bool = False, paths: dict[str, str] | None = None) -> dict[str, Run]:
    """Every host's latest run, or ``paths`` ({host: run dir}) when given."""
    found = {h: Path(d) for h, d in paths.items()} if paths else runs(quick)
    return {h: Run(h, d) for h, d in found.items()}


def sanity(run: Run) -> list[str]:
    """What makes a run unfit to compare: both platforms, the same lab files,
    the same images, every planned step present."""
    out = []
    recs = run.records
    for p in PLATFORMS:
        if p not in recs:
            out.append(f"{p}: no steps")
    shas: dict[str, set[str]] = {}
    imgs: dict[str, dict] = {}
    for p, steps in recs.items():
        for rec in steps.values():
            if rec.get("lab_sha256"):
                shas.setdefault(rec["lab"], set()).add(rec["lab_sha256"])
            lab_imgs = ((rec.get("vm") or {}).get("images") or {}).get("lab")
            if lab_imgs:
                imgs.setdefault(p, {}).update(lab_imgs)
    want = run.manifest.get("labs") or {}
    for lab, s in shas.items():
        if len(s) > 1 or (lab in want and want[lab] not in s):
            out.append(f"{lab}: lab files differ ({sorted(s)})")
    if len(imgs) == 2 and imgs["ae3gis"] != imgs["gns3"]:
        out.append("the platforms ran different lab images")
    plan = run.manifest.get("plan") or {}
    # a resume can add experiments (e.g. E3) with a newer plan
    for r in run.manifest.get("resumes") or []:
        plan = {**plan, **(r.get("plan") or {})}
    e1 = plan.get("e1") or {}
    for p in PLATFORMS:
        steps = recs.get(p, {})
        for rep in range(1, (e1.get("reps") or 0) + 1):
            for name in [f"e0-r{rep}", *(f"e1-h{n}-r{rep}" for n in e1.get("sizes") or [])]:
                if name not in steps:
                    out.append(f"{p}: {name} missing")
        if "e2" not in steps:
            out.append(f"{p}: e2 missing")
        for size in (plan.get("e3") or {}).get("sizes") or []:
            if f"e3-h{size}-r1" not in steps:
                out.append(f"{p}: e3-h{size}-r1 missing")
    return out
