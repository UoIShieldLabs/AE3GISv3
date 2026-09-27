"""Topologies made from a few numbers, for scale benchmarks (pure).

``generate(params)`` returns an ordinary topology (the editor's shape, it
validates and deploys like a drawn one) laid out like a small campus:

- one site; a servers subnet ``10.0.0.0/24`` whose gateway router is the core
- client subnets ``10.1.<k>.0/24`` of up to ``hosts_per_subnet`` hosts, each
  with its own gateway router linked to the core (a ``/30`` from
  ``10.255.0.0/24``, so at most 64 client subnets)
- per subnet a distribution switch under the router and access switches of up
  to ``hosts_per_switch`` hosts under it (a router may hold only one interface
  per subnet, so several access switches meet at the distribution switch)
- addresses: router ``.1``, distribution switch ``.2``, hosts and servers
  from ``.10`` (at most 230), access switches from ``.240``

Ids are short and stable (``core``, ``r3``, ``sw3``, ``sw3-2``, ``h3-17``,
``srv-1``) so a scale step's nodes keep their names across steps.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

MAX_CLIENT_SUBNETS = 64  # /30 router links come from 10.255.0.0/24
FIRST_HOST = 10
MAX_PER_SUBNET = 230  # .10 … .239
FIRST_ACCESS_SWITCH = 240
MAX_ACCESS_SWITCHES = 15  # .240 … .254


class GeneratorError(ValueError):
    pass


@dataclass
class GeneratorParams:
    hosts: int
    servers: int = 1
    hosts_per_subnet: int = 200
    hosts_per_switch: int = 48
    host_type: str = "workstation"
    server_type: str = "workstation"
    router_type: str = "router"
    switch_type: str = "switch"
    name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def counts(p: GeneratorParams) -> dict[str, int]:
    """How big the topology will be: subnets, routers, switches, nodes, links."""
    per = min(p.hosts_per_subnet, MAX_PER_SUBNET)
    subnets = math.ceil(p.hosts / per) if p.hosts else 0
    sizes = [min(per, p.hosts - i * per) for i in range(subnets)]
    switches = sum(_switches(n, p.hosts_per_switch) for n in sizes) + _switches(
        p.servers, p.hosts_per_switch
    )
    routers = subnets + 1
    nodes = p.hosts + p.servers + routers + switches
    # host/server links + switch uplinks (one per switch) + router links to the core
    links = p.hosts + p.servers + switches + subnets
    return {
        "subnets": subnets + 1,
        "routers": routers,
        "switches": switches,
        "nodes": nodes,
        "links": links,
    }


def _switches(members: int, per_switch: int) -> int:
    """Switches for ``members`` hosts: one, or a distribution switch + access switches."""
    if members <= 0:
        return 1  # the router still needs its LAN
    access = math.ceil(members / per_switch)
    return 1 if access == 1 else access + 1


def check(p: GeneratorParams) -> None:
    if p.hosts < 0 or p.servers < 0:
        raise GeneratorError("hosts and servers cannot be negative")
    if p.hosts + p.servers == 0:
        raise GeneratorError("A topology needs at least one host or server")
    if not 1 <= p.hosts_per_subnet <= MAX_PER_SUBNET:
        raise GeneratorError(f"hosts_per_subnet must be 1–{MAX_PER_SUBNET}")
    if p.hosts_per_switch < 1:
        raise GeneratorError("hosts_per_switch must be at least 1")
    if p.servers > MAX_PER_SUBNET:
        raise GeneratorError(f"At most {MAX_PER_SUBNET} servers")
    busiest = max(min(p.hosts, p.hosts_per_subnet), p.servers)
    if math.ceil(busiest / p.hosts_per_switch) > MAX_ACCESS_SWITCHES:
        raise GeneratorError(
            f"{busiest} hosts at {p.hosts_per_switch} per switch need more than "
            f"{MAX_ACCESS_SWITCHES} access switches in a subnet; raise hosts_per_switch"
        )
    subnets = math.ceil(p.hosts / p.hosts_per_subnet)
    if subnets > MAX_CLIENT_SUBNETS:
        raise GeneratorError(
            f"{p.hosts} hosts at {p.hosts_per_subnet} per subnet need {subnets} subnets; "
            f"at most {MAX_CLIENT_SUBNETS} (raise hosts_per_subnet, up to {MAX_PER_SUBNET})"
        )


def _lan(
    *,
    subnet_id: str,
    name: str,
    prefix: str,
    router: dict[str, Any],
    switch_prefix: str,
    members: list[tuple[str, str, str]],  # (id, name, type)
    p: GeneratorParams,
    x: float,
    y: float,
) -> dict[str, Any]:
    """One subnet: router, switches, members (hosts or servers)."""
    containers: list[dict[str, Any]] = [router]
    connections: list[dict[str, Any]] = []
    cols = 12
    router["position"] = {"x": 0, "y": 0}
    dist = {
        "id": switch_prefix,
        "name": f"Switch {switch_prefix}",
        "type": p.switch_type,
        "ip": f"{prefix}.2",
        "position": {"x": 0, "y": 120},
    }
    containers.append(dist)
    connections.append(
        {"id": f"c-{dist['id']}-{router['id']}", "from": dist["id"], "to": router["id"]}
    )
    per = p.hosts_per_switch
    groups = [members[i : i + per] for i in range(0, len(members), per)]
    single = len(groups) <= 1
    rows_per_group = math.ceil(per / cols)
    for g, group in enumerate(groups):
        sw = dist
        if not single:
            sw = {
                "id": f"{switch_prefix}-{g + 1}",
                "name": f"Switch {switch_prefix}-{g + 1}",
                "type": p.switch_type,
                "ip": f"{prefix}.{FIRST_ACCESS_SWITCH + g}",
                "position": {"x": g * 160, "y": 240},
            }
            containers.append(sw)
            connections.append(
                {"id": f"c-{sw['id']}-{dist['id']}", "from": sw["id"], "to": dist["id"]}
            )
        for i, (mid, mname, mtype) in enumerate(group):
            containers.append(
                {
                    "id": mid,
                    "name": mname,
                    "type": mtype,
                    "ip": f"{prefix}.{FIRST_HOST + g * per + i}",
                    "position": {
                        "x": (i % cols) * 90,
                        "y": 360 + (g * rows_per_group + i // cols) * 80,
                    },
                }
            )
            connections.append({"id": f"c-{mid}-{sw['id']}", "from": mid, "to": sw["id"]})
    return {
        "id": subnet_id,
        "name": name,
        "cidr": f"{prefix}.0/24",
        "gateway": router["ip"],
        "position": {"x": x, "y": y},
        "containers": containers,
        "connections": connections,
    }


def generate(p: GeneratorParams) -> dict[str, Any]:
    check(p)
    per = p.hosts_per_subnet
    subnets: list[dict[str, Any]] = []
    servers = [(f"srv-{i}", f"Server {i}", p.server_type) for i in range(1, p.servers + 1)]
    subnets.append(
        _lan(
            subnet_id="sub-srv",
            name="Servers",
            prefix="10.0.0",
            router={"id": "core", "name": "Core router", "type": p.router_type, "ip": "10.0.0.1"},
            switch_prefix="swsrv",
            members=servers,
            p=p,
            x=0,
            y=0,
        )
    )
    links: list[dict[str, Any]] = []
    n_subnets = math.ceil(p.hosts / per) if p.hosts else 0
    grid = max(1, math.ceil(math.sqrt(n_subnets + 1)))
    for k in range(n_subnets):
        first = k * per
        size = min(per, p.hosts - first)
        hosts = [(f"h{k}-{i}", f"Host {k}-{i}", p.host_type) for i in range(1, size + 1)]
        slot = k + 1
        subnets.append(
            _lan(
                subnet_id=f"sub-{k}",
                name=f"Clients {k}",
                prefix=f"10.1.{k}",
                router={
                    "id": f"r{k}",
                    "name": f"Router {k}",
                    "type": p.router_type,
                    "ip": f"10.1.{k}.1",
                },
                switch_prefix=f"sw{k}",
                members=hosts,
                p=p,
                x=(slot % grid) * 1400,
                y=(slot // grid) * 1100,
            )
        )
        links.append({"id": f"c-sub-{k}-srv", "from": f"sub-{k}", "to": "sub-srv"})
    return {
        "name": p.name or f"Benchmark {p.hosts} hosts",
        "sites": [
            {
                "id": "site-bench",
                "name": "Benchmark",
                "location": "",
                "position": {"x": 0, "y": 0},
                "subnets": subnets,
                "subnetConnections": links,
            }
        ],
        "siteConnections": [],
        "generator": p.to_dict(),
    }
