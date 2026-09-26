"""iperf3 command lines and its ``--json-stream`` output (pure).

With ``--json-stream`` iperf3 prints one JSON object per line: ``start``, one
``interval`` per second, then ``end`` (plus ``error``, e.g. when interrupted
or refused). Both ends report: the client and the server each describe what
they sent and received, so a flow yields sender and receiver samples.

Directions are relative to the flow: ``fwd`` is client → server, ``rev`` is
server → client (``-R`` makes the whole flow ``rev``; ``--bidir`` has both).
Output shapes are pinned by fixtures recorded from a real lab
(``tests/fixtures/iperf3``).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

DEFAULT_PORT = 5201


@dataclass
class FlowSample:
    t: float  # seconds since the run started (interval end)
    flow_id: str
    direction: str  # fwd | rev
    side: str  # sender | receiver
    bps: float
    bytes: int
    seconds: float
    omitted: bool = False
    retransmits: int | None = None
    rtt_ms: float | None = None
    packets: int | None = None
    jitter_ms: float | None = None
    lost_packets: int | None = None
    lost_percent: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Iperf3Event:
    """What one line of output meant."""

    kind: str  # start | interval | end | error | other
    samples: list[FlowSample] = field(default_factory=list)
    data: Any = None  # the start/end payload, or the error text


def client_argv(flow: dict[str, Any], server_ip: str, port: int, interval: float) -> list[str]:
    argv = ["iperf3", "-c", server_ip, "-p", str(port), "--json-stream", "-i", _num(interval)]
    argv += ["-t", str(int(flow.get("duration_s") or 0))]
    if flow.get("protocol") == "udp":
        argv += ["-u", "-b", str(flow.get("bitrate") or "1M")]
    elif flow.get("bitrate"):
        argv += ["-b", str(flow["bitrate"])]
    if (flow.get("parallel") or 1) > 1:
        argv += ["-P", str(flow["parallel"])]
    if flow.get("length"):
        argv += ["-l", str(flow["length"])]
    if flow.get("omit_s"):
        argv += ["-O", str(flow["omit_s"])]
    direction = flow.get("direction") or "forward"
    if direction == "reverse":
        argv.append("-R")
    elif direction == "bidir":
        argv.append("--bidir")
    argv += ["--connect-timeout", "3000"]
    return argv


def server_argv(port: int, interval: float) -> list[str]:
    # -1: serve one test, then exit.
    return ["iperf3", "-s", "-1", "-p", str(port), "--json-stream", "-i", _num(interval)]


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _sample(
    block: dict[str, Any], flow_id: str, role: str, offset: float, streams: list[dict[str, Any]]
) -> FlowSample:
    sender = bool(block.get("sender"))
    # The client sends fwd traffic and receives rev; the server the opposite.
    fwd = sender if role == "client" else not sender
    rtts = [s["rtt"] for s in streams if s.get("sender") == sender and s.get("rtt")]
    return FlowSample(
        t=round(offset + float(block.get("end", 0)), 3),
        flow_id=flow_id,
        direction="fwd" if fwd else "rev",
        side="sender" if sender else "receiver",
        bps=float(block.get("bits_per_second", 0)),
        bytes=int(block.get("bytes", 0)),
        seconds=float(block.get("seconds", 0)),
        omitted=bool(block.get("omitted")),
        retransmits=block.get("retransmits"),
        rtt_ms=round(sum(rtts) / len(rtts) / 1000, 3) if rtts else None,
        packets=block.get("packets"),
        jitter_ms=block.get("jitter_ms"),
        lost_packets=block.get("lost_packets"),
        lost_percent=block.get("lost_percent"),
    )


class Iperf3StreamParser:
    """Feed raw output (any chunking) from one end of one flow."""

    def __init__(self, flow_id: str, role: str, offset: float = 0.0) -> None:
        assert role in ("client", "server")
        self.flow_id = flow_id
        self.role = role
        self.offset = offset
        self._buf = b""
        self.start: dict[str, Any] | None = None
        self.end: dict[str, Any] | None = None
        self.errors: list[str] = []

    def feed(self, chunk: bytes) -> list[Iperf3Event]:
        self._buf += chunk
        out = []
        while b"\n" in self._buf:
            line, self._buf = self._buf.split(b"\n", 1)
            event = self.parse_line(line)
            if event is not None:
                out.append(event)
        return out

    def parse_line(self, line: bytes | str) -> Iperf3Event | None:
        try:
            obj = json.loads(line)
        except (ValueError, TypeError):
            return None
        if not isinstance(obj, dict):
            return None
        kind, data = obj.get("event"), obj.get("data")
        if kind == "start":
            self.start = data if isinstance(data, dict) else {}
            return Iperf3Event("start", data=self.start)
        if kind == "interval" and isinstance(data, dict):
            streams = [s for s in data.get("streams") or [] if isinstance(s, dict)]
            samples = [
                _sample(data[key], self.flow_id, self.role, self.offset, streams)
                for key in ("sum", "sum_bidir_reverse")
                if isinstance(data.get(key), dict)
            ]
            return Iperf3Event("interval", samples=samples)
        if kind == "end":
            self.end = data if isinstance(data, dict) else {}
            return Iperf3Event("end", data=self.end)
        if kind == "error":
            text = str(data)
            self.errors.append(text)
            return Iperf3Event("error", data=text)
        return Iperf3Event("other", data=data)


def is_interrupt(error: str) -> bool:
    """The error iperf3 prints when we stop it (not a failure)."""
    return "interrupt" in error or "the client has terminated" in error
