"""Summaries of a traffic run from its samples (pure).

``FlowSummary`` takes samples one at a time and keeps only what the summary
needs (one float per interval for medians), so a run of thousands of flows
over hours never holds its samples in memory; ``summarize_flow`` is the same
over a finished list.
"""

from __future__ import annotations

from array import array
from statistics import median
from typing import Any


def _stats(values) -> dict[str, float] | None:
    if not values:
        return None
    return {
        "mean": sum(values) / len(values),
        "p50": median(values),
        "min": min(values),
        "max": max(values),
    }


class _Direction:
    __slots__ = (
        "rx_bps",
        "tx_bps",
        "rx_bytes",
        "tx_bytes",
        "retrans",
        "rtt",
        "jitter",
        "lost",
        "packets",
    )

    def __init__(self) -> None:
        self.rx_bps = array("d")
        self.tx_bps = array("d")
        self.rx_bytes = 0
        self.tx_bytes = 0
        self.retrans: int | None = None
        self.rtt = array("d")
        self.jitter = array("d")
        self.lost: int | None = None
        self.packets = 0

    def add(self, s: dict[str, Any]) -> None:
        if s["side"] == "receiver":
            self.rx_bps.append(s["bps"])
            self.rx_bytes += s["bytes"]
            if s.get("jitter_ms") is not None:
                self.jitter.append(s["jitter_ms"])
            if s.get("lost_packets") is not None:
                self.lost = (self.lost or 0) + s["lost_packets"]
                self.packets += s.get("packets") or 0
        else:
            self.tx_bps.append(s["bps"])
            self.tx_bytes += s["bytes"]
            if s.get("retransmits") is not None:
                self.retrans = (self.retrans or 0) + s["retransmits"]
            if s.get("rtt_ms") is not None:
                self.rtt.append(s["rtt_ms"])

    def result(self) -> dict[str, Any]:
        rx = bool(self.rx_bps)
        measured = self.rx_bps if rx else self.tx_bps
        entry: dict[str, Any] = {
            "intervals": len(measured),
            "measured_by": "receiver" if rx else "sender",
            "bps": _stats(measured),
            "bytes": self.rx_bytes if rx else self.tx_bytes,
            "sent_bytes": self.tx_bytes if self.tx_bps else None,
        }
        if self.retrans is not None:
            entry["retransmits"] = self.retrans
        if self.rtt:
            entry["rtt_ms"] = _stats(self.rtt)
        if self.jitter:
            entry["jitter_ms"] = _stats(self.jitter)
        if self.lost is not None:
            entry["lost_packets"] = self.lost
            entry["packets"] = self.packets
            entry["lost_percent"] = 100 * self.lost / self.packets if self.packets else 0.0
        return entry


class FlowSummary:
    """Per direction: throughput as the receiver measured it (what actually
    arrived), bytes, TCP retransmits and RTT from the sender, UDP jitter and
    loss from the receiver. Omitted (warm-up) intervals are left out."""

    def __init__(self) -> None:
        self._dirs: dict[str, _Direction] = {}

    def add(self, sample: dict[str, Any]) -> None:
        if sample.get("omitted"):
            return
        self._dirs.setdefault(sample["direction"], _Direction()).add(sample)

    def result(self) -> dict[str, Any]:
        return {d: self._dirs[d].result() for d in ("fwd", "rev") if d in self._dirs}


def summarize_flow(samples: list[dict[str, Any]]) -> dict[str, Any]:
    summary = FlowSummary()
    for s in samples:
        summary.add(s)
    return summary.result()
