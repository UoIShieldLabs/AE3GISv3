"""Tools that drive the user's browser (in-app only, never over MCP): open a
topology, select devices, open a view, re-arrange the canvas. They return at once;
the browser carries the action out when that topology is open."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from services.agent.tools.base import ToolContext, ToolResult, tool
from services.agent.tools.common import TopologyArg, own_topology, topology_id, view_topology


class OpenIn(TopologyArg):
    site_id: str = Field(default="", description="Drill into this site.")
    subnet_id: str = Field(default="", description="Drill into this subnet (give site_id too).")


@tool(
    "open_in_editor",
    "Open a topology in the user's editor (optionally inside a site or subnet).",
    OpenIn,
    tier="tutor",
    surface="app",
)
async def open_in_editor(ctx: ToolContext, args: OpenIn) -> ToolResult:
    with ctx.db() as db:
        topo = view_topology(db, ctx, args.topology_id)
        tid, name = topo.id, topo.name
    action = {"type": "open_topology", "topology_id": tid}
    if args.site_id:
        action["site_id"] = args.site_id
    if args.subnet_id:
        action["subnet_id"] = args.subnet_id
    return ToolResult(f"Opened {name} in the editor.", ui=[action])


class SelectIn(TopologyArg):
    ids: list[str] = Field(min_length=1, max_length=200, description="Site, subnet or device ids.")


@tool(
    "select_nodes",
    "Highlight sites, subnets or devices on the user's canvas (to point at what you mean).",
    SelectIn,
    tier="tutor",
    surface="app",
)
async def select_nodes(ctx: ToolContext, args: SelectIn) -> ToolResult:
    tid = topology_id(ctx, args.topology_id)
    return ToolResult(
        f"Selected {len(args.ids)} item(s).",
        ui=[{"type": "select", "topology_id": tid, "ids": args.ids}],
    )


class ViewIn(TopologyArg):
    view: Literal["terminal", "capture", "traffic", "monitor", "scenario"]
    node: str = Field(default="", description="terminal: the device to open a shell on.")
    job_id: str = Field(default="", description="capture / traffic / monitor: the run to show.")


@tool(
    "open_view",
    "Open a panel in the user's dock: a terminal on a device, or the live view of a capture, "
    "traffic run, monitor or the scenario runner.",
    ViewIn,
    tier="tutor",
    surface="app",
)
async def open_view(ctx: ToolContext, args: ViewIn) -> ToolResult:
    tid = topology_id(ctx, args.topology_id)
    action = {"type": "open_view", "topology_id": tid, "view": args.view}
    if args.node:
        action["node"] = args.node
    if args.job_id:
        action["job_id"] = args.job_id
    return ToolResult(f"Opened the {args.view} view.", ui=[action])


class ArrangeIn(TopologyArg):
    layout: Literal["tree", "circle", "grid", "purdue"] = "tree"
    site_id: str = Field(default="", description="Arrange inside this site (default: the sites).")
    subnet_id: str = Field(default="", description="Arrange inside this subnet (give site_id).")


@tool(
    "arrange",
    "Re-arrange a level of the canvas with an auto-layout (tree, circle, grid, purdue) and save "
    "it. Applied in the user's editor when the topology is open there.",
    ArrangeIn,
    risk="write",
    surface="app",
)
async def arrange(ctx: ToolContext, args: ArrangeIn) -> ToolResult:
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        tid = topo.id
    action = {"type": "arrange", "topology_id": tid, "layout": args.layout}
    if args.site_id:
        action["site_id"] = args.site_id
    if args.subnet_id:
        action["subnet_id"] = args.subnet_id
    return ToolResult(f"Asked the editor to arrange it as {args.layout}.", ui=[action])
