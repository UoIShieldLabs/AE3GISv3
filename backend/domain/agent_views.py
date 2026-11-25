"""Compact, bounded text views for the agent (what a tool hands back to a model).

Models read text better than raw records, and a topology or a job log can be far
larger than is useful in a conversation. These views keep every id the agent
needs to act on (in ``[brackets]``) and drop the rest; every tool result also
goes through ``clip`` so no single call floods the context.
"""

from __future__ import annotations

import json
from typing import Any

import catalog

Json = dict[str, Any]

# Characters of one tool result handed to the model (the UI keeps the full data).
RESULT_CHARS = 8_000


def clip(text: str, limit: int = RESULT_CHARS) -> str:
    """Trim ``text`` to ``limit`` characters, keeping the head and the tail."""
    if len(text) <= limit:
        return text
    head = int(limit * 0.7)
    tail = limit - head - 60
    dropped = len(text) - head - max(tail, 0)
    return f"{text[:head]}\n… [{dropped} characters cut] …\n{text[-tail:] if tail > 0 else ''}"


def compact_json(value: Any, limit: int = RESULT_CHARS) -> str:
    return clip(json.dumps(value, default=str, separators=(",", ":")), limit)


def _dicts(value: Any) -> list[Json]:
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _device_line(c: Json, names: dict[str, str]) -> str:
    type_name = str(c.get("type", ""))
    parts = [
        f"- {c.get('name') or c.get('id')} [{c.get('id')}] {type_name}",
        str(c.get("ip") or "no-ip"),
    ]
    image = c.get("image")
    if image:
        parts.append(f"image={image}")
    else:
        parts.append(f"image={catalog.resolve_image(type_name)} (default)")
    for leg in _dicts(c.get("interfaces")):
        parts.append(
            f"leg {names.get(str(leg.get('subnetId')), leg.get('subnetId'))}={leg.get('ip')}"
        )
    if c.get("mirrorTo"):
        parts.append(f"mirrors-to={c['mirrorTo']}")
    if c.get("webUiPort"):
        parts.append(f"web-ui:{c['webUiPort']}")
    if c.get("env"):
        parts.append("env=" + ",".join(f"{k}={v}" for k, v in dict(c["env"]).items()))
    return " ".join(parts)


def _link(conn: Json, names: dict[str, str]) -> str:
    a, b = str(conn.get("from")), str(conn.get("to"))
    text = f"{names.get(a, a)} — {names.get(b, b)} [{conn.get('id')}]"
    fc, tc = conn.get("fromContainer"), conn.get("toContainer")
    if fc or tc:
        text += f" via {names.get(str(fc), fc)} ↔ {names.get(str(tc), tc)}"
    return text


def topology_outline(
    data: Json,
    *,
    topology_id: str = "",
    version: int | None = None,
    status: str = "",
    diagnostics: list[Json] | None = None,
) -> str:
    """Sites → subnets → devices with ids, addresses, images and every link."""
    names: dict[str, str] = {}
    sites = _dicts(data.get("sites"))
    for site in sites:
        names[str(site.get("id"))] = str(site.get("name") or site.get("id"))
        for subnet in _dicts(site.get("subnets")):
            names[str(subnet.get("id"))] = str(subnet.get("name") or subnet.get("id"))
            for c in _dicts(subnet.get("containers")):
                names[str(c.get("id"))] = str(c.get("name") or c.get("id"))
    n_subnets = sum(len(_dicts(s.get("subnets"))) for s in sites)
    n_devices = sum(
        len(_dicts(sn.get("containers"))) for s in sites for sn in _dicts(s.get("subnets"))
    )
    head = f'Topology "{data.get("name") or "untitled"}"'
    if topology_id:
        head += f" [{topology_id}]"
    meta = [x for x in (f"v{version}" if version is not None else "", status) if x]
    if meta:
        head += f" ({', '.join(meta)})"
    lines = [f"{head}: {len(sites)} site(s), {n_subnets} subnet(s), {n_devices} device(s)"]
    if data.get("description"):
        lines.append(f"Description: {clip(str(data['description']), 400)}")
    for site in sites:
        lines.append(f"Site {site.get('name')} [{site.get('id')}]")
        for subnet in _dicts(site.get("subnets")):
            extra = (
                f" purdue={subnet['purdueLevel']}" if subnet.get("purdueLevel") is not None else ""
            )
            lines.append(
                f"  Subnet {subnet.get('name')} [{subnet.get('id')}] {subnet.get('cidr') or 'no-cidr'}"
                f" gateway={subnet.get('gateway') or 'none'}{extra}"
            )
            for c in _dicts(subnet.get("containers")):
                lines.append("    " + _device_line(c, names))
            for conn in _dicts(subnet.get("connections")):
                lines.append("    link " + _link(conn, names))
        for conn in _dicts(site.get("subnetConnections")):
            lines.append("  subnet link " + _link(conn, names))
    for conn in _dicts(data.get("siteConnections")):
        lines.append("site link " + _link(conn, names))
    tutorials = _dicts(data.get("tutorials"))
    if tutorials:
        lines.append(
            "Tutorials: "
            + "; ".join(
                f"{t.get('title')} [{t.get('id')}] {len(_dicts(t.get('cells')))} cell(s)"
                for t in tutorials
            )
        )
    scenarios = _dicts(data.get("scenarios"))
    for sc in scenarios:
        phases = _dicts(sc.get("phases"))
        lines.append(
            f"Scenario {sc.get('name')} [{sc.get('id')}]: "
            + "; ".join(
                f"{p.get('name')} [{p.get('id')}] {len(_dicts(p.get('executions')))} step(s)"
                for p in phases
            )
        )
    if diagnostics:
        lines.append("Diagnostics:")
        for d in diagnostics[:40]:
            lines.append(f"  {d.get('severity')}: {d.get('message')} ({d.get('code')})")
        if len(diagnostics) > 40:
            lines.append(f"  … and {len(diagnostics) - 40} more")
    return clip("\n".join(lines), 24_000)


def tutorial_text(tutorial: Json, names: dict[str, str] | None = None) -> str:
    names = names or {}
    lines = [f"Tutorial {tutorial.get('title')} [{tutorial.get('id')}]"]
    setup = tutorial.get("setup") if isinstance(tutorial.get("setup"), dict) else None
    if setup:
        for s in _dicts(setup.get("steps")):
            cid = str(s.get("containerId"))
            lines.append(f"  setup on {names.get(cid, cid)}: {s.get('command')}")
        for t in _dicts(setup.get("traffic")):
            lines.append(f"  background traffic: {compact_json(t, 300)}")
    for i, cell in enumerate(_dicts(tutorial.get("cells"))):
        if cell.get("kind") == "command":
            cid = str(cell.get("containerId"))
            lines.append(
                f"  [{i}] command on {names.get(cid, cid)} [{cell.get('id')}]: {cell.get('command')}"
            )
        else:
            lines.append(
                f"  [{i}] note [{cell.get('id')}]: {clip(str(cell.get('source') or ''), 1200)}"
            )
    return clip("\n".join(lines))


def node_names(data: Json) -> dict[str, str]:
    names: dict[str, str] = {}
    for site in _dicts(data.get("sites")):
        for subnet in _dicts(site.get("subnets")):
            for c in _dicts(subnet.get("containers")):
                names[str(c.get("id"))] = str(c.get("name") or c.get("id"))
    return names


def job_text(job: Json, log_tail: str = "") -> str:
    lines = [f"Job {job.get('kind')} [{job.get('id')}] status={job.get('status')}"]
    if job.get("error"):
        lines.append(f"error: {job['error']}")
    for step in job.get("steps") or []:
        if isinstance(step, dict):
            msg = f" — {step.get('message')}" if step.get("message") else ""
            lines.append(f"  step {step.get('name')}: {step.get('status')}{msg}")
    result = job.get("result")
    if result:
        lines.append("result: " + compact_json(result, 3000))
    if log_tail:
        lines.append("log tail:\n" + clip(log_tail, 3000))
    return clip("\n".join(lines))


def runtime_text(runtime: Json, names: dict[str, str] | None = None) -> str:
    names = names or {}
    lines = [f"status={runtime.get('status')} version={runtime.get('version')}"]
    if runtime.get("deployed_at"):
        lines.append(f"deployed_at={runtime['deployed_at']}")
    job = runtime.get("active_job")
    if job:
        lines.append(
            f"active job: {job.get('kind')} [{job.get('id')}] {job.get('status')}"
            + "".join(f"; {s.get('name')}={s.get('status')}" for s in job.get("steps") or [])
        )
    for a in runtime.get("activity") or []:
        lines.append(
            f"running: {a.get('kind')} [{a.get('job_id')}] {a.get('label') or ''}".rstrip()
        )
    nodes = runtime.get("nodes") or []
    if nodes:
        states: dict[str, list[str]] = {}
        for n in nodes:
            states.setdefault(str(n.get("state")), []).append(
                names.get(str(n.get("id")), str(n.get("id")))
            )
        for state, who in states.items():
            lines.append(f"nodes {state}: {', '.join(who[:60])}{' …' if len(who) > 60 else ''}")
    saved = runtime.get("saved")
    if saved:
        lines.append(f"saved lab state: {compact_json(saved, 300)}")
    return clip("\n".join(lines))


def events_text(events: list[Json], limit: int = 25) -> str:
    rows = []
    for e in events[-limit:]:
        rows.append(f"{e.get('ts')} {e.get('level')} {e.get('type')}: {e.get('message')}")
    return clip("\n".join(rows), 4000)
