"""Summaries of a traffic run from its samples (pure)."""

from __future__ import annotations

from statistics import median
from typing import Any


def _stats(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    return {
        "mean": sum(values) / len(values),
        "p50": median(values),
        "min": min(values),
        "max": max(values),
    }


def summarize_flow(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Per direction: throughput as the receiver measured it (what actually
    arrived), bytes, TCP retransmits and RTT from the sender, UDP jitter and
    loss from the receiver. Omitted (warm-up) intervals are left out."""
    out: dict[str, Any] = {}
    for direction in ("fwd", "rev"):
        rows = [s for s in samples if s["direction"] == direction and not s.get("omitted")]
        if not rows:
            continue
        rx = [s for s in rows if s["side"] == "receiver"]
        tx = [s for s in rows if s["side"] == "sender"]
        measured = rx or tx
        entry: dict[str, Any] = {
            "intervals": len(measured),
            "measured_by": "receiver" if rx else "sender",
            "bps": _stats([s["bps"] for s in measured]),
            "bytes": sum(s["bytes"] for s in measured),
            "sent_bytes": sum(s["bytes"] for s in tx) if tx else None,
        }
        retrans = [s["retransmits"] for s in tx if s.get("retransmits") is not None]
        if retrans:
            entry["retransmits"] = sum(retrans)
        rtts = [s["rtt_ms"] for s in tx if s.get("rtt_ms") is not None]
        if rtts:
            entry["rtt_ms"] = _stats(rtts)
        jitter = [s["jitter_ms"] for s in rx if s.get("jitter_ms") is not None]
        if jitter:
            entry["jitter_ms"] = _stats(jitter)
        lost = [s["lost_packets"] for s in rx if s.get("lost_packets") is not None]
        packets = [s["packets"] for s in rx if s.get("packets") is not None]
        if lost:
            total = sum(packets)
            entry["lost_packets"] = sum(lost)
            entry["packets"] = total
            entry["lost_percent"] = 100 * sum(lost) / total if total else 0.0
        out[direction] = entry
    return out
