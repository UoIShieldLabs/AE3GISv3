"""Topology tools: list, read, create, edit, validate, duplicate, delete."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

import catalog
from api import presets as presets_api
from api.errors import Invalid
from api.schemas import GenerateRequest
from domain import saved_state
from domain.agent_views import compact_json, topology_outline
from domain.generator import GeneratorError, GeneratorParams, check_catalog, generate
from domain.topology_edit import apply_ops
from services import lessons, topologies
from services.agent.tools.base import ToolContext, ToolResult, tool
from services.agent.tools.common import (
    TopologyArg,
    own_topology,
    ui_topology_changed,
    view_topology,
)


def _diag_dicts(diags: list[Any]) -> list[dict[str, Any]]:
    return [d.to_dict() for d in diags]


def _outline(topo: Any, diags: list[Any] | None = None) -> str:
    return topology_outline(
        topologies.data_with_name(topo),
        topology_id=topo.id,
        version=topo.version,
        status=topo.status,
        diagnostics=_diag_dicts(diags) if diags is not None else None,
    )


# ── reading ──────────────────────────────────────────────────────────


class ListIn(BaseModel):
    query: str = Field(default="", description="Only names containing this (case-insensitive).")
    limit: int = Field(default=50, ge=1, le=200)


@tool(
    "list_topologies",
    "List the topologies you can see (id, name, status, owner, whether published or a lesson copy).",
    ListIn,
    tier="tutor",
)
async def list_topologies(ctx: ToolContext, args: ListIn) -> ToolResult:
    with ctx.db() as db:
        topos = topologies.list_visible(db, ctx.identity)
        q = args.query.strip().lower()
        if q:
            topos = [t for t in topos if q in (t.name or "").lower()]
        topos = topos[: args.limit]
        meta = topologies.summary_meta(db, topos)
        rows = []
        for t in topos:
            m = meta[t.id]
            owner = (m.get("owner") or {}).get("username") if m.get("owner") else None
            flags = [t.status, f"v{t.version}"]
            if owner:
                flags.append(f"owner={owner}")
            if m.get("published"):
                flags.append("published")
            if t.source_id:
                flags.append(f"copy-of={t.source_id}")
            rows.append(f"- {t.name} [{t.id}] {' '.join(flags)}")
    text = "\n".join(rows) if rows else "No topologies."
    return ToolResult(text, data={"count": len(rows)})


class GetIn(TopologyArg):
    include_json: bool = Field(
        default=False,
        description="Also return the raw topology JSON (only for fields the outline doesn't show).",
    )


@tool(
    "get_topology",
    "Read a topology: sites → subnets → devices with ids, IPs, images and every link, plus "
    "its tutorials, scenarios and validation diagnostics. Ids in [brackets] are what other "
    "tools take.",
    GetIn,
    tier="tutor",
)
async def get_topology(ctx: ToolContext, args: GetIn) -> ToolResult:
    with ctx.db() as db:
        topo = view_topology(db, ctx, args.topology_id)
        text = _outline(topo, topologies.diagnostics_for(topo.data))
        if args.include_json:
            text += "\n\nJSON:\n" + compact_json(topo.data or {}, 16_000)
        return ToolResult(text, data={"topology_id": topo.id, "version": topo.version})


@tool(
    "validate_topology",
    "Check a topology for problems. Errors block a deploy; warnings only inform.",
    TopologyArg,
    tier="tutor",
)
async def validate_topology(ctx: ToolContext, args: TopologyArg) -> ToolResult:
    with ctx.db() as db:
        topo = view_topology(db, ctx, args.topology_id)
        diags = _diag_dicts(topologies.diagnostics_for(topo.data))
    if not diags:
        return ToolResult("No problems found.", data={"diagnostics": []})
    lines = [f"- {d['severity']}: {d['message']} ({d['code']})" for d in diags]
    errors = sum(1 for d in diags if d["severity"] == "error")
    return ToolResult(
        f"{errors} error(s), {len(diags) - errors} warning(s):\n" + "\n".join(lines),
        data={"diagnostics": diags},
    )


class CatalogIn(BaseModel):
    category: str = Field(default="", description="Only this category (e.g. network, ics).")


@tool(
    "get_catalog",
    "The device types you can add (id, display name, role router|switch|host, category, "
    "default image and image variants, Purdue level).",
    CatalogIn,
    tier="tutor",
)
async def get_catalog(ctx: ToolContext, args: CatalogIn) -> ToolResult:
    rows = []
    for type_id, spec in sorted(catalog.node_types().items()):
        if args.category and spec.get("category") != args.category:
            continue
        variants = [i for i in spec.get("images") or [] if i != spec.get("defaultImage")]
        line = (
            f"- {type_id}: {spec.get('displayName')} role={spec.get('role')} "
            f"category={spec.get('category')} default={spec.get('defaultImage')}"
        )
        if variants:
            line += f" variants={','.join(variants)}"
        if spec.get("purdueLevel") is not None:
            line += f" purdue={spec['purdueLevel']}"
        if spec.get("webUiPort"):
            line += f" web-ui:{spec['webUiPort']}"
        rows.append(line)
    return ToolResult("\n".join(rows) or "No types in that category.")


# ── creating and editing ─────────────────────────────────────────────


class CreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    preset: str = Field(
        default="",
        description="Start from a preset (ids: list them with read_docs topic 'presets').",
    )
    generate: GenerateRequest | None = Field(
        default=None,
        description="Instead of blank: generate a parametric network (a servers subnet behind "
        "a core router, client subnets behind their own routers).",
    )


@tool(
    "create_topology",
    "Create a new topology you own: blank, from a preset, or generated. Returns its id and "
    "outline. Build it out with edit_topology, then open_in_editor so the user sees it.",
    CreateIn,
    risk="write",
)
async def create_topology(ctx: ToolContext, args: CreateIn) -> ToolResult:
    if args.generate is not None:
        try:
            params = GeneratorParams(**args.generate.model_dump())
            check_catalog(params, catalog.node_types())
            data = generate(params)
        except GeneratorError as exc:
            raise Invalid(str(exc), code="bad_generator") from exc
    elif args.preset:
        preset = presets_api._load_preset(args.preset.strip())
        data = preset.get("topology") if isinstance(preset.get("topology"), dict) else {}
        data = json.loads(json.dumps(data))
    else:
        data = {"sites": [], "siteConnections": [], "view": {"version": 2}}
    data["name"] = args.name
    if args.description:
        data["description"] = args.description
    with ctx.db() as db:
        topo, diags = topologies.create(
            db, name=args.name, data=data, owner_id=ctx.identity.owner_id
        )
        return ToolResult(
            f"Created topology {topo.name} [{topo.id}].\n" + _outline(topo, diags),
            data={"topology_id": topo.id, "version": topo.version},
        )


class _Op(BaseModel):
    model_config = {"extra": "forbid"}


class SetMetaOp(_Op):
    op: Literal["set_meta"]
    name: str | None = None
    description: str | None = None


class AddSiteOp(_Op):
    op: Literal["add_site"]
    name: str = ""
    location: str = ""


class AddSubnetOp(_Op):
    op: Literal["add_subnet"]
    site: str = Field(description="Site id.")
    cidr: str = Field(description="e.g. 10.0.1.0/24; unique across the topology.")
    name: str = ""
    purdue_level: float | None = Field(default=None, description="5, 4, 3.5 (DMZ), 3, 2, 1, 0.")
    infra: bool = Field(
        default=True,
        description="Add the gateway router (first address) and a switch, linked. Its result "
        "names them: refer to them later as $N.router / $N.switch.",
    )


class AddDeviceOp(_Op):
    op: Literal["add_device"]
    subnet: str = Field(description="Subnet id.")
    type: str = Field(description="A catalog type id (get_catalog).")
    name: str = ""
    ip: str = Field(default="", description="Omit for the next free address.")
    image: str = Field(default="", description="Omit for the type's default image.")
    env: dict[str, str] | None = None
    web_ui_port: int | None = None
    connect_to: str | None = Field(
        default="auto",
        description="'auto' (default): link to the subnet's switch (a new switch links to the "
        "router); a device id in the same subnet; or null for no link.",
    )


class AddInterfaceOp(_Op):
    op: Literal["add_interface"]
    device: str = Field(description="Device id (not a switch).")
    subnet: str = Field(description="Another subnet to attach a leg to (dual-homing).")
    ip: str = ""


class ConnectOp(_Op):
    op: Literal["connect"]
    a: str = Field(description="Id of a site, subnet or device.")
    b: str
    label: str = ""


class UpdateOp(_Op):
    op: Literal["update"]
    id: str = Field(
        description="Id of a site, subnet, device, link, scenario, phase, tutorial or cell."
    )
    set: dict[str, Any] = Field(
        default_factory=dict,
        description="Fields to set, using the topology's own names (name, ip, image, env, "
        "webUiPort, mirrorTo, cidr, gateway, purdueLevel, label, title, source, command…).",
    )
    unset: list[str] = Field(default_factory=list)


class RemoveOp(_Op):
    op: Literal["remove"]
    ids: list[str] = Field(
        description="Sites, subnets, devices, links, scenarios, phases, tutorials or cells. "
        "Removing a node also drops its links, legs and scenario steps."
    )


class AddScenarioOp(_Op):
    op: Literal["add_scenario"]
    name: str = ""
    description: str = ""


class AddPhaseOp(_Op):
    op: Literal["add_phase"]
    scenario: str
    name: str = ""
    description: str = ""


class AddStepOp(_Op):
    op: Literal["add_step"]
    phase: str
    device: str
    script: str = Field(description="The command line to run on the device.")
    args: list[str] | None = None


class RemoveStepOp(_Op):
    op: Literal["remove_step"]
    phase: str
    index: int


class AddTutorialOp(_Op):
    op: Literal["add_tutorial"]
    title: str = ""


class AddCellOp(_Op):
    op: Literal["add_cell"]
    tutorial: str
    kind: Literal["markdown", "command"]
    source: str = Field(default="", description="Markdown (kind markdown).")
    device: str = Field(default="", description="Device the command is typed into (kind command).")
    command: str = ""
    after: str = Field(default="", description="Insert after this cell id (default: at the end).")


class SetupStep(BaseModel):
    device: str
    command: str


class SetTutorialSetupOp(_Op):
    op: Literal["set_tutorial_setup"]
    tutorial: str
    steps: list[SetupStep] = Field(
        description="Commands 'Configure lab' runs headless, in order, before the tutorial."
    )


EditOp = Annotated[
    SetMetaOp
    | AddSiteOp
    | AddSubnetOp
    | AddDeviceOp
    | AddInterfaceOp
    | ConnectOp
    | UpdateOp
    | RemoveOp
    | AddScenarioOp
    | AddPhaseOp
    | AddStepOp
    | RemoveStepOp
    | AddTutorialOp
    | AddCellOp
    | SetTutorialSetupOp,
    Field(discriminator="op"),
]


class EditIn(TopologyArg):
    ops: list[EditOp] = Field(min_length=1, max_length=200)
    expected_version: int | None = Field(
        default=None, description="Fail if the topology changed since this version."
    )


@tool(
    "edit_topology",
    """Apply edit operations to a topology, in order, all or nothing. Ops: set_meta, add_site,
add_subnet (adds its router + switch), add_device (next free IP, linked to the switch), connect
(device↔device in a subnet, router↔router across, subnet↔subnet or site↔site through gateway
routers), add_interface (dual-home a device), update, remove; scenarios: add_scenario,
add_phase, add_step, remove_step; tutorials: add_tutorial, add_cell, set_tutorial_setup.
A later op can name what an earlier one created as "$N" (N = op index), and an add_subnet's
infrastructure as "$N.router" / "$N.switch". Returns the created ids and the diagnostics.""",
    EditIn,
    risk="write",
)
async def edit_topology(ctx: ToolContext, args: EditIn) -> ToolResult:
    # An omitted connect_to dumps as "auto"; an explicit null stays None (no link).
    ops = [op.model_dump() for op in args.ops]
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        result = apply_ops(topo.data or {}, ops)
        if not result.changed:
            return ToolResult("Nothing changed.", data={"version": topo.version})
        name = result.data.get("name") if isinstance(result.data.get("name"), str) else None
        topo, diags = topologies.update(
            db,
            topo,
            name=name,
            data=result.data,
            expected_version=args.expected_version
            if args.expected_version is not None
            else topo.version,
        )
        created = "\n".join(
            f"- op {c['op']}: {c['kind']} {c.get('name') or ''} [{c['id']}]".replace("  ", " ")
            + "".join(f" {k}={c[k]}" for k in ("router", "switch", "ip") if c.get(k))
            for c in result.created
        )
        d = _diag_dicts(diags)
        errors = [x for x in d if x["severity"] == "error"]
        text = f"Saved {topo.name} [{topo.id}] as v{topo.version}."
        if created:
            text += "\nCreated:\n" + created
        if result.removed:
            text += f"\nRemoved: {', '.join(result.removed)}"
        if d:
            text += f"\nDiagnostics ({len(errors)} error(s)):\n" + "\n".join(
                f"- {x['severity']}: {x['message']}" for x in d[:30]
            )
        if topo.status == "deployed":
            text += "\nThe lab is deployed: it keeps running the old design until destroyed and redeployed."
        return ToolResult(
            text,
            data={"topology_id": topo.id, "version": topo.version, "created": result.created},
            ui=[ui_topology_changed(topo)],
        )


class DuplicateIn(TopologyArg):
    name: str = Field(default="", max_length=200)


@tool(
    "duplicate_topology",
    "Make a copy of a topology that you own (a student's lesson copy is never made here).",
    DuplicateIn,
    risk="write",
)
async def duplicate_topology(ctx: ToolContext, args: DuplicateIn) -> ToolResult:
    with ctx.db() as db:
        source = view_topology(db, ctx, args.topology_id)
        topo, _ = topologies.copy_for(db, ctx.identity, source, duplicate=True)
        if args.name.strip():
            topo, _ = topologies.update(db, topo, name=args.name.strip())
        return ToolResult(
            f"Created {topo.name} [{topo.id}], a copy of {source.name}.",
            data={"topology_id": topo.id},
        )


@tool(
    "delete_topology",
    "Delete a topology for good (a lesson's student copies go with it). Always asks the user.",
    TopologyArg,
    risk="risky",
    always_ask=True,
)
async def delete_topology(ctx: ToolContext, args: TopologyArg) -> ToolResult:
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        name, tid = topo.name, topo.id
        refs = saved_state.refs(topo.saved_state)
        retired = topologies.delete(db, topo)
    lessons.schedule(ctx.runner, ctx.engine, retired)
    await ctx.engine.remove_images(refs)
    return ToolResult(
        f"Deleted {name} [{tid}].", ui=[{"type": "topology_deleted", "topology_id": tid}]
    )
