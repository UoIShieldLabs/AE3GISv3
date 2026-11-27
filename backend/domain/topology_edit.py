"""Edit operations over the opaque topology dict (the agent's ``edit_topology``).

A pure function: ``apply_ops(data, ops)`` returns a new dict and what it created,
never touching the input. Each operation mirrors what the editor's store does
for the same gesture (``frontend/src/store/slices/topologySlice.ts``), so a
topology edited here loads in the editor exactly like one edited by hand:

- ``add_subnet`` adds its gateway router and switch, linked (the editor's
  ``autoInfra``), and sets the subnet ``gateway``;
- ``add_device`` takes the next free address in its subnet (legs included);
- ``connect`` follows ``addConnection``: device ↔ device in a subnet, router ↔
  router across subnets or sites, subnet ↔ subnet / site ↔ site through the
  gateway routers (created when missing);
- ``remove`` cascades like ``deleteItems`` (links, legs, mirrors, scenario steps).

New entities get no ``position``: the editor's ``normalizeTopology`` slots them
in (a whole-scope layout when none of a scope's children are placed).

Tutorial and scenario operations edit ``tutorials`` / ``scenarios`` the same
way their panels do. Fields this module doesn't know about pass through.
"""

from __future__ import annotations

import copy
import ipaddress
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import catalog

Json = dict[str, Any]

# Keys an ``update`` may not set: identity and the child collections (edited
# through their own operations so ids and cascades stay consistent).
PROTECTED_KEYS = frozenset(
    {
        "id",
        "subnets",
        "containers",
        "connections",
        "subnetConnections",
        "siteConnections",
        "phases",
        "executions",
        "cells",
    }
)


class EditError(ValueError):
    """An operation that cannot apply; ``index`` is its position in the batch."""

    def __init__(self, message: str, *, index: int | None = None, op: str | None = None):
        super().__init__(message)
        self.index = index
        self.op = op

    def __str__(self) -> str:  # "op 2 (connect): ..."
        base = super().__str__()
        if self.index is None:
            return base
        return f"op {self.index} ({self.op}): {base}"


@dataclass
class EditResult:
    data: Json
    # One entry per created entity: {"op": index, "kind": ..., "id": ..., "name": ...}.
    created: list[Json] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: bool = False


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ── small readers (the shape the editor keeps after normalizeTopology) ──


def _list(owner: Json, key: str) -> list[Any]:
    value = owner.get(key)
    if not isinstance(value, list):
        value = []
        owner[key] = value
    return value


def _dicts(owner: Json, key: str) -> list[Json]:
    return [x for x in _list(owner, key) if isinstance(x, dict)]


def _role(type_name: str) -> str:
    return catalog.role_for(type_name)


def _label(type_name: str) -> str:
    spec = catalog.get_type(type_name) or {}
    return str(spec.get("displayName") or type_name or "Node")


@dataclass
class Hit:
    kind: str  # site | subnet | container
    site: Json
    subnet: Json | None = None
    container: Json | None = None


def locate(data: Json, entity_id: str) -> Hit | None:
    for site in _dicts(data, "sites"):
        if site.get("id") == entity_id:
            return Hit("site", site)
        for subnet in _dicts(site, "subnets"):
            if subnet.get("id") == entity_id:
                return Hit("subnet", site, subnet)
            for c in _dicts(subnet, "containers"):
                if c.get("id") == entity_id:
                    return Hit("container", site, subnet, c)
    return None


def _connection_lists(data: Json) -> list[list[Any]]:
    lists = [_list(data, "siteConnections")]
    for site in _dicts(data, "sites"):
        lists.append(_list(site, "subnetConnections"))
        for subnet in _dicts(site, "subnets"):
            lists.append(_list(subnet, "connections"))
    return lists


def find_connection(data: Json, conn_id: str) -> Json | None:
    for conns in _connection_lists(data):
        for conn in conns:
            if isinstance(conn, dict) and conn.get("id") == conn_id:
                return conn
    return None


def _has_connection(conns: list[Any], a: str, b: str) -> bool:
    return any(
        isinstance(c, dict)
        and ((c.get("from") == a and c.get("to") == b) or (c.get("from") == b and c.get("to") == a))
        for c in conns
    )


def gateway_of(subnet: Json) -> Json | None:
    """The first router-role device (the editor's ``gatewayOf``)."""
    for c in _dicts(subnet, "containers"):
        if _role(str(c.get("type", ""))) == "router":
            return c
    return None


def site_router(site: Json) -> Json | None:
    for subnet in _dicts(site, "subnets"):
        r = gateway_of(subnet)
        if r is not None:
            return r
    return None


def used_ips(data: Json, subnet_id: str) -> set[str]:
    """Home addresses in the subnet plus every leg into it (``usedIpsInSubnet``)."""
    ips: set[str] = set()
    for site in _dicts(data, "sites"):
        for subnet in _dicts(site, "subnets"):
            for c in _dicts(subnet, "containers"):
                if subnet.get("id") == subnet_id and c.get("ip"):
                    ips.add(str(c["ip"]))
                for leg in _dicts(c, "interfaces"):
                    if leg.get("subnetId") == subnet_id and leg.get("ip"):
                        ips.add(str(leg["ip"]))
    return ips


def next_ip(cidr: str, taken: set[str]) -> str:
    """The first free host address of ``cidr`` ('' when unparsable or full)."""
    try:
        net = ipaddress.ip_network(str(cidr).strip(), strict=False)
    except ValueError:
        return ""
    if net.version != 4:
        return ""
    for host in net.hosts() if net.num_addresses > 2 else net:
        if str(host) not in taken:
            return str(host)
    return ""


def next_name(existing: list[str], base: str) -> str:
    """``nextName``: "Workstation 1", then "Workstation 2", ..."""
    b = (base or "Node").strip()
    pattern = re.compile(rf"^{re.escape(b)}\s*(\d+)$", re.I)
    top = 0
    bare = False
    for n in existing:
        t = n.strip()
        if t.lower() == b.lower():
            bare = True
        m = pattern.match(t)
        if m:
            top = max(top, int(m.group(1)))
    return f"{b} 1" if top == 0 and not bare else f"{b} {top + 1}"


def _ensure_router(data: Json, subnet: Json) -> str:
    """The subnet's gateway router, created (and wired to its switch) when missing."""
    existing = gateway_of(subnet)
    if existing is not None:
        return str(existing["id"])
    ip = next_ip(str(subnet.get("cidr", "")), used_ips(data, str(subnet["id"])))
    rid = new_id("node")
    containers = _list(subnet, "containers")
    containers.append(
        {"id": rid, "name": f"{subnet.get('name') or 'Subnet'} Router", "type": "router", "ip": ip}
    )
    subnet["gateway"] = ip
    sw = next(
        (c for c in _dicts(subnet, "containers") if _role(str(c.get("type"))) == "switch"), None
    )
    conns = _list(subnet, "connections")
    if sw is not None and not _has_connection(conns, sw["id"], rid):
        conns.append({"id": new_id("c"), "from": sw["id"], "to": rid})
    return rid


# ── operations ──


class _Editor:
    def __init__(self, data: Json):
        self.data = data
        self.result = EditResult(data=data)
        self.index = 0

    def created(self, kind: str, entity: Json, **extra: Any) -> None:
        self.result.created.append(
            {
                "op": self.index,
                "kind": kind,
                "id": entity["id"],
                "name": entity.get("name"),
                **extra,
            }
        )
        self.result.changed = True

    # topology meta
    def set_meta(self, op: Json) -> None:
        for key in ("name", "description"):
            if key in op and op[key] is not None:
                self.data[key] = str(op[key])
                self.result.changed = True

    # sites
    def add_site(self, op: Json) -> None:
        name = str(op.get("name") or "").strip() or next_name(
            [str(s.get("name", "")) for s in _dicts(self.data, "sites")], "Site"
        )
        site = {
            "id": new_id("site"),
            "name": name,
            "location": str(op.get("location") or ""),
            "subnets": [],
            "subnetConnections": [],
        }
        _list(self.data, "sites").append(site)
        self.created("site", site)

    # subnets
    def add_subnet(self, op: Json) -> None:
        hit = self._need(op.get("site"), "site")
        cidr = str(op.get("cidr") or "").strip()
        try:
            ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            raise EditError(f"'{cidr}' is not a valid CIDR (e.g. 10.0.1.0/24)") from None
        name = str(op.get("name") or "").strip() or next_name(
            [str(s.get("name", "")) for s in _dicts(hit.site, "subnets")], "Subnet"
        )
        subnet: Json = {
            "id": new_id("subnet"),
            "name": name,
            "cidr": cidr,
            "containers": [],
            "connections": [],
        }
        if op.get("purdue_level") is not None:
            subnet["purdueLevel"] = op["purdue_level"]
        extra: dict[str, Any] = {}
        if op.get("infra", True):
            router_ip = next_ip(cidr, set())
            switch_ip = next_ip(cidr, {router_ip} if router_ip else set())
            rid, sid = new_id("node"), new_id("node")
            subnet["gateway"] = router_ip
            subnet["containers"] = [
                {"id": rid, "name": f"{name} Router", "type": "router", "ip": router_ip},
                {"id": sid, "name": f"{name} Switch", "type": "switch", "ip": switch_ip},
            ]
            subnet["connections"] = [{"id": new_id("c"), "from": sid, "to": rid}]
            extra = {"router": rid, "switch": sid}
        _list(hit.site, "subnets").append(subnet)
        self.created("subnet", subnet, **extra)

    # devices
    def add_device(self, op: Json) -> None:
        hit = self._need(op.get("subnet"), "subnet")
        subnet = hit.subnet
        assert subnet is not None
        type_name = str(op.get("type") or "").strip()
        if catalog.get_type(type_name) is None:
            known = ", ".join(sorted(catalog.node_types()))
            raise EditError(f"unknown device type '{type_name}'; known types: {known}")
        ip = str(op.get("ip") or "").strip()
        taken = used_ips(self.data, str(subnet["id"]))
        if ip and ip in taken:
            raise EditError(f"{ip} is already used in subnet {subnet.get('name')}")
        if not ip:
            ip = next_ip(str(subnet.get("cidr", "")), taken)
        name = str(op.get("name") or "").strip() or next_name(
            [str(c.get("name", "")) for c in _dicts(subnet, "containers")], _label(type_name)
        )
        device: Json = {"id": new_id("node"), "name": name, "type": type_name, "ip": ip}
        if op.get("image"):
            device["image"] = str(op["image"])
        if op.get("env"):
            device["env"] = {str(k): str(v) for k, v in dict(op["env"]).items()}
        if op.get("web_ui_port"):
            device["webUiPort"] = int(op["web_ui_port"])
        role = _role(type_name)
        containers = _list(subnet, "containers")
        # Link it to its LAN: the switch (a router or host), or the router (a
        # new switch), unless told otherwise. ``connect_to: null`` = no link.
        target: str | None = None
        if "connect_to" not in op or op.get("connect_to") == "auto":
            peers = _dicts(subnet, "containers")
            if role == "switch":
                gw = gateway_of(subnet)
                target = gw["id"] if gw else None
            else:
                sw = next((c for c in peers if _role(str(c.get("type"))) == "switch"), None)
                target = sw["id"] if sw else None
        elif op.get("connect_to"):
            other = locate(self.data, str(op["connect_to"]))
            if other is None or other.kind != "container" or other.subnet is not subnet:
                raise EditError("connect_to must be a device in the same subnet")
            target = str(op["connect_to"])
        containers.append(device)
        if role == "router" and not subnet.get("gateway"):
            subnet["gateway"] = ip
        if target:
            _list(subnet, "connections").append(
                {"id": new_id("c"), "from": target, "to": device["id"]}
            )
        self.created("device", device, ip=ip)

    def add_interface(self, op: Json) -> None:
        dev = self._need(op.get("device"), "container")
        sub = self._need(op.get("subnet"), "subnet")
        assert dev.container is not None and sub.subnet is not None
        if _role(str(dev.container.get("type"))) == "switch":
            raise EditError("a switch cannot take an interface leg (it would bridge two subnets)")
        if dev.subnet is sub.subnet:
            raise EditError("the device already lives in that subnet")
        legs = _list(dev.container, "interfaces")
        if any(isinstance(leg, dict) and leg.get("subnetId") == sub.subnet["id"] for leg in legs):
            raise EditError("the device already has a leg in that subnet")
        taken = used_ips(self.data, str(sub.subnet["id"]))
        ip = str(op.get("ip") or "").strip() or next_ip(str(sub.subnet.get("cidr", "")), taken)
        if ip in taken:
            raise EditError(f"{ip} is already used in subnet {sub.subnet.get('name')}")
        legs.append({"subnetId": sub.subnet["id"], "ip": ip})
        self.result.changed = True

    # links
    def connect(self, op: Json) -> None:
        a_id, b_id = str(op.get("a") or ""), str(op.get("b") or "")
        if not a_id or not b_id or a_id == b_id:
            raise EditError("connect needs two different ids, a and b")
        a, b = locate(self.data, a_id), locate(self.data, b_id)
        if a is None or b is None:
            raise EditError(f"no site, subnet or device with id '{b_id if a else a_id}'")
        cid = new_id("c")
        conn: Json = {"id": cid}
        if op.get("label"):
            conn["label"] = str(op["label"])
        data = self.data
        target: list[Any]
        if a.kind == "site" and b.kind == "site":
            ra, rb = site_router(a.site), site_router(b.site)
            target = _list(data, "siteConnections")
            if _has_connection(target, a_id, b_id):
                raise EditError("those sites are already connected")
            conn = {**conn, "from": a_id, "to": b_id}
            if ra:
                conn["fromContainer"] = ra["id"]
            if rb:
                conn["toContainer"] = rb["id"]
        elif a.kind == "subnet" and b.kind == "subnet":
            assert a.subnet is not None and b.subnet is not None
            fc, tc = _ensure_router(data, a.subnet), _ensure_router(data, b.subnet)
            if a.site is b.site:
                target = _list(a.site, "subnetConnections")
                ends = (a_id, b_id)
            else:
                target = _list(data, "siteConnections")
                ends = (str(a.site["id"]), str(b.site["id"]))
            if _has_connection(target, *ends):
                raise EditError("those are already connected")
            conn = {**conn, "from": ends[0], "to": ends[1], "fromContainer": fc, "toContainer": tc}
        elif a.kind == "container" and b.kind == "container":
            assert a.subnet is not None and b.subnet is not None
            if a.subnet is b.subnet:
                target = _list(a.subnet, "connections")
                if _has_connection(target, a_id, b_id):
                    raise EditError("those devices are already connected")
                conn = {**conn, "from": a_id, "to": b_id}
            else:
                assert a.container is not None and b.container is not None
                both_routers = all(
                    _role(str(x.get("type"))) == "router" for x in (a.container, b.container)
                )
                if not both_routers:
                    raise EditError(
                        "only routers link across subnets or sites (connect the subnets instead)"
                    )
                if a.site is b.site:
                    target = _list(a.site, "subnetConnections")
                    ends = (str(a.subnet["id"]), str(b.subnet["id"]))
                else:
                    target = _list(data, "siteConnections")
                    ends = (str(a.site["id"]), str(b.site["id"]))
                if _has_connection(target, *ends):
                    raise EditError("those are already connected")
                conn = {
                    **conn,
                    "from": ends[0],
                    "to": ends[1],
                    "fromContainer": a_id,
                    "toContainer": b_id,
                }
        elif {a.kind, b.kind} == {"subnet", "container"}:
            sub, con = (a, b) if a.kind == "subnet" else (b, a)
            assert sub.subnet is not None and con.subnet is not None and con.container is not None
            if sub.site is not con.site or sub.subnet is con.subnet:
                raise EditError("a subnet links to a router of another subnet in the same site")
            if _role(str(con.container.get("type"))) != "router":
                raise EditError("a subnet links to a router, not to another device type")
            target = _list(sub.site, "subnetConnections")
            if _has_connection(target, str(sub.subnet["id"]), str(con.subnet["id"])):
                raise EditError("those subnets are already connected")
            sub_router = _ensure_router(data, sub.subnet)
            from_sub = a.kind == "subnet"
            conn = {
                **conn,
                "from": sub.subnet["id"] if from_sub else con.subnet["id"],
                "to": con.subnet["id"] if from_sub else sub.subnet["id"],
                "fromContainer": sub_router if from_sub else con.container["id"],
                "toContainer": con.container["id"] if from_sub else sub_router,
            }
        else:
            raise EditError(f"cannot connect a {a.kind} to a {b.kind}")
        target.append(conn)
        self.result.created.append({"op": self.index, "kind": "connection", "id": cid})
        self.result.changed = True

    # generic update
    def update(self, op: Json) -> None:
        entity_id = str(op.get("id") or "")
        obj = self._object(entity_id)
        sets = op.get("set") or {}
        if not isinstance(sets, dict):
            raise EditError("set must be an object of field → value")
        bad = sorted(set(sets) & PROTECTED_KEYS)
        if bad:
            raise EditError(
                f"cannot set {', '.join(bad)} with update; use the dedicated operations"
            )
        for key, value in sets.items():
            obj[key] = value
        for key in op.get("unset") or []:
            if key in PROTECTED_KEYS:
                raise EditError(f"cannot unset {key}")
            obj.pop(str(key), None)
        if sets or op.get("unset"):
            self.result.changed = True

    # removal
    def remove(self, op: Json) -> None:
        ids = [str(i) for i in op.get("ids") or []]
        if not ids:
            raise EditError("remove needs ids")
        node_ids: list[str] = []
        conn_ids: list[str] = []
        other: list[str] = []
        for i in ids:
            if locate(self.data, i) is not None:
                node_ids.append(i)
            elif find_connection(self.data, i) is not None:
                conn_ids.append(i)
            elif self._find_teaching(i) is not None:
                other.append(i)
            else:
                raise EditError(f"nothing with id '{i}'")
        if conn_ids:
            drop = set(conn_ids)
            for conns in _connection_lists(self.data):
                conns[:] = [c for c in conns if not (isinstance(c, dict) and c.get("id") in drop)]
        if node_ids:
            _drop_nodes(self.data, node_ids)
        for i in other:
            self._remove_teaching(i)
        self.result.removed.extend(ids)
        self.result.changed = True

    # scenarios (the classroom step-through)
    def add_scenario(self, op: Json) -> None:
        scenarios = _list(self.data, "scenarios")
        sc = {
            "id": new_id("scenario"),
            "name": str(op.get("name") or f"Scenario {len(scenarios) + 1}"),
            "phases": [],
        }
        if op.get("description"):
            sc["description"] = str(op["description"])
        scenarios.append(sc)
        self.created("scenario", sc)

    def add_phase(self, op: Json) -> None:
        sc = self._find_in("scenarios", op.get("scenario"), "scenario")
        phases = _list(sc, "phases")
        ph = {
            "id": new_id("phase"),
            "name": str(op.get("name") or f"Phase {len(phases) + 1}"),
            "executions": [],
        }
        if op.get("description"):
            ph["description"] = str(op["description"])
        phases.append(ph)
        self.created("phase", ph)

    def add_step(self, op: Json) -> None:
        phase = self._phase(op.get("phase"))
        node = self._need(op.get("device"), "container")
        assert node.container is not None
        step: Json = {"containerId": node.container["id"], "script": str(op.get("script") or "")}
        if not step["script"].strip():
            raise EditError("a step needs a script (the command to run)")
        if op.get("args"):
            step["args"] = [str(a) for a in op["args"]]
        _list(phase, "executions").append(step)
        self.result.changed = True

    def remove_step(self, op: Json) -> None:
        phase = self._phase(op.get("phase"))
        steps = _list(phase, "executions")
        idx = op.get("index")
        if not isinstance(idx, int) or not 0 <= idx < len(steps):
            raise EditError(f"step index must be 0..{len(steps) - 1}")
        steps.pop(idx)
        self.result.changed = True

    # tutorials
    def add_tutorial(self, op: Json) -> None:
        tutorials = _list(self.data, "tutorials")
        tut = {
            "id": new_id("tutorial"),
            "title": str(op.get("title") or f"Tutorial {len(tutorials) + 1}"),
            "cells": [],
        }
        tutorials.append(tut)
        self.created("tutorial", tut, name=tut["title"])

    def add_cell(self, op: Json) -> None:
        tut = self._find_in("tutorials", op.get("tutorial"), "tutorial")
        cells = _list(tut, "cells")
        kind = op.get("kind")
        if kind == "markdown":
            cell: Json = {
                "id": new_id("cell"),
                "kind": "markdown",
                "source": str(op.get("source") or ""),
            }
        elif kind == "command":
            node = self._need(op.get("device"), "container")
            assert node.container is not None
            cell = {
                "id": new_id("cell"),
                "kind": "command",
                "containerId": node.container["id"],
                "command": str(op.get("command") or ""),
            }
        else:
            raise EditError("a cell's kind is markdown or command")
        after = op.get("after")
        if after:
            pos = next(
                (i for i, c in enumerate(cells) if isinstance(c, dict) and c.get("id") == after),
                None,
            )
            if pos is None:
                raise EditError(f"no cell '{after}' in that tutorial")
            cells.insert(pos + 1, cell)
        else:
            cells.append(cell)
        self.created("cell", cell)

    def set_tutorial_setup(self, op: Json) -> None:
        tut = self._find_in("tutorials", op.get("tutorial"), "tutorial")
        steps = []
        for s in op.get("steps") or []:
            node = self._need(s.get("device"), "container")
            assert node.container is not None
            steps.append(
                {
                    "id": new_id("setup"),
                    "containerId": node.container["id"],
                    "command": str(s.get("command") or ""),
                }
            )
        setup = tut.get("setup") if isinstance(tut.get("setup"), dict) else {}
        tut["setup"] = {**setup, "steps": steps, "traffic": setup.get("traffic", [])}
        self.result.changed = True

    # helpers
    def _need(self, entity_id: Any, kind: str) -> Hit:
        hit = locate(self.data, str(entity_id or ""))
        if hit is None or hit.kind != kind:
            word = "device" if kind == "container" else kind
            raise EditError(f"no {word} with id '{entity_id}'")
        return hit

    def _object(self, entity_id: str) -> Json:
        hit = locate(self.data, entity_id)
        if hit is not None:
            return hit.container or hit.subnet or hit.site  # type: ignore[return-value]
        conn = find_connection(self.data, entity_id)
        if conn is not None:
            return conn
        teaching = self._find_teaching(entity_id)
        if teaching is not None:
            return teaching
        raise EditError(f"nothing with id '{entity_id}'")

    def _find_in(self, key: str, entity_id: Any, word: str) -> Json:
        for item in _dicts(self.data, key):
            if item.get("id") == entity_id:
                return item
        raise EditError(f"no {word} with id '{entity_id}'")

    def _phase(self, phase_id: Any) -> Json:
        for sc in _dicts(self.data, "scenarios"):
            for ph in _dicts(sc, "phases"):
                if ph.get("id") == phase_id:
                    return ph
        raise EditError(f"no phase with id '{phase_id}'")

    def _find_teaching(self, entity_id: str) -> Json | None:
        for sc in _dicts(self.data, "scenarios"):
            if sc.get("id") == entity_id:
                return sc
            for ph in _dicts(sc, "phases"):
                if ph.get("id") == entity_id:
                    return ph
        for tut in _dicts(self.data, "tutorials"):
            if tut.get("id") == entity_id:
                return tut
            for cell in _dicts(tut, "cells"):
                if cell.get("id") == entity_id:
                    return cell
        return None

    def _remove_teaching(self, entity_id: str) -> None:
        def keep(x: Any) -> bool:
            return not (isinstance(x, dict) and x.get("id") == entity_id)

        scenarios = _list(self.data, "scenarios") if "scenarios" in self.data else []
        scenarios[:] = [s for s in scenarios if keep(s)]
        for sc in _dicts(self.data, "scenarios"):
            phases = _list(sc, "phases")
            phases[:] = [p for p in phases if keep(p)]
        tutorials = _list(self.data, "tutorials") if "tutorials" in self.data else []
        tutorials[:] = [t for t in tutorials if keep(t)]
        for tut in _dicts(self.data, "tutorials"):
            cells = _list(tut, "cells")
            cells[:] = [c for c in cells if keep(c)]


def _drop_nodes(data: Json, ids: list[str]) -> None:
    """The editor's ``dropNodes``: remove sites / subnets / devices and everything
    that pointed at them."""
    drop = set(ids)

    def touches(c: Any) -> bool:
        return isinstance(c, dict) and (c.get("from") in drop or c.get("to") in drop)

    def scrub(c: Any) -> None:
        if not isinstance(c, dict):
            return
        if c.get("fromContainer") in drop:
            c.pop("fromContainer", None)
        if c.get("toContainer") in drop:
            c.pop("toContainer", None)

    sites = _list(data, "sites")
    sites[:] = [s for s in sites if not (isinstance(s, dict) and s.get("id") in drop)]
    site_conns = _list(data, "siteConnections")
    site_conns[:] = [c for c in site_conns if not touches(c)]
    for site in _dicts(data, "sites"):
        subnets = _list(site, "subnets")
        subnets[:] = [s for s in subnets if not (isinstance(s, dict) and s.get("id") in drop)]
        sub_conns = _list(site, "subnetConnections")
        sub_conns[:] = [c for c in sub_conns if not touches(c)]
        for subnet in _dicts(site, "subnets"):
            containers = _list(subnet, "containers")
            containers[:] = [
                c for c in containers if not (isinstance(c, dict) and c.get("id") in drop)
            ]
            conns = _list(subnet, "connections")
            conns[:] = [c for c in conns if not touches(c)]
            gw = subnet.get("gateway")
            if gw and not any(c.get("ip") == gw for c in _dicts(subnet, "containers")):
                r = gateway_of(subnet)
                if r is not None:
                    subnet["gateway"] = r.get("ip", "")
                else:
                    subnet.pop("gateway", None)
        for c in sub_conns:
            scrub(c)
    for c in site_conns:
        scrub(c)

    live_subnets: set[str] = set()
    live_nodes: set[str] = set()
    for site in _dicts(data, "sites"):
        for subnet in _dicts(site, "subnets"):
            live_subnets.add(str(subnet.get("id")))
            for c in _dicts(subnet, "containers"):
                live_nodes.add(str(c.get("id")))
    for site in _dicts(data, "sites"):
        for subnet in _dicts(site, "subnets"):
            for c in _dicts(subnet, "containers"):
                if isinstance(c.get("interfaces"), list):
                    c["interfaces"] = [
                        leg
                        for leg in c["interfaces"]
                        if isinstance(leg, dict) and leg.get("subnetId") in live_subnets
                    ]
                    if not c["interfaces"]:
                        del c["interfaces"]
                if c.get("mirrorTo") and c["mirrorTo"] not in live_nodes:
                    del c["mirrorTo"]
    for sc in [s for s in data.get("scenarios") or [] if isinstance(s, dict)]:
        for ph in [p for p in sc.get("phases") or [] if isinstance(p, dict)]:
            ph["executions"] = [
                e
                for e in ph.get("executions") or []
                if isinstance(e, dict) and e.get("containerId") in live_nodes
            ]


OPERATIONS: dict[str, Callable[[_Editor, Json], None]] = {
    "set_meta": _Editor.set_meta,
    "add_site": _Editor.add_site,
    "add_subnet": _Editor.add_subnet,
    "add_device": _Editor.add_device,
    "add_interface": _Editor.add_interface,
    "connect": _Editor.connect,
    "update": _Editor.update,
    "remove": _Editor.remove,
    "add_scenario": _Editor.add_scenario,
    "add_phase": _Editor.add_phase,
    "add_step": _Editor.add_step,
    "remove_step": _Editor.remove_step,
    "add_tutorial": _Editor.add_tutorial,
    "add_cell": _Editor.add_cell,
    "set_tutorial_setup": _Editor.set_tutorial_setup,
}

# Ids an operation may name before they exist: "$0" is the first id created by
# operation 0, "$0.router" / "$0.switch" the infrastructure of an add_subnet.
_REF = re.compile(r"^\$(\d+)(?:\.(router|switch))?$")


def _resolve_refs(value: Any, created: list[Json]) -> Any:
    if isinstance(value, str):
        m = _REF.match(value)
        if not m:
            return value
        idx, part = int(m.group(1)), m.group(2)
        entry = next((c for c in created if c["op"] == idx), None)
        if entry is None:
            raise EditError(f"'{value}' refers to operation {idx}, which created nothing")
        if part:
            if part not in entry:
                raise EditError(f"operation {idx} created no {part}")
            return entry[part]
        return entry["id"]
    if isinstance(value, list):
        return [_resolve_refs(v, created) for v in value]
    if isinstance(value, dict):
        return {k: _resolve_refs(v, created) for k, v in value.items()}
    return value


def apply_ops(data: Json, ops: list[Json]) -> EditResult:
    """Apply ``ops`` in order to a copy of ``data``. All or nothing: the first
    operation that cannot apply raises ``EditError`` and nothing is returned."""
    editor = _Editor(copy.deepcopy(data) if isinstance(data, dict) else {})
    editor.data.setdefault("sites", [])
    editor.data.setdefault("siteConnections", [])
    for index, raw in enumerate(ops):
        if not isinstance(raw, dict):
            raise EditError("each operation is an object", index=index)
        name = str(raw.get("op") or "")
        fn = OPERATIONS.get(name)
        if fn is None:
            raise EditError(
                f"unknown operation '{name}'; one of: {', '.join(OPERATIONS)}", index=index, op=name
            )
        editor.index = index
        try:
            fn(editor, _resolve_refs(raw, editor.result.created))
        except EditError as exc:
            if exc.index is None:
                exc.index, exc.op = index, name
            raise
    return editor.result
