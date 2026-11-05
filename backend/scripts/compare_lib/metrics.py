"""Monitor sweeps and host samples → numbers per phase window.

Inside the VM (the monitor, ``ae3gis-collect``):
- CPU: busy share of all the VM's CPUs (from ``/proc/stat`` tick deltas), and
  the same as cores;
- memory used: ``MemTotal - MemAvailable``;
- the lab's containers: memory (used minus inactive file, as ``docker stats``)
  and CPU cores; the other containers (probes, the AE3GIS backend) apart;
- the platform's own processes (``infra``: dockerd, containerd(-shim),
  vde_switch / ubridge, gns3server): RSS and cores;
- Docker's disk used, and PSI stall totals (CPU, memory, I/O).

On the host (``HostSampler``): footprint, RSS and cores of the VM process and
of its helpers, and the host's CPU and memory.
"""

from __future__ import annotations

import statistics
from typing import Any


def _mean(xs: list[float]) -> float | None:
    return round(statistics.fmean(xs), 4) if xs else None


def _max(xs: list[float]) -> float | None:
    return max(xs) if xs else None


def mem_used(line: dict) -> int | None:
    m = (line.get("host") or {}).get("mem") or {}
    if "MemTotal" in m and "MemAvailable" in m:
        return m["MemTotal"] - m["MemAvailable"]
    return None


def _cpu_pairs(lines: list[dict]):
    for a, b in zip(lines, lines[1:], strict=False):
        ca, cb = (a.get("host") or {}).get("cpu"), (b.get("host") or {}).get("cpu")
        if ca and cb and len(ca) == len(cb) and b["t"] > a["t"]:
            yield a, b, ca, cb


def vm_cpu(lines: list[dict]) -> list[tuple[float, float, float]]:
    """(end time, busy share 0..1, cores) per sweep interval."""
    out = []
    for _a, b, ca, cb in _cpu_pairs(lines):
        d = [y - x for x, y in zip(ca, cb, strict=True)]
        total = sum(d)
        if total <= 0:
            continue
        idle = d[3] + d[4]  # idle + iowait
        share = (total - idle) / total
        out.append((b["t"], share, share * (b.get("ncpu") or 1)))
    return out


def _container_mem(v: list) -> int:
    used, inactive = v[1] or 0, v[2] or 0
    return max(0, used - inactive)


def containers(lines: list[dict], lab: set[str]) -> dict[str, Any]:
    """Memory and CPU of the lab's containers (12-char ids) and of the others."""
    mem_lab, mem_other, n_lab = [], [], []
    cores_lab, cores_other = [], []
    for a, b in zip(lines, lines[1:], strict=False):
        dt = b["t"] - a["t"]
        if dt <= 0:
            continue
        ca, cb = a.get("c") or {}, b.get("c") or {}
        cl = co = 0.0
        for cid, v in cb.items():
            if cid in ca:
                du = max(0, (v[0] or 0) - (ca[cid][0] or 0)) / 1e6 / dt
                if cid in lab:
                    cl += du
                else:
                    co += du
        cores_lab.append(cl)
        cores_other.append(co)
    for x in lines:
        c = x.get("c") or {}
        mem_lab.append(sum(_container_mem(v) for k, v in c.items() if k in lab))
        mem_other.append(sum(_container_mem(v) for k, v in c.items() if k not in lab))
        n_lab.append(sum(1 for k in c if k in lab))
    return {
        "lab_n": max(n_lab) if n_lab else 0,
        "lab_mem": _mean(mem_lab),
        "lab_mem_max": _max(mem_lab),
        "lab_cores": _mean(cores_lab),
        "other_mem": _mean(mem_other),
        "other_cores": _mean(cores_other),
    }


def infra(lines: list[dict]) -> dict[str, dict[str, float | None]]:
    """Per platform process name: count, RSS and cores (from tick deltas)."""
    names = {n for x in lines for n in (x.get("infra") or {})}
    out = {}
    for n in sorted(names):
        rss = [x["infra"][n][1] for x in lines if n in (x.get("infra") or {})]
        cnt = [x["infra"][n][0] for x in lines if n in (x.get("infra") or {})]
        cores = []
        for a, b in zip(lines, lines[1:], strict=False):
            ia, ib = (a.get("infra") or {}).get(n), (b.get("infra") or {}).get(n)
            dt = b["t"] - a["t"]
            if ia and ib and dt > 0:
                cores.append(max(0, ib[2] - ia[2]) / (b.get("clk_tck") or 100) / dt)
        out[n] = {"n": _max(cnt), "rss": _mean(rss), "cores": _mean(cores)}
    return out


def psi_delta(lines: list[dict]) -> dict[str, float | None]:
    """Stall time per second of window (``some``), per resource."""
    out: dict[str, float | None] = {}
    if len(lines) < 2:
        return out
    a, b = lines[0], lines[-1]
    dt = b["t"] - a["t"]
    for res in ("cpu", "memory", "io"):
        pa = ((a.get("host") or {}).get("psi") or {}).get(res, {}).get("some")
        pb = ((b.get("host") or {}).get("psi") or {}).get(res, {}).get("some")
        out[res] = round((pb[1] - pa[1]) / 1e6 / dt, 5) if pa and pb and dt > 0 else None
    return out


def monitor_window(lines: list[dict], lab: set[str] | None = None) -> dict[str, Any]:
    """Everything the monitor says about one window."""
    if not lines:
        return {"sweeps": 0}
    cpu = vm_cpu(lines)
    used = [u for u in (mem_used(x) for x in lines) if u is not None]
    disk = [(x.get("host") or {}).get("disk") for x in lines]
    disk = [d[0] - d[1] for d in disk if d]
    return {
        "sweeps": len(lines),
        "t": [lines[0]["t"], lines[-1]["t"]],
        "cpu_share": _mean([c[1] for c in cpu]),
        "cpu_cores": _mean([c[2] for c in cpu]),
        "cpu_cores_max": _max([c[2] for c in cpu]),
        "mem_used": _mean(used),
        "mem_used_max": _max(used),
        "mem_total": ((lines[-1].get("host") or {}).get("mem") or {}).get("MemTotal"),
        "disk_used": disk[-1] if disk else None,
        "containers": containers(lines, lab or set()),
        "infra": infra(lines),
        "psi": psi_delta(lines),
        "sweep_ms": _max([x.get("sweep_ms") or 0 for x in lines]),
    }


def host_window(samples: list[dict]) -> dict[str, Any]:
    """Footprint, RSS and cores per group, and the host's CPU and memory."""
    if not samples:
        return {"samples": 0}
    groups = {g for s in samples for g in s.get("g", {})}
    out: dict[str, Any] = {"samples": len(samples)}
    for g in sorted(groups):
        vals = [s["g"][g] for s in samples if g in s.get("g", {})]
        out[g] = {
            "footprint": _mean([v["footprint"] for v in vals]),
            "footprint_max": _max([v["footprint"] for v in vals]),
            "rss": _mean([v["rss"] for v in vals]),
            "rss_max": _max([v["rss"] for v in vals]),
            "cores": _mean([v["cores"] for v in vals if v["cores"] is not None]),
        }
    cpu = [s["cpu"] for s in samples if s.get("cpu")]
    out["host_cpu_busy"] = _mean([100 - c.get("idle", 100) for c in cpu])
    pm = [s["physmem"] for s in samples if s.get("physmem")]
    out["host_used"] = _mean([p.get("used", 0) for p in pm])
    out["host_compressor"] = _mean([p.get("compressor", 0) for p in pm])
    return out


def series(lines: list[dict], host: list[dict], lab: set[str], t_offset: float) -> list[list]:
    """A compact time series for plots: [t (runner clock), VM CPU cores, VM
    memory used, lab memory, VM footprint on the host] per sweep."""
    out = []
    cpu = {t: cores for t, _share, cores in vm_cpu(lines)}
    hi = 0
    for x in lines:
        rt = x["t"] + t_offset
        while hi + 1 < len(host) and host[hi + 1]["rt"] <= rt:
            hi += 1
        fp = host[hi]["g"].get("vm", {}).get("footprint") if host else None
        c = x.get("c") or {}
        out.append(
            [
                round(rt, 2),
                round(cpu.get(x["t"], 0.0), 3),
                mem_used(x),
                sum(_container_mem(v) for k, v in c.items() if k in lab),
                fp,
            ]
        )
    return out
