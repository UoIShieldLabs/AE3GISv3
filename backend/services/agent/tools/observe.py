"""Observation tools: packet captures, traffic runs and resource monitors. Inputs
are the API's own request schemas, so the agent starts exactly what the UI does."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from api.errors import NotFound
from api.schemas import CaptureRequest, MonitorRequest, TrafficRunRequest
from db.models import Job, Topology
from domain.agent_views import compact_json, node_names
from domain.packets import summarize
from domain.pcap import PcapSplitter
from services import capture, traffic
from services import monitor as monitor_service
from services.agent.tools.base import ToolContext, ToolResult, tool
from services.agent.tools.common import TopologyArg, job_for, own_topology


def _started(kind: str, job: Job, extra: str = "") -> ToolResult:
    text = f"{kind} [{job.id}] started"
    if extra:
        text += f" ({extra})"
    text += ". Stop it with stop_run; read it with get_job"
    return ToolResult(text + ".", data={"job_id": job.id, "topology_id": job.topology_id})


class CaptureIn(TopologyArg, CaptureRequest):
    """target: {kind: "link", connection_id} (a whole link, from one end) or
    {kind: "interface", node_id, interface: "eth0"}. Link ids are in get_topology."""


@tool(
    "start_capture",
    "Capture packets on a link ({kind:'link', connection_id}) or a node interface "
    "({kind:'interface', node_id, interface:'eth0'}) of a deployed topology, with an optional "
    "BPF filter (e.g. 'icmp', 'tcp port 502') and limits. Read packets with get_packets.",
    CaptureIn,
    risk="write",
)
async def start_capture(ctx: ToolContext, args: CaptureIn) -> ToolResult:
    req = CaptureRequest.model_validate(args.model_dump(exclude={"topology_id"})).model_dump()
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        job, created = capture.start_capture(db, ctx.runner, topo, req)
        result = _started("Capture", job, "" if created else "already capturing there")
    result.ui.append(
        {
            "type": "open_view",
            "topology_id": job.topology_id,
            "view": "capture",
            "job_id": job.id,
            "auto": True,
        }
    )
    return result


def _read_packets(path: Path, after: int, limit: int) -> tuple[list[dict[str, Any]], int]:
    splitter = PcapSplitter()
    items: list[dict[str, Any]] = []
    n = 0
    with path.open("rb") as fh:
        while chunk := fh.read(1 << 20):
            for rec in splitter.feed(chunk):
                n += 1
                if n > after and len(items) < limit:
                    items.append(
                        summarize(n, rec.ts, rec.data, rec.origlen, splitter.linktype).to_dict()
                    )
    return items, n


class PacketsIn(BaseModel):
    capture_id: str = Field(description="The capture's job id.")
    after: int = Field(default=0, ge=0, description="Packet number to start after (paging).")
    limit: int = Field(default=60, ge=1, le=300)
    contains: str = Field(default="", description="Only packets whose summary contains this text.")


@tool(
    "get_packets",
    "Packet summaries of a capture (number, time, src → dst, protocol, info), from its pcap; "
    "works while it runs and after it stopped.",
    PacketsIn,
    tier="tutor",
)
async def get_packets(ctx: ToolContext, args: PacketsIn) -> ToolResult:
    with ctx.db() as db:
        job = job_for(db, ctx, args.capture_id)
        if job.kind != capture.KIND:
            raise NotFound("Capture")
        status = job.status
    assert ctx.runner.artifacts is not None
    path = ctx.runner.artifacts.path(args.capture_id, capture.PCAP_NAME)
    if not path.exists():
        return ToolResult(f"No packets yet (capture {status}).")
    want = args.limit if not args.contains else 5000
    items, total = await asyncio.to_thread(_read_packets, path, args.after, want)
    needle = args.contains.lower()
    if needle:
        items = [
            p for p in items if needle in f"{p['src']} {p['dst']} {p['proto']} {p['info']}".lower()
        ][: args.limit]
    lines = [
        f"{p['n']} {p['ts']:.3f} {p['src']} → {p['dst']} {p['proto']} {p['len']}B {p['info']}"
        for p in items
    ]
    head = f"Capture [{args.capture_id}] {status}: {total} packet(s); showing {len(items)}"
    if items:
        head += f" (next after={items[-1]['n']})"
    return ToolResult(head + "\n" + "\n".join(lines), data={"total": total})


class TrafficIn(TopologyArg, TrafficRunRequest):
    """flows: iperf3 flows {id, client, server, protocol, bitrate…}; patterns:
    {id, kind: clients_to_servers|mesh, clients/servers/nodes selectors, bitrate}."""


@tool(
    "start_traffic",
    "Generate iperf3 traffic between deployed nodes: explicit flows ({id, client, server, "
    "protocol tcp|udp, bitrate e.g. '10M', direction}) and/or patterns (clients_to_servers or "
    "mesh over node selectors). duration_s defaults to 30. One run per topology at a time.",
    TrafficIn,
    risk="write",
)
async def start_traffic(ctx: ToolContext, args: TrafficIn) -> ToolResult:
    req = TrafficRunRequest.model_validate(args.model_dump(exclude={"topology_id"})).model_dump()
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        job = traffic.start_run(db, ctx.runner, topo, req)
        result = _started("Traffic run", job, f"{args.duration_s or 'until stopped'}s")
    result.ui.append(
        {
            "type": "open_view",
            "topology_id": job.topology_id,
            "view": "traffic",
            "job_id": job.id,
            "auto": True,
        }
    )
    return result


class MonitorIn(TopologyArg, MonitorRequest):
    """nodes: "all", a list of device ids, or a selector {types, subnets, roles, ids, exclude}."""


@tool(
    "start_monitor",
    "Record CPU, memory and network of the lab's nodes and of the host every interval_s "
    "(default 1 s) until stopped or duration_s. Read it with monitor_snapshot.",
    MonitorIn,
    risk="write",
)
async def start_monitor(ctx: ToolContext, args: MonitorIn) -> ToolResult:
    req = MonitorRequest.model_validate(args.model_dump(exclude={"topology_id"})).model_dump()
    if isinstance(args.nodes, BaseModel):
        req["nodes"] = args.nodes.model_dump(exclude_none=True)
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        job = monitor_service.start_monitor(db, ctx.runner, topo, req)
        result = _started("Monitor", job)
    result.ui.append(
        {
            "type": "open_view",
            "topology_id": job.topology_id,
            "view": "monitor",
            "job_id": job.id,
            "auto": True,
        }
    )
    return result


class SnapshotIn(BaseModel):
    monitor_id: str = Field(description="The monitor's job id.")
    top: int = Field(default=10, ge=1, le=50, description="How many of the busiest nodes.")


@tool(
    "monitor_snapshot",
    "The latest sweep of a monitor: host totals and the busiest nodes by CPU (with memory, "
    "rx/tx rates).",
    SnapshotIn,
    tier="tutor",
)
async def monitor_snapshot(ctx: ToolContext, args: SnapshotIn) -> ToolResult:
    with ctx.db() as db:
        job = job_for(db, ctx, args.monitor_id)
        if job.kind != "monitor":
            raise NotFound("Monitor")
        status = job.status
        topo = db.get(Topology, job.topology_id) if job.topology_id else None
        names = node_names(topo.data or {}) if topo is not None else {}
    assert ctx.runner.artifacts is not None
    directory = ctx.runner.artifacts.dir(args.monitor_id)

    def read() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return (
            monitor_service.read_csv(directory, monitor_service.HOST_NAME),
            monitor_service.read_csv(directory, monitor_service.NODES_NAME),
        )

    host, nodes = await asyncio.to_thread(read)
    if not host:
        return ToolResult(f"Monitor [{args.monitor_id}] {status}: no samples yet.")
    last_t = host[-1]["t"]
    latest = [r for r in nodes if r.get("t") == last_t and r.get("kind") != "tool"]
    latest.sort(key=lambda r: float(r.get("cpu_pct") or 0), reverse=True)
    host_row = {k: v for k, v in host[-1].items() if v not in ("", None)}
    lines = [
        f"Monitor [{args.monitor_id}] {status}, t={last_t}s",
        "host: " + compact_json(host_row, 1500),
    ]
    for r in latest[: args.top]:
        who = names.get(str(r.get("target")), r.get("target"))
        lines.append(
            f"- {who}: cpu={r.get('cpu_pct')}% mem={r.get('mem_used')} rx={r.get('rx_bps')}bps tx={r.get('tx_bps')}bps"
        )
    return ToolResult("\n".join(lines))
