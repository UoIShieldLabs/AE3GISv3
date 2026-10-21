"""Shared matplotlib figures: static, so GitHub renders the notebooks."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm

from .hosts import HOSTS
from .load import INTERVALS, RATES
from .traffic_suite import SCENARIO_ORDER, grid, label_grid, scenario_name

GREY = "#9a9a9a"


def style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 100,
            "savefig.dpi": 100,
            "figure.figsize": (9, 4.5),
            "axes.grid": True,
            "grid.alpha": 0.3,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "font.size": 10,
        }
    )


def _scenario(s: str) -> str:
    p, q = s.split("·")
    return scenario_name(p, q)


# ── traffic grids ─────────────────────────────────────────────────────


def limit_heatmaps(cells: pd.DataFrame, title: str, vmax: float | None = None) -> plt.Figure:
    """The four scenarios' rate × interval grids, coloured by the comfortable
    size (log scale) and labelled like the runner's summary."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.5), constrained_layout=True)
    vals = cells["comfortable"].dropna()
    norm = LogNorm(
        vmin=max(25, vals.min() if len(vals) else 25),
        vmax=vmax or max(100, vals.max() if len(vals) else 100),
    )
    im = None
    for ax, scen in zip(axes.flat, SCENARIO_ORDER, strict=False):
        g = grid(cells, scen).astype(float)
        labels = label_grid(cells, scen)
        im = ax.imshow(g.values, cmap="viridis", norm=norm, aspect="auto")
        for i in range(len(RATES)):
            for j in range(len(INTERVALS)):
                v, text = g.values[i, j], labels.values[i, j]
                dark = not np.isnan(v) and norm(v) < 0.55
                text = text or "–"
                ax.text(
                    j,
                    i,
                    text,
                    ha="center",
                    va="center",
                    fontsize=8 if len(text) <= 11 else 6.5,
                    color="white" if dark else "black",
                )
        ax.set_xticks(range(len(INTERVALS)), [f"{i} ms" for i in INTERVALS])
        ax.set_yticks(range(len(RATES)), RATES)
        ax.set_title(_scenario(scen))
        ax.set_xlabel("burst interval")
        ax.set_ylabel("rate per flow")
        ax.grid(False)
    fig.colorbar(im, ax=axes, shrink=0.6, label="comfortable hosts (log)")
    fig.suptitle(title, fontweight="bold")
    return fig


def value_heatmaps(
    grids: dict[str, pd.DataFrame],
    title: str,
    fmt: str = "{:.0f}",
    cmap: str = "magma",
    log: bool = False,
    unit: str = "",
) -> plt.Figure:
    """One heatmap per scenario of an already pivoted rate × interval value
    (a 2 × 2 grid for four scenarios, one row for fewer)."""
    scens = [s for s in SCENARIO_ORDER if s in grids]
    if len(scens) == 4:
        fig, axes = plt.subplots(2, 2, figsize=(12, 7), constrained_layout=True)
    else:
        fig, axes = plt.subplots(
            1, len(scens), figsize=(6 * len(scens), 3.8), constrained_layout=True
        )
    axes = np.atleast_1d(axes)
    allv = pd.concat([g.stack() for g in grids.values() if g is not None and not g.empty])
    allv = allv[allv > 0] if log else allv
    if allv.empty:
        plt.close(fig)
        return None
    norm = (
        LogNorm(vmin=allv.min(), vmax=allv.max()) if log else plt.Normalize(allv.min(), allv.max())
    )
    im = None
    for ax, scen in zip(axes.flat, scens, strict=False):
        g = grids[scen].reindex(index=RATES, columns=INTERVALS).astype(float)
        im = ax.imshow(g.values, cmap=cmap, norm=norm, aspect="auto")
        for i in range(len(RATES)):
            for j in range(len(INTERVALS)):
                v = g.values[i, j]
                if np.isnan(v):
                    ax.text(j, i, "–", ha="center", va="center", fontsize=8, color=GREY)
                    continue
                dark = norm(v) < 0.55
                ax.text(
                    j,
                    i,
                    fmt.format(v),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if dark else "black",
                )
        ax.set_xticks(range(len(INTERVALS)), [f"{i} ms" for i in INTERVALS])
        ax.set_yticks(range(len(RATES)), RATES)
        ax.set_title(_scenario(scen))
        ax.grid(False)
    fig.colorbar(im, ax=axes, shrink=0.6, label=unit)
    fig.suptitle(title, fontweight="bold")
    return fig


def interval_lines(cells: pd.DataFrame, title: str) -> plt.Figure:
    """Comfortable hosts against the burst interval, one line per rate."""
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.6), sharey=False, constrained_layout=True)
    colors = plt.cm.plasma(np.linspace(0.1, 0.85, len(RATES)))
    for ax, scen in zip(axes, SCENARIO_ORDER, strict=False):
        g = grid(cells, scen)
        for rate, color in zip(RATES, colors, strict=False):
            ax.plot(INTERVALS, g.loc[rate].values, marker="o", color=color, label=rate)
        ax.set_xscale("log")
        ax.set_xticks(INTERVALS, [str(i) for i in INTERVALS])
        ax.minorticks_off()
        ax.set_title(_scenario(scen))
        ax.set_xlabel("burst interval (ms)")
    axes[0].set_ylabel("comfortable hosts")
    axes[-1].legend(title="rate", fontsize=8)
    fig.suptitle(title, fontweight="bold")
    return fig


def cost_lines(cost: pd.DataFrame, title: str) -> plt.Figure:
    """Cores per 100 Mb/s against lab size, one line per scenario."""
    fig, ax = plt.subplots(figsize=(8, 4))
    for scen in SCENARIO_ORDER:
        if scen in cost.index:
            ax.plot(cost.columns, cost.loc[scen].values, marker="o", label=_scenario(scen))
    ax.set_yscale("log")
    ax.set_xlabel("lab size (hosts)")
    ax.set_ylabel("lab CPU cores per 100 Mb/s")
    ax.set_title(title)
    ax.legend(fontsize=8)
    return fig


def deploy_costs(deploys: pd.DataFrame, title: str) -> plt.Figure | None:
    d = deploys[deploys["outcome"] == "ok"].dropna(subset=["nodes"])
    if d.empty:
        return None
    d = d.groupby("size").median(numeric_only=True).reset_index()
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 3.8), constrained_layout=True)
    a.plot(d["size"], d["deploy_s"], marker="o", label="deploy")
    a.plot(d["size"], d["destroy_s"], marker="s", label="destroy")
    a.set_xlabel("hosts")
    a.set_ylabel("seconds")
    a.set_title("deploy and destroy time")
    a.legend()
    b.plot(d["size"], d["mem_settle_gb"], marker="o", color="#8c564b")
    b.set_xlabel("hosts")
    b.set_ylabel("GB in use after the deploy settles")
    b.set_title("memory of the idle lab")
    fig.suptitle(title, fontweight="bold")
    return fig


def search_history(history: pd.DataFrame, title: str) -> plt.Figure:
    """Sizes probed per cell of one scenario: green pass, red fail."""
    cells = list(dict.fromkeys(history["cell"]))
    fig, ax = plt.subplots(figsize=(12, max(3, 0.28 * len(cells))))
    for i, cid in enumerate(cells):
        h = history[history["cell"] == cid]
        ok = h["outcome"] == "ok"
        ax.scatter(h.loc[ok, "size"], [i] * ok.sum(), color="#2ca02c", s=18, zorder=3)
        ax.scatter(
            h.loc[~ok, "size"], [i] * (~ok).sum(), color="#d62728", marker="x", s=22, zorder=3
        )
    ax.set_yticks(range(len(cells)), [c.split("·", 2)[2] for c in cells], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("hosts probed (green: passed, red: failed)")
    ax.set_title(title)
    return fig


# ── idle ──────────────────────────────────────────────────────────────


def ceilings(climbs: pd.DataFrame, color: str, title: str) -> plt.Figure:
    """Each climb's ceiling, the mean and ± std; annotated climbs in grey."""
    fig, ax = plt.subplots(figsize=(9, 3.8))
    c = climbs.dropna(subset=["ceiling"])
    cols = [GREY if note else color for note in c["note"]]
    ax.bar(c["n"].astype(str), c["ceiling"], color=cols)
    m, s = c["ceiling"].mean(), c["ceiling"].std()
    ax.axhline(m, color="black", lw=1)
    ax.axhspan(m - s, m + s, color="black", alpha=0.08)
    for x, (v, note) in enumerate(zip(c["ceiling"], c["note"], strict=False)):
        ax.text(
            x, v, f"{v:.0f}" + (f"\n{note}" if note else ""), ha="center", va="bottom", fontsize=7
        )
    ax.set_xlabel("climb")
    ax.set_ylabel("ceiling (hosts)")
    ax.set_title(f"{title}: {m:.0f} ± {s:.0f} hosts")
    return fig


def trajectories(steps: pd.DataFrame, climbs: pd.DataFrame, title: str) -> plt.Figure:
    """Per climb: memory % against hosts, and deploy / ready time against nodes."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.8), constrained_layout=True)
    notes = dict(zip(climbs["run"], climbs["note"], strict=False))
    colors = plt.cm.tab10(np.linspace(0, 1, 10))
    for (run, st), color in zip(steps.groupby("run", sort=False), colors, strict=False):
        st = st.sort_values("scale")
        ok = st[st["outcome"] == "ok"]
        style_ = dict(color=GREY if notes.get(run) else color, alpha=0.9, marker="o", ms=3, lw=1)
        axes[0].plot(ok["scale"], ok["mem_pct"], **style_)
        axes[1].plot(ok["nodes"], ok["deploy_s"], **style_)
        axes[2].plot(ok["nodes"], ok["ready_s"], **style_)
    axes[0].set(xlabel="hosts", ylabel="peak memory %", title="memory")
    axes[1].set(xlabel="nodes", ylabel="seconds", title="deploy time")
    axes[2].set(xlabel="nodes", ylabel="seconds", title="network ready time")
    fig.suptitle(title + " (one line per climb; grey: annotated climbs)", fontweight="bold")
    return fig


def census_bars(census: pd.DataFrame, title: str) -> plt.Figure:
    c = census.dropna(subset=["host_mb_per_node"]).sort_values("host_mb_per_node")
    fig, ax = plt.subplots(figsize=(9, max(4, 0.26 * len(c))))
    cols = ["#1f77b4" if u else GREY for u in c["usable"]]
    ax.barh(c["type"] + " · " + c["image"], c["host_mb_per_node"], color=cols)
    ax.set_xscale("log")
    ax.set_xlabel("host MB per node (log; grey: not usable here)")
    ax.tick_params(axis="y", labelsize=7)
    ax.set_title(title)
    return fig


# ── comparison ────────────────────────────────────────────────────────


def host_bars(
    values: pd.DataFrame,
    title: str,
    ylabel: str,
    err: pd.DataFrame | None = None,
    log: bool = False,
) -> plt.Figure:
    """Grouped bars: rows are groups (e.g. scenarios), columns are hosts."""
    fig, ax = plt.subplots(figsize=(10, 4))
    n = len(values.columns)
    width = 0.8 / max(n, 1)
    x = np.arange(len(values.index))
    for i, host in enumerate(values.columns):
        h = HOSTS.get(host)
        ax.bar(
            x + (i - (n - 1) / 2) * width,
            values[host].values,
            width,
            yerr=None if err is None else err[host].values,
            capsize=3,
            color=h.color if h else None,
            label=h.name if h else host,
        )
    ax.set_xticks(x, values.index)
    if log:
        ax.set_yscale("log")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=8)
    return fig


def ceiling_vs_mix(cc: pd.DataFrame, color: str, title: str) -> plt.Figure | None:
    """Each climb's ceiling against the census-weighted MB per node of its mix."""
    if cc.empty:
        return None
    fig, ax = plt.subplots(figsize=(6.5, 4))
    cols = [GREY if note else color for note in cc["note"]]
    ax.scatter(cc["mix_mb_per_node"], cc["ceiling"], color=cols, s=40, zorder=3)
    for _run, r in cc.iterrows():
        ax.annotate(
            str(int(r["n"])),
            (r["mix_mb_per_node"], r["ceiling"]),
            fontsize=7,
            xytext=(4, 3),
            textcoords="offset points",
        )
    ax.set_xlabel("census MB per node of the climb's mix")
    ax.set_ylabel("ceiling (hosts)")
    ax.set_title(title)
    return fig


def idle_comparison(data: dict) -> plt.Figure:
    """Ceilings (bars: mean ± std; dots: every climb), hosts per GB of Docker
    memory, MB per node, deploy seconds per node."""
    hosts = [k for k, d in data.items() if d.random is not None]
    fig, axes = plt.subplots(1, 4, figsize=(15, 4), constrained_layout=True)
    names = [data[k].host.name for k in hosts]
    for i, k in enumerate(hosts):
        d, c = data[k], data[k].random.climbs
        col = d.host.color
        axes[0].bar(
            i, c["ceiling"].mean(), yerr=c["ceiling"].std(), color=col, alpha=0.75, capsize=4
        )
        jitter = np.linspace(-0.2, 0.2, len(c))
        axes[0].scatter(
            i + jitter,
            c["ceiling"],
            color=[GREY if n else "black" for n in c["note"]],
            s=10,
            zorder=3,
        )
        axes[1].bar(
            i,
            (c["ceiling"] / d.host.mem_gb).mean(),
            yerr=(c["ceiling"] / d.host.mem_gb).std(),
            color=col,
            capsize=4,
        )
        axes[2].bar(i, c["mb_per_node"].mean(), yerr=c["mb_per_node"].std(), color=col, capsize=4)
        axes[3].bar(
            i,
            c["deploy_s_per_node"].mean(),
            yerr=c["deploy_s_per_node"].std(),
            color=col,
            capsize=4,
        )
    for ax, t, y in zip(
        axes,
        ("idle ceiling", "hosts per GB of Docker memory", "MB per node", "deploy seconds per node"),
        ("hosts (dots: each climb; grey: annotated)", "hosts / GB", "MB", "s / node"),
        strict=False,
    ):
        ax.set_xticks(range(len(hosts)), names, rotation=15)
        ax.set_title(t)
        ax.set_ylabel(y)
    axes[3].set_yscale("log")
    return fig


def census_agreement(
    table: pd.DataFrame, ref: str, title: str, unit: str = "host MB per node"
) -> plt.Figure:
    """Per-image memory: each host against the reference host."""
    fig, ax = plt.subplots(figsize=(6.5, 6))
    lo, hi = np.nanmin(table.values[table.values > 0]), np.nanmax(table.values)
    ax.plot([lo, hi], [lo, hi], color=GREY, lw=1, ls="--", label="same cost")
    for host in table.columns:
        if host == ref:
            continue
        h = HOSTS[host]
        ax.scatter(table[ref], table[host], color=h.color, s=22, label=h.name, zorder=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(f"{HOSTS[ref].name}: {unit}")
    ax.set_ylabel(f"other host: {unit}")
    ax.set_title(title)
    ax.legend(fontsize=8)
    return fig


def high_rate_comparison(values: dict[str, pd.DataFrame], title: str) -> plt.Figure:
    """Comfortable hosts per scenario, one panel per rate; ``values[rate]`` has
    scenarios as rows and hosts as columns."""
    rates = list(values)
    fig, axes = plt.subplots(1, len(rates), figsize=(5 * len(rates), 4), constrained_layout=True)
    for ax, rate in zip(np.atleast_1d(axes), rates, strict=False):
        v = values[rate]
        n = len(v.columns)
        width = 0.8 / n
        x = np.arange(len(v.index))
        for i, host in enumerate(v.columns):
            h = HOSTS[host]
            ax.bar(
                x + (i - (n - 1) / 2) * width, v[host].values, width, color=h.color, label=h.name
            )
        ax.set_xticks(x, [_scenario(s) for s in v.index], rotation=20, fontsize=8)
        ax.set_title(f"{rate} per flow")
        ax.set_ylabel("comfortable hosts (median over intervals)")
    np.atleast_1d(axes)[0].legend(fontsize=8)
    fig.suptitle(title, fontweight="bold")
    return fig
