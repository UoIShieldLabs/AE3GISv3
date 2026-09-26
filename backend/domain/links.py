"""Resolve capture targets against a deployed lab's links (pure).

``links`` is ``LabPlan.links()`` as saved in ``EngineState.links`` at deploy
time: one entry per collision domain with its ``connection_id``, resolved
``from``/``to`` node ids and endpoints (node id + interface name). Every
connection is its own two-endpoint collision domain, so capturing on either
endpoint's interface sees the whole link.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


class TargetError(ValueError):
    """The target does not exist in the deployed lab; ``code`` is the API error code."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Endpoint:
    node_id: str
    machine: str
    interface: str
    collision_domain: str
    connection_id: str | None
    peer_node_id: str | None
    ip: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _endpoint(link: dict[str, Any], ep: dict[str, Any]) -> Endpoint:
    peers = [e["node"] for e in link.get("endpoints", []) if e is not ep]
    return Endpoint(
        node_id=ep["node"],
        machine=ep.get("machine_name") or ep["node"],
        interface=ep["interface"],
        collision_domain=link["collision_domain"],
        connection_id=link.get("connection_id"),
        peer_node_id=peers[0] if peers else None,
        ip=ep.get("ip"),
    )


def interfaces_by_node(links: list[dict[str, Any]]) -> dict[str, list[Endpoint]]:
    """Every deployed interface, grouped by node and sorted by name."""
    out: dict[str, list[Endpoint]] = {}
    for link in links:
        for ep in link.get("endpoints", []):
            out.setdefault(ep["node"], []).append(_endpoint(link, ep))
    for eps in out.values():
        eps.sort(key=lambda e: (len(e.interface), e.interface))
    return out


def endpoints_for_connection(links: list[dict[str, Any]], connection_id: str) -> list[Endpoint]:
    """The endpoints of a connection, its ``from`` side first."""
    for link in links:
        if link.get("connection_id") != connection_id:
            continue
        eps = [_endpoint(link, ep) for ep in link.get("endpoints", [])]
        first = link.get("from")
        return sorted(eps, key=lambda e: e.node_id != first)
    return []


def resolve_target(links: list[dict[str, Any]], target: dict[str, Any]) -> Endpoint:
    """A capture target (a link or a node interface) → the interface to capture on.

    Link targets default to the connection's ``from`` end; either end sees the
    whole two-endpoint segment.
    """
    kind = target.get("kind")
    if kind == "link":
        cid = target.get("connection_id") or ""
        eps = endpoints_for_connection(links, cid)
        if not eps:
            raise TargetError(
                "That connection is not part of the deployed lab (save and redeploy?)",
                code="link_not_deployed",
            )
        side = target.get("endpoint") or "from"
        return eps[1] if side == "to" and len(eps) > 1 else eps[0]
    if kind == "interface":
        node_id = target.get("node_id") or ""
        iface = target.get("interface") or ""
        for ep in interfaces_by_node(links).get(node_id, []):
            if ep.interface == iface:
                return ep
        raise TargetError(
            f"{node_id} has no deployed interface {iface!r}", code="interface_not_deployed"
        )
    raise TargetError(f"Unknown target kind {kind!r}", code="bad_target")
