"""Typed, read-only views over the opaque topology dict.

The backend never reshapes ``Topology.data``; these helpers are the one place
that knows where things live so services and validation don't re-implement
the same loops.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

import catalog

Json = dict[str, Any]
ConnectionKind = Literal["site", "subnet", "container"]


def _dicts(value: Any) -> list[Json]:
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def sites(data: Json) -> list[Json]:
    return _dicts((data or {}).get("sites"))


def subnets(site: Json) -> list[Json]:
    return _dicts(site.get("subnets"))


def containers(subnet: Json) -> list[Json]:
    return _dicts(subnet.get("containers"))


def iter_subnets(data: Json) -> Iterator[tuple[Json, Json]]:
    for site in sites(data):
        for subnet in subnets(site):
            yield site, subnet


def iter_containers(data: Json) -> Iterator[tuple[Json, Json, Json]]:
    for site, subnet in iter_subnets(data):
        for c in containers(subnet):
            yield site, subnet, c


def find_container(data: Json, container_id: str) -> Json | None:
    for _, _, c in iter_containers(data):
        if c.get("id") == container_id:
            return c
    return None


def find_subnet(data: Json, subnet_id: str) -> tuple[Json, Json] | None:
    for site, subnet in iter_subnets(data):
        if subnet.get("id") == subnet_id:
            return site, subnet
    return None


def find_site(data: Json, site_id: str) -> Json | None:
    for site in sites(data):
        if site.get("id") == site_id:
            return site
    return None


def is_router(container: Json) -> bool:
    return catalog.role_for(str(container.get("type", ""))) == "router"


def gateway_of(subnet: Json) -> Json | None:
    """The router whose IP is the subnet gateway, else the first router."""
    routers = [c for c in containers(subnet) if is_router(c)]
    gw_ip = subnet.get("gateway")
    for r in routers:
        if gw_ip and r.get("ip") == gw_ip:
            return r
    return routers[0] if routers else None


@dataclass
class ConnectionRef:
    kind: ConnectionKind
    conn: Json
    site: Json | None = None
    subnet: Json | None = None
    path: str = ""


def iter_connections(data: Json) -> Iterator[ConnectionRef]:
    for si, site in enumerate(sites(data)):
        for ni, subnet in enumerate(subnets(site)):
            for ci, conn in enumerate(_dicts(subnet.get("connections"))):
                yield ConnectionRef(
                    "container", conn, site, subnet, f"sites[{si}].subnets[{ni}].connections[{ci}]"
                )
        for ci, conn in enumerate(_dicts(site.get("subnetConnections"))):
            yield ConnectionRef("subnet", conn, site, None, f"sites[{si}].subnetConnections[{ci}]")
    for ci, conn in enumerate(_dicts((data or {}).get("siteConnections"))):
        yield ConnectionRef("site", conn, None, None, f"siteConnections[{ci}]")


def topology_name(data: Json, fallback: str = "topology") -> str:
    name = (data or {}).get("name")
    return name.strip() if isinstance(name, str) and name.strip() else fallback


def counts(data: Json) -> dict[str, int]:
    n_subnets = sum(len(subnets(s)) for s in sites(data))
    n_containers = sum(1 for _ in iter_containers(data))
    return {"sites": len(sites(data)), "subnets": n_subnets, "containers": n_containers}


def images_in(data: Json) -> list[str]:
    """Every image the topology would deploy (catalog-resolved), de-duplicated."""
    seen: dict[str, None] = {}
    for _, _, c in iter_containers(data):
        img = catalog.resolve_image(str(c.get("type", "")), c.get("image"))
        if img:
            seen.setdefault(img, None)
    return list(seen)
