"""Traffic for E2, through the netns driver (``ae3gis-netns`` run mode), the
same way on both platforms: every process runs in a node's network namespace
with the driver image's binaries.

- **latency:** ``ping`` between host pairs (BusyBox: one ``time=`` per reply);
- **flat-out:** one unpaced iperf3 TCP flow;
- **load:** a pattern's flows (clients → servers, or mesh), each at a constant
  rate, TCP or UDP, measured over a fixed window that starts once every client
  has started (the driver's ``clients_started``).

Times are the VM's clock (the driver's and the monitor's), so a window can be
cut from the monitor's sweeps directly.
"""

from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from domain.traffic import iperf3  # noqa: E402  (pure: argv builders, stream parser)

UDP_LEN = iperf3.UDP_MAX_LEN
# Paced TCP writes: iperf3's default 128 KB write comes once a second at 1M
# (once in 10 s at 100K), so a window's edges would gain or lose a whole block;
# 8 KB keeps that under ~1% at 100K over 60 s. Unpaced TCP keeps the default.
TCP_PACED_LEN = 8192
_PING = re.compile(r"time=([\d.]+) ms")


def pct(values: list[float], q: float) -> float | None:
    """The q-th percentile (nearest rank), None without values."""
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, max(0, round(q / 100 * len(s) + 0.5) - 1))]


# ── latency ──


def ping_spec(pairs: list[dict], pids: dict[str, int], count: int, interval: float) -> dict:
    procs = [
        {
            "id": f"ping{i}",
            "pid": pids[p["client"]],
            "role": "client",
            "argv": ["ping", "-c", str(count), "-i", str(interval), "-W", "1", p["server_address"]],
        }
        for i, p in enumerate(pairs)
    ]
    return {"mode": "run", "ramp_s": 0, "grace_s": 5, "procs": procs}


def ping_summary(events: list[dict], count: int) -> dict:
    rtts: dict[str, list[float]] = {}
    for e in events:
        if e.get("k") == "out":
            m = _PING.search(e.get("line", ""))
            if m:
                rtts.setdefault(e["p"], []).append(float(m.group(1)))
    every = [x for v in rtts.values() for x in v]
    sent = count * len({e["p"] for e in events if e.get("k") == "started"})
    return {
        "pairs": len(rtts),
        "replies": len(every),
        "sent": sent,
        "p50_ms": pct(every, 50),
        "p95_ms": pct(every, 95),
        "max_ms": max(every) if every else None,
        "mean_ms": round(statistics.fmean(every), 4) if every else None,
    }


# ── iperf3 runs ──


def iperf_spec(
    flows: list[dict],
    pids: dict[str, int],
    *,
    protocol: str,
    rate: str | None,
    duration_s: int,
    interval_s: float = 1.0,
) -> dict:
    """Servers and clients for ``flows`` (``id, client, server,
    server_address, port``), every client at ``rate`` (None: unpaced TCP)."""
    procs = []
    for f in flows:
        procs.append(
            {
                "id": f"{f['id']}.s",
                "pid": pids[f["server"]],
                "role": "server",
                "port": f["port"],
                "argv": iperf3.server_argv(f["port"], interval_s),
            }
        )
        flow = {"protocol": protocol, "bitrate": rate, "duration_s": duration_s}
        if protocol == "udp":
            flow["length"] = UDP_LEN
        elif rate:
            flow["length"] = TCP_PACED_LEN
        procs.append(
            {
                "id": f"{f['id']}.c",
                "pid": pids[f["client"]],
                "role": "client",
                "retries": 3,
                "argv": iperf3.client_argv(flow, f["server_address"], f["port"], interval_s),
            }
        )
    return {"mode": "run", "ramp_s": 0, "ready_timeout_s": 30, "grace_s": 10, "procs": procs}


def samples(events: list[dict]) -> list[iperf3.FlowSample]:
    """Every interval sample of every process, timed in the VM's clock."""
    started: dict[str, float] = {}
    parsers: dict[str, iperf3.Iperf3StreamParser] = {}
    out: list[iperf3.FlowSample] = []
    for e in events:
        k, p = e.get("k"), e.get("p")
        if k == "started":
            started[p] = float(e["t"])
            flow, _, end = p.rpartition(".")
            parsers[p] = iperf3.Iperf3StreamParser(
                flow, "server" if end == "s" else "client", offset=started[p]
            )
        elif k == "out" and p in parsers:
            ev = parsers[p].parse_line(e.get("line", ""))
            if ev and ev.kind == "interval":
                out += ev.samples
    return out


def load_summary(
    events: list[dict], *, n_flows: int, rate_bps: float | None, window_s: float
) -> dict:
    """Offered vs delivered over the window after ``clients_started``: the
    receivers' bytes (the server side of forward flows), UDP loss and jitter,
    TCP retransmits and RTT."""
    cs = next((e for e in events if e.get("k") == "clients_started"), None)
    if cs is None:
        return {"error": "no clients_started", "errors": _errors(events)}
    w0, w1 = float(cs["t"]), float(cs["t"]) + window_s
    rx = [
        s
        for s in samples(events)
        if s.direction == "fwd" and s.side == "receiver" and w0 < s.t <= w1 + 0.5
    ]
    tx = [
        s
        for s in samples(events)
        if s.direction == "fwd" and s.side == "sender" and w0 < s.t <= w1 + 0.5
    ]
    delivered = sum(s.bytes for s in rx) * 8 / window_s
    offered = rate_bps * n_flows if rate_bps else None
    packets = sum(s.packets or 0 for s in rx)
    lost = sum(s.lost_packets or 0 for s in rx)
    rtts = [s.rtt_ms for s in tx if s.rtt_ms is not None]
    jit = [s.jitter_ms for s in rx if s.jitter_ms is not None]
    per_flow: dict[str, int] = {}
    for s in rx:
        per_flow[s.flow_id] = per_flow.get(s.flow_id, 0) + s.bytes
    return {
        "window": [round(w0, 3), round(w1, 3)],
        "flows": n_flows,
        "clients_started": cs.get("n"),
        "clients_failed": len(cs.get("failed") or []) + len(cs.get("never_started") or []),
        "flows_measured": len(per_flow),
        "offered_bps": offered,
        "delivered_bps": round(delivered, 1),
        "delivered_ratio": round(delivered / offered, 4) if offered else None,
        "loss": round(lost / packets, 5) if packets else None,
        "jitter_ms": round(statistics.fmean(jit), 4) if jit else None,
        "retransmits": sum(s.retransmits or 0 for s in tx) if tx else None,
        "rtt_p95_ms": pct(rtts, 95),
        "errors": _errors(events),
    }


def _errors(events: list[dict]) -> list[str]:
    out = [e.get("message", "") for e in events if e.get("k") == "error"]
    out += [
        f"{e['p']}: {e.get('line', '')[:120]}"
        for e in events
        if e.get("k") == "err" and e.get("line", "").strip()
    ]
    return out[:10]
