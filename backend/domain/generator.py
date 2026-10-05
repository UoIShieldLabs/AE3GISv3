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

Mixed topologies (all optional; without them every host is ``host_type``):

- ``host_mix`` / ``switch_mix``: ``{type, image?, weight}`` entries; the hosts
  (or switches) are split by weight exactly (largest remainder), so every
  scale has the same composition, then placed in a ``seed``-shuffled order
- ``server_mix``: ``{type, image?, count}`` (a fixed number) or
  ``{type, image?, per_hosts}`` (one per that many hosts, at least one); it
  replaces ``servers``
- ``core_type`` / ``core_image``: the core router (e.g. a firewall)

An entry's ``image`` (else the type's default) becomes the container's image.

Random topologies (``random``): pools of ``{type, images}`` entries. Each
node draws an entry with equal odds (so every type is as likely as any other,
however many images it has), then one of its images with equal odds,
independently of the other nodes, so the mix varies from seed to seed:

- ``hosts``: every client host (it replaces ``host_mix``)
- ``switches``: every switch (replaces ``switch_mix``)
- ``routers``: the core and every client subnet's router (replaces ``core_*``;
  a structural router must forward, so leave default-drop firewalls out)

Each pool draws from its own stream of the seed, host after host: a bigger
topology keeps a smaller one's hosts, so a climb's steps stay comparable.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterator
from dataclasses import asdict, dataclass, replace
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
    host_mix: list[dict[str, Any]] | None = None
    server_mix: list[dict[str, Any]] | None = None
    switch_mix: list[dict[str, Any]] | None = None
    core_type: str | None = None
    core_image: str | None = None
    seed: int = 0
    random: dict[str, Any] | None = None  # {hosts, switches?, routers?}: pools of {type, images}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


Kind = tuple[str, str | None]  # (type, image or None for the type's default)


def _apportion(n: int, weights: list[float]) -> list[int]:
    """Split ``n`` by ``weights`` into integers summing to ``n`` (largest
    remainder; ties go to the earlier entry)."""
    total = sum(weights)
    if n <= 0 or total <= 0:
        return [0] * len(weights)
    exact = [n * w / total for w in weights]
    out = [math.floor(x) for x in exact]
    order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - out[i]), i))
    for i in order[: n - sum(out)]:
        out[i] += 1
    return out


def _kinds(
    n: int, mix: list[dict[str, Any]] | None, default: str, rng: random.Random
) -> list[Kind]:
    """``n`` node kinds: all ``default``, or split by the mix and shuffled."""
    if not mix:
        return [(default, None)] * n
    kinds: list[Kind] = []
    for entry, k in zip(mix, _apportion(n, [float(e["weight"]) for e in mix]), strict=True):
        kinds += [(entry["type"], entry.get("image") or None)] * k
    rng.shuffle(kinds)
    return kinds


POOLS = ("hosts", "switches", "routers")


def _pool(p: GeneratorParams, name: str) -> list[dict[str, Any]] | None:
    return (p.random or {}).get(name) or None


def _draw(n: int, pool: list[dict[str, Any]], rng: random.Random) -> list[Kind]:
    """``n`` kinds drawn one by one: an entry with equal odds, then one of its images."""
    out: list[Kind] = []
    for _ in range(n):
        entry = rng.choice(pool)
        out.append((entry["type"], rng.choice(entry["images"])))
    return out


def server_counts(p: GeneratorParams) -> list[int]:
    """How many servers each ``server_mix`` entry adds at this scale."""
    out = []
    for e in p.server_mix or []:
        if e.get("per_hosts"):
            out.append(math.ceil(p.hosts / int(e["per_hosts"])) if p.hosts else 0)
        else:
            out.append(int(e.get("count") or 0))
    return out


def n_servers(p: GeneratorParams) -> int:
    return sum(server_counts(p)) if p.server_mix else p.servers


def counts(p: GeneratorParams) -> dict[str, int]:
    """How big the topology will be: subnets, routers, switches, nodes, links."""
    per = min(p.hosts_per_subnet, MAX_PER_SUBNET)
    servers = n_servers(p)
    subnets = math.ceil(p.hosts / per) if p.hosts else 0
    sizes = [min(per, p.hosts - i * per) for i in range(subnets)]
    switches = sum(_switches(n, p.hosts_per_switch) for n in sizes) + _switches(
        servers, p.hosts_per_switch
    )
    routers = subnets + 1
    nodes = p.hosts + servers + routers + switches
    # host/server links + switch uplinks (one per switch) + router links to the core
    links = p.hosts + servers + switches + subnets
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


def max_hosts(p: GeneratorParams) -> int:
    """The most hosts these params generate (``hosts`` itself is ignored): the
    limits only tighten as hosts grow, so a binary search finds the edge."""
    lo, hi = 0, MAX_CLIENT_SUBNETS * MAX_PER_SUBNET
    while lo < hi:
        mid = (lo + hi + 1) // 2
        try:
            check(replace(p, hosts=mid))
        except GeneratorError:
            hi = mid - 1
        else:
            lo = mid
    return lo


def _check_mix(name: str, mix: list[dict[str, Any]] | None, *, weighted: bool) -> None:
    if mix is None:
        return
    if not mix:
        raise GeneratorError(f"{name} needs at least one entry")
    for e in mix:
        if not isinstance(e, dict) or not str(e.get("type") or "").strip():
            raise GeneratorError(f"every {name} entry needs a type")
        if weighted:
            try:
                ok = float(e.get("weight")) > 0
            except (TypeError, ValueError):
                ok = False
            if not ok:
                raise GeneratorError(f"{name} entry {e['type']!r} needs a positive weight")
        elif (e.get("count") is None) == (not e.get("per_hosts")):
            raise GeneratorError(f"{name} entry {e['type']!r} needs either count or per_hosts")
        elif e.get("per_hosts") is not None and int(e["per_hosts"]) < 1:
            raise GeneratorError(f"{name} entry {e['type']!r}: per_hosts must be at least 1")
        elif e.get("count") is not None and int(e["count"]) < 0:
            raise GeneratorError(f"{name} entry {e['type']!r}: count cannot be negative")


def kinds_used(p: GeneratorParams) -> list[Kind]:
    """Every (type, image) these params can place at any scale, in a stable
    order (an image of None is the type's default). A small step may leave a
    mix entry out, so a benchmark prepares these, not one step's images."""

    def pooled(name: str) -> list[Kind] | None:
        pool = _pool(p, name)
        return [(e["type"], i) for e in pool for i in e["images"]] if pool else None

    kinds: list[Kind] = pooled("routers") or [
        (p.router_type, None),
        (p.core_type or p.router_type, p.core_image),
    ]
    for name, mix, default in (
        ("hosts", p.host_mix, p.host_type),
        ("switches", p.switch_mix, p.switch_type),
        (None, p.server_mix, p.server_type if p.servers else None),
    ):
        if not (mix or default):
            continue
        kinds += (name and pooled(name)) or (
            [(e["type"], e.get("image") or None) for e in mix] if mix else [(default, None)]
        )
    return list(dict.fromkeys(kinds))


def types_used(p: GeneratorParams) -> set[str]:
    """Every node type the topology would contain (to check against a catalog)."""
    return {t for t, _ in kinds_used(p)}


def check_types(p: GeneratorParams, known: set[str]) -> None:
    """Refuse node types missing from ``known`` (the catalog's)."""
    unknown = sorted(types_used(p) - known)
    if unknown:
        raise GeneratorError(f"Unknown node type(s): {', '.join(unknown)}")


def check_catalog(p: GeneratorParams, types: dict[str, dict[str, Any]]) -> None:
    """Refuse what a catalog (``types``: name → spec with ``role`` and
    ``images``) can't deploy: unknown types, pool images a type doesn't list,
    and structural pools of the wrong role (a switch slot needs a switch)."""
    check_types(p, set(types))
    for name, role in (("hosts", None), ("switches", "switch"), ("routers", "router")):
        for e in _pool(p, name) or []:
            spec = types[e["type"]]
            if role and spec.get("role") != role:
                raise GeneratorError(f"random.{name}: {e['type']!r} is not a {role}")
            foreign = [i for i in e["images"] if i not in (spec.get("images") or [])]
            if foreign:
                raise GeneratorError(
                    f"random.{name}: {e['type']!r} has no image {', '.join(foreign)}"
                )


def _check_random(p: GeneratorParams) -> None:
    if p.random is None:
        return
    if not isinstance(p.random, dict) or set(p.random) - set(POOLS):
        raise GeneratorError(f"random takes pools {', '.join(POOLS)}")
    if not _pool(p, "hosts"):
        raise GeneratorError("random needs a hosts pool")
    for name in POOLS:
        for e in _pool(p, name) or []:
            if not isinstance(e, dict) or not str(e.get("type") or "").strip():
                raise GeneratorError(f"every random.{name} entry needs a type")
            images = e.get("images")
            if (
                not isinstance(images, list)
                or not images
                or not all(isinstance(i, str) and i for i in images)
            ):
                raise GeneratorError(f"random.{name} entry {e['type']!r} needs images")
    clashes = {
        "hosts": p.host_mix,
        "switches": p.switch_mix,
        "routers": p.core_type or p.core_image,
    }
    for name, other in clashes.items():
        if _pool(p, name) and other:
            replaced = {"hosts": "host_mix", "switches": "switch_mix", "routers": "core_*"}[name]
            raise GeneratorError(f"random.{name} replaces {replaced}; give one of them")


def check(p: GeneratorParams) -> None:
    _check_random(p)
    _check_mix("host_mix", p.host_mix, weighted=True)
    _check_mix("switch_mix", p.switch_mix, weighted=True)
    _check_mix("server_mix", p.server_mix, weighted=False)
    servers = n_servers(p)
    if p.hosts < 0 or servers < 0:
        raise GeneratorError("hosts and servers cannot be negative")
    if p.hosts + servers == 0:
        raise GeneratorError("A topology needs at least one host or server")
    if not 1 <= p.hosts_per_subnet <= MAX_PER_SUBNET:
        raise GeneratorError(f"hosts_per_subnet must be 1–{MAX_PER_SUBNET}")
    if p.hosts_per_switch < 1:
        raise GeneratorError("hosts_per_switch must be at least 1")
    if servers > MAX_PER_SUBNET:
        raise GeneratorError(f"{servers} servers, at most {MAX_PER_SUBNET} (they share one subnet)")
    busiest = max(min(p.hosts, p.hosts_per_subnet), servers)
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
    members: list[tuple[str, str, Kind]],  # (id, name, kind)
    switch_kinds: Iterator[Kind],
    p: GeneratorParams,
    x: float,
    y: float,
) -> dict[str, Any]:
    """One subnet: router, switches, members (hosts or servers)."""
    containers: list[dict[str, Any]] = [router]
    connections: list[dict[str, Any]] = []
    cols = 12
    router["position"] = {"x": 0, "y": 0}
    dist = _node(
        {
            "id": switch_prefix,
            "name": f"Switch {switch_prefix}",
            "ip": f"{prefix}.2",
            "position": {"x": 0, "y": 120},
        },
        next(switch_kinds),
    )
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
            sw = _node(
                {
                    "id": f"{switch_prefix}-{g + 1}",
                    "name": f"Switch {switch_prefix}-{g + 1}",
                    "ip": f"{prefix}.{FIRST_ACCESS_SWITCH + g}",
                    "position": {"x": g * 160, "y": 240},
                },
                next(switch_kinds),
            )
            containers.append(sw)
            connections.append(
                {"id": f"c-{sw['id']}-{dist['id']}", "from": sw["id"], "to": dist["id"]}
            )
        for i, (mid, mname, kind) in enumerate(group):
            containers.append(
                _node(
                    {
                        "id": mid,
                        "name": mname,
                        "ip": f"{prefix}.{FIRST_HOST + g * per + i}",
                        "position": {
                            "x": (i % cols) * 90,
                            "y": 360 + (g * rows_per_group + i // cols) * 80,
                        },
                    },
                    kind,
                )
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


def _node(fields: dict[str, Any], kind: Kind) -> dict[str, Any]:
    """A container: id/name/ip/position first, then its type (and image)."""
    node = {**fields, "type": kind[0]}
    if kind[1]:
        node["image"] = kind[1]
    return node


def _router(k: int, kind: Kind) -> dict[str, Any]:
    """Client subnet ``k``'s gateway router (fields in their historic order)."""
    router = {"id": f"r{k}", "name": f"Router {k}", "type": kind[0], "ip": f"10.1.{k}.1"}
    if kind[1]:
        router["image"] = kind[1]
    return router


def _server_kinds(p: GeneratorParams, rng: random.Random) -> list[Kind]:
    if not p.server_mix:
        return [(p.server_type, None)] * p.servers
    kinds: list[Kind] = []
    for e, k in zip(p.server_mix, server_counts(p), strict=True):
        kinds += [(e["type"], e.get("image") or None)] * k
    rng.shuffle(kinds)
    return kinds


def generate(p: GeneratorParams) -> dict[str, Any]:
    check(p)
    per = p.hosts_per_subnet
    # One generator, drawn in a fixed order: the same params and seed give
    # the same topology.
    rng = random.Random(p.seed)
    host_kinds = _kinds(p.hosts, p.host_mix, p.host_type, rng)
    server_kinds = _server_kinds(p, rng)
    switch_kinds = iter(_kinds(counts(p)["switches"], p.switch_mix, p.switch_type, rng))
    n_subnets = math.ceil(p.hosts / per) if p.hosts else 0
    router_kinds = iter(
        [(p.core_type or p.router_type, p.core_image)] + [(p.router_type, None)] * n_subnets
    )
    # Random pools draw from streams of their own (string seeds are stable
    # across processes), leaving the mixes' draws above as they were.
    if pool := _pool(p, "hosts"):
        host_kinds = _draw(p.hosts, pool, random.Random(f"{p.seed}:hosts"))
    if pool := _pool(p, "switches"):
        switch_kinds = iter(_draw(counts(p)["switches"], pool, random.Random(f"{p.seed}:switches")))
    if pool := _pool(p, "routers"):
        router_kinds = iter(_draw(n_subnets + 1, pool, random.Random(f"{p.seed}:routers")))
    subnets: list[dict[str, Any]] = []
    servers = [(f"srv-{i}", f"Server {i}", kind) for i, kind in enumerate(server_kinds, start=1)]
    core = _node({"id": "core", "name": "Core router", "ip": "10.0.0.1"}, next(router_kinds))
    subnets.append(
        _lan(
            subnet_id="sub-srv",
            name="Servers",
            prefix="10.0.0",
            router=core,
            switch_prefix="swsrv",
            members=servers,
            switch_kinds=switch_kinds,
            p=p,
            x=0,
            y=0,
        )
    )
    links: list[dict[str, Any]] = []
    grid = max(1, math.ceil(math.sqrt(n_subnets + 1)))
    for k in range(n_subnets):
        first = k * per
        size = min(per, p.hosts - first)
        hosts = [
            (f"h{k}-{i}", f"Host {k}-{i}", host_kinds[first + i - 1]) for i in range(1, size + 1)
        ]
        slot = k + 1
        subnets.append(
            _lan(
                subnet_id=f"sub-{k}",
                name=f"Clients {k}",
                prefix=f"10.1.{k}",
                router=_router(k, next(router_kinds)),
                switch_prefix=f"sw{k}",
                members=hosts,
                switch_kinds=switch_kinds,
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
