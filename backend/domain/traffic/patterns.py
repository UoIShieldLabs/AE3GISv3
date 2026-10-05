"""Traffic patterns → flows (pure).

A run's flows come from explicit ``flows`` and from ``patterns``: one line
that says who talks to whom, with one set of flow parameters (protocol,
bitrate, direction, streams…) for every flow it makes.

- ``clients_to_servers``: each client sends to one server (``each: one``,
  round-robin over the servers) or to every server (``each: all``). Clients
  that are also servers are left out.
- ``mesh``: the nodes stand on a ring (topology order) and each sends to the
  next ``fanout`` nodes, so every node sends and receives exactly ``fanout``
  flows; ``fanout = n - 1`` is a full mesh.

Clients and mesh nodes default to the hosts (routers and switches only carry
traffic unless picked).

Flow ids are ``<pattern id>.<n>``. Ports are given per server node (5201,
5202, … for the flows it serves), so thousands of flows never run out of
ports and a node's servers never collide.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from domain.traffic.iperf3 import DEFAULT_PORT, bitrate_bps

# Per-flow iperf3 parameters a pattern passes on to each of its flows.
FLOW_PARAMS = (
    "protocol",
    "bitrate",
    "parallel",
    "length",
    "direction",
    "omit_s",
    "burst_interval_ms",
)

Pick = Callable[[Any], list[str]]  # selector -> node ids (deployed, topology order)
HOSTS = {"roles": ["host"]}


class PatternError(ValueError):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


def _params(pattern: dict[str, Any]) -> dict[str, Any]:
    out = {k: pattern[k] for k in FLOW_PARAMS if pattern.get(k) is not None}
    if str(out.get("bitrate", "")).strip() in ("0", ""):
        out.pop("bitrate", None)  # "0" = as fast as it goes
    return out


def _pairs(pattern: dict[str, Any], pick: Pick) -> list[tuple[str, str]]:
    kind = pattern["kind"]
    if kind == "clients_to_servers":
        servers = pick(pattern.get("servers"))
        if not servers:
            raise PatternError(f"Pattern {pattern['id']!r} has no servers", "no_servers")
        server_set = set(servers)
        clients = [c for c in pick(pattern.get("clients") or HOSTS) if c not in server_set]
        if not clients:
            raise PatternError(f"Pattern {pattern['id']!r} has no clients", "no_clients")
        if pattern.get("each") == "all":
            return [(c, s) for c in clients for s in servers]
        return [(c, servers[i % len(servers)]) for i, c in enumerate(clients)]
    if kind == "mesh":
        nodes = pick(pattern.get("nodes") or HOSTS)
        if len(nodes) < 2:
            raise PatternError(f"Pattern {pattern['id']!r} needs at least two nodes", "no_nodes")
        fanout = min(int(pattern.get("fanout") or 1), len(nodes) - 1)
        return [
            (nodes[i], nodes[(i + k) % len(nodes)])
            for i in range(len(nodes))
            for k in range(1, fanout + 1)
        ]
    raise PatternError(f"Unknown pattern kind {kind!r}", "bad_pattern")


def expand(patterns: list[dict[str, Any]], pick: Pick) -> list[dict[str, Any]]:
    """The flows ``patterns`` make (without addresses or ports)."""
    flows: list[dict[str, Any]] = []
    for pattern in patterns:
        params = _params(pattern)
        for n, (client, server) in enumerate(_pairs(pattern, pick), 1):
            flows.append(
                {
                    "id": f"{pattern['id']}.{n}",
                    "client": client,
                    "server": server,
                    "pattern": pattern["id"],
                    **params,
                }
            )
    return flows


def assign_ports(flows: list[dict[str, Any]], base: int = DEFAULT_PORT) -> None:
    """Give each flow a port on its server node, counting up per node."""
    used: dict[str, int] = {}
    for f in flows:
        n = used.get(f["server"], 0)
        used[f["server"]] = n + 1
        f["port"] = base + n


def offered_bps(flow: dict[str, Any]) -> float | None:
    """What a flow is asked to carry (both directions for ``bidir``); None when
    it may take whatever the path gives (TCP without a bitrate). UDP without a
    bitrate is iperf3's default 1 Mb/s per stream."""
    rate = bitrate_bps(flow.get("bitrate"))
    if rate is None:
        if flow.get("protocol") != "udp":
            return None
        rate = 1e6
    rate *= int(flow.get("parallel") or 1)
    return rate * (2 if flow.get("direction") == "bidir" else 1)
