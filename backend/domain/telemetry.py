"""Container stats samples → rates (pure).

Docker reports cumulative counters; a sample's rates come from the previous
one. CPU is in Docker's units (100 = one core fully used), memory excludes
the page cache (``usage - inactive_file``, as ``docker stats`` shows it).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from engine.base import RawStats


def rates(prev: RawStats | None, cur: RawStats, t: float) -> dict[str, Any]:
    """One node/sidecar sample at run time ``t`` (seconds)."""
    mem_used = cur.mem_usage - (cur.mem_inactive_file or 0)
    sample: dict[str, Any] = {
        "t": round(t, 3),
        "target": cur.target,
        "kind": cur.kind,
        "cpu_percent": None,
        "mem_used": max(mem_used, 0),
        "mem_limit": cur.mem_limit,
        "pids": cur.pids,
        "ifaces": {},
    }
    if prev is None:
        return sample
    dt = cur.ts - prev.ts
    if dt <= 0:
        return sample
    dcpu = cur.cpu_total_ns - prev.cpu_total_ns
    if dcpu >= 0:
        dsys = (cur.system_cpu_ns or 0) - (prev.system_cpu_ns or 0)
        if cur.system_cpu_ns and prev.system_cpu_ns and dsys > 0 and cur.online_cpus:
            sample["cpu_percent"] = round(dcpu / dsys * cur.online_cpus * 100, 2)
        else:
            sample["cpu_percent"] = round(dcpu / (dt * 1e9) * 100, 2)
    for name, c in cur.ifaces.items():
        p = prev.ifaces.get(name)
        if p is None:
            continue
        a, b = asdict(p), asdict(c)
        d = {k: b[k] - a[k] for k in b}
        if any(v < 0 for v in d.values()):  # counters reset (interface recreated)
            continue
        sample["ifaces"][name] = {
            "rx_bps": round(d["rx_bytes"] * 8 / dt),
            "tx_bps": round(d["tx_bytes"] * 8 / dt),
            "rx_pps": round(d["rx_packets"] / dt, 1),
            "tx_pps": round(d["tx_packets"] / dt, 1),
            "rx_dropped": d["rx_dropped"],
            "tx_dropped": d["tx_dropped"],
            "errors": d["rx_errors"] + d["tx_errors"],
        }
    return sample
