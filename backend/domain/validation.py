"""Topology diagnostics.

Errors are conditions the deployment engine cannot work around; deploy is
refused while any exist. Warnings are honest reports of things the engine will
ignore or guess. Saves are never rejected: a draft may be incomplete.
"""

from __future__ import annotations

import ipaddress
from dataclasses import asdict, dataclass
from typing import Any, Literal

import catalog
from domain.topology import (
    containers,
    is_router,
    iter_connections,
    sites,
    subnets,
)

Severity = Literal["error", "warning"]


@dataclass
class Diagnostic:
    code: str
    severity: Severity
    message: str
    path: str = ""
    node_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def has_errors(diags: list[Diagnostic]) -> bool:
    return any(d.severity == "error" for d in diags)


def summarize(diags: list[Diagnostic]) -> dict[str, int]:
    return {
        "errors": sum(1 for d in diags if d.severity == "error"),
        "warnings": sum(1 for d in diags if d.severity == "warning"),
    }


def _valid_cidr(cidr: Any) -> ipaddress.IPv4Network | None:
    if not isinstance(cidr, str) or not cidr.strip():
        return None
    try:
        net = ipaddress.ip_network(cidr.strip(), strict=False)
    except ValueError:
        return None
    return net if isinstance(net, ipaddress.IPv4Network) else None


def _valid_ip(ip: Any) -> ipaddress.IPv4Address | None:
    if not isinstance(ip, str) or not ip.strip():
        return None
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return None
    return addr if isinstance(addr, ipaddress.IPv4Address) else None


def validate(data: Any) -> list[Diagnostic]:  # noqa: C901 - one linear pass, many checks
    out: list[Diagnostic] = []

    def err(code: str, msg: str, path: str = "", node: str | None = None) -> None:
        out.append(Diagnostic(code, "error", msg, path, node))

    def warn(code: str, msg: str, path: str = "", node: str | None = None) -> None:
        out.append(Diagnostic(code, "warning", msg, path, node))

    if not isinstance(data, dict):
        err("topology.shape", "Topology must be a JSON object")
        return out
    if "sites" in data and not isinstance(data["sites"], list):
        err("topology.shape", "'sites' must be a list", "sites")
        return out

    site_ids: dict[str, str] = {}
    subnet_ids: dict[str, str] = {}
    container_ids: dict[str, str] = {}  # id -> first path
    container_subnets: dict[str, set[str]] = {}
    names: dict[str, list[str]] = {}
    linked: set[str] = set()
    site_subnets: dict[str, set[str]] = {}
    subnet_containers: dict[str, set[str]] = {}
    subnet_has_router: dict[str, bool] = {}
    subnet_path: dict[str, str] = {}

    for si, site in enumerate(sites(data)):
        spath = f"sites[{si}]"
        sid = site.get("id")
        if not isinstance(sid, str) or not sid:
            err("id.missing", "Site has no id", spath)
            sid = f"__site{si}"
        elif sid in site_ids:
            err("id.duplicate", f"Duplicate site id '{sid}'", spath)
        site_ids[sid] = spath
        site_subnets[sid] = set()
        if not subnets(site):
            warn("site.empty", f"Site '{site.get('name') or sid}' has no subnets", spath, sid)

        for ni, subnet in enumerate(subnets(site)):
            npath = f"{spath}.subnets[{ni}]"
            nid = subnet.get("id")
            if not isinstance(nid, str) or not nid:
                err("id.missing", "Subnet has no id", npath)
                nid = f"__subnet{si}_{ni}"
            elif nid in subnet_ids or nid in site_ids:
                err("id.duplicate", f"Duplicate id '{nid}'", npath)
            subnet_ids[nid] = npath
            subnet_path[nid] = npath
            site_subnets[sid].add(nid)
            subnet_containers[nid] = set()
            subnet_has_router[nid] = False

            net = _valid_cidr(subnet.get("cidr"))
            if net is None:
                err(
                    "cidr.invalid",
                    f"Subnet '{subnet.get('name') or nid}' needs an IPv4 CIDR like 10.0.1.0/24",
                    f"{npath}.cidr",
                    nid,
                )

            gw = subnet.get("gateway")
            if gw:
                gw_ip = _valid_ip(gw)
                if gw_ip is None or (net is not None and gw_ip not in net):
                    warn(
                        "gateway.outside_subnet",
                        f"Gateway {gw} is not inside {subnet.get('cidr')}; the engine will auto-detect one",
                        f"{npath}.gateway",
                        nid,
                    )

            seen_ips: dict[str, str] = {}
            router_ips: set[str] = set()
            if not containers(subnet):
                warn(
                    "subnet.empty",
                    f"Subnet '{subnet.get('name') or nid}' has no devices",
                    npath,
                    nid,
                )

            for ci, c in enumerate(containers(subnet)):
                cpath = f"{npath}.containers[{ci}]"
                cid = c.get("id")
                if not isinstance(cid, str) or not cid:
                    err("id.missing", "Device has no id", cpath)
                    cid = f"__c{si}_{ni}_{ci}"
                elif cid in subnet_containers[nid]:
                    err("id.duplicate", f"Duplicate device id '{cid}' in subnet", cpath, cid)
                elif cid in site_ids or cid in subnet_ids:
                    err(
                        "id.duplicate",
                        f"Device id '{cid}' collides with a site or subnet id",
                        cpath,
                        cid,
                    )
                elif cid in container_ids:
                    # Same device in two subnets = multi-homing (supported by the engine).
                    warn(
                        "device.multihomed",
                        f"Device '{c.get('name') or cid}' is a member of more than one subnet",
                        cpath,
                        cid,
                    )
                container_ids.setdefault(cid, cpath)
                container_subnets.setdefault(cid, set()).add(nid)
                subnet_containers[nid].add(cid)

                ctype = str(c.get("type", "") or "")
                if catalog.get_type(ctype) is None:
                    warn(
                        "type.unknown",
                        f"Unknown device type '{ctype}' deploys as a plain host",
                        f"{cpath}.type",
                        cid,
                    )
                if is_router(c):
                    subnet_has_router[nid] = True

                name = c.get("name")
                if isinstance(name, str) and name.strip():
                    names.setdefault(name.strip().lower(), []).append(cid)

                ip_raw = c.get("ip")
                ip = _valid_ip(ip_raw)
                if ip is None:
                    err(
                        "ip.invalid",
                        f"Device '{c.get('name') or cid}' needs a valid IPv4 address",
                        f"{cpath}.ip",
                        cid,
                    )
                else:
                    if net is not None and ip not in net:
                        err(
                            "ip.outside_subnet",
                            f"{ip_raw} is outside {subnet.get('cidr')}",
                            f"{cpath}.ip",
                            cid,
                        )
                    key = str(ip)
                    if key in seen_ips:
                        err(
                            "ip.duplicate",
                            f"{ip_raw} is used by more than one device in this subnet",
                            f"{cpath}.ip",
                            cid,
                        )
                    seen_ips[key] = cid
                    if is_router(c):
                        router_ips.add(key)

                if c.get("persistencePaths"):
                    warn(
                        "field.unsupported",
                        "persistencePaths is stored but not applied by the Kathara engine",
                        f"{cpath}.persistencePaths",
                        cid,
                    )
                if c.get("config"):
                    warn(
                        "field.unsupported",
                        "config is stored but not applied by the Kathara engine",
                        f"{cpath}.config",
                        cid,
                    )

            if (
                gw
                and net is not None
                and _valid_ip(gw) in net
                and str(_valid_ip(gw)) not in router_ips
            ):
                warn(
                    "gateway.not_router",
                    f"Gateway {gw} is not the address of a router in this subnet",
                    f"{npath}.gateway",
                    nid,
                )

    for lname, ids in names.items():
        if len(set(ids)) > 1:
            warn("name.duplicate", f"Several devices are named '{lname}'", "", ids[0])

    # ── connections ──
    subnets_with_uplinks: set[str] = set()
    for ref in iter_connections(data):
        conn = ref.conn
        frm, to = conn.get("from"), conn.get("to")
        for key, value in (("from", frm), ("to", to)):
            if not isinstance(value, str) or not value:
                err(
                    "connection.endpoint_missing", f"Connection has no '{key}'", f"{ref.path}.{key}"
                )
                continue
            if ref.kind == "container":
                ok = (
                    value in subnet_containers.get(str(ref.subnet.get("id")), set())
                    if ref.subnet
                    else False
                )
                if not ok:
                    err(
                        "connection.endpoint_unknown",
                        f"'{value}' is not a device in this subnet",
                        f"{ref.path}.{key}",
                    )
            elif ref.kind == "subnet":
                site_id = str(ref.site.get("id")) if ref.site else ""
                if value in site_subnets.get(site_id, set()):
                    subnets_with_uplinks.add(value)
                elif value not in container_ids:
                    err(
                        "connection.endpoint_unknown",
                        f"'{value}' is not a subnet or device of this site",
                        f"{ref.path}.{key}",
                    )
            else:
                if value not in site_ids and value not in container_ids:
                    err(
                        "connection.endpoint_unknown",
                        f"'{value}' is not a site or device",
                        f"{ref.path}.{key}",
                    )
            linked.add(value)
        for key in ("fromContainer", "toContainer"):
            value = conn.get(key)
            if value and value not in container_ids:
                err(
                    "connection.endpoint_unknown", f"'{value}' is not a device", f"{ref.path}.{key}"
                )
            elif value:
                linked.add(value)
        if isinstance(frm, str) and frm and frm == to:
            err("connection.self", "A connection cannot link a node to itself", ref.path)

    for nid in subnets_with_uplinks:
        if not subnet_has_router.get(nid):
            err(
                "subnet.no_router",
                "This subnet links to other subnets but has no router to route through",
                subnet_path[nid],
                nid,
            )

    for cid, cpath in container_ids.items():
        if cid not in linked and len(container_subnets.get(cid, ())) == 1:
            warn("device.unlinked", "Device is not connected to anything", cpath, cid)

    return out
