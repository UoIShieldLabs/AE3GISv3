"""Images and host tools: image status and builds (staff), labs on the host and
purging one (admins)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from api.errors import Forbidden
from domain.topology import images_in
from services import reconcile
from services.agent.tools.base import ToolContext, ToolResult, tool
from services.agent.tools.common import view_topology


class ImagesIn(BaseModel):
    topology_id: str = Field(default="", description="Only the images this topology uses.")


@tool(
    "list_images",
    "Node images and their status (ready, missing, stale, building, failed…), and whether "
    "this host can build them.",
    ImagesIn,
)
async def list_images(ctx: ToolContext, args: ImagesIn) -> ToolResult:
    images = ctx.runner.images
    assert images is not None
    if args.topology_id:
        with ctx.db() as db:
            topo = view_topology(db, ctx, args.topology_id)
            refs = images_in(topo.data or {})
    else:
        refs = images.catalog_refs()
    report = await images.report(refs)
    host = report.get("host") or {}
    lines = [
        f"host {host.get('platform')}: can build={host.get('can_build')} {host.get('detail') or ''}".rstrip()
    ]
    for img in report.get("images") or []:
        line = f"- {img.get('ref')} ({img.get('kind')}): {img.get('status')}"
        if img.get("reason"):
            line += f" — {img['reason']}"
        lines.append(line)
    return ToolResult("\n".join(lines))


class BuildIn(BaseModel):
    refs: list[str] = Field(min_length=1, max_length=20, description="Image refs (ae3gis.local/…).")
    fresh: bool = Field(default=False, description="Rebuild from scratch (no cache).")


@tool(
    "build_images",
    "Build node images from their Dockerfile sources (one job per image; a deploy builds "
    "missing ones on its own). Wait with wait_for_job.",
    BuildIn,
    risk="write",
)
async def build_images(ctx: ToolContext, args: BuildIn) -> ToolResult:
    if not ctx.identity.is_staff:
        raise Forbidden("Only an instructor can do this", code="staff_only")
    images = ctx.runner.images
    assert images is not None
    with ctx.db() as db:
        started = images.start_builds(db, args.refs, fresh=args.fresh)
        rows = [f"- {(j.params or {}).get('ref')}: job [{j.id}] {j.status}" for j in started]
    return ToolResult("Builds:\n" + "\n".join(rows))


class NoIn(BaseModel):
    pass


@tool(
    "list_labs",
    "Every lab on this host's engine vs the database: tracked, orphan (no topology) or stale.",
    NoIn,
    tier="admin",
)
async def list_labs(ctx: ToolContext, args: NoIn) -> ToolResult:
    with ctx.db() as db:
        report = await reconcile.report(db, ctx.engine)
    lines = []
    for lab in report.get("labs") or []:
        owner = (lab.get("owner") or {}).get("username") if lab.get("owner") else None
        lines.append(
            f"- {lab.get('classification')}: {lab.get('lab_name') or lab.get('lab_hash')} "
            f"hash={lab.get('lab_hash')} topology={lab.get('topology_name') or '-'} "
            f"[{lab.get('topology_id') or '-'}] owner={owner or '-'}"
        )
    for lab in report.get("stale") or []:
        lines.append(
            f"- stale (no lab running): {lab.get('topology_name')} [{lab.get('topology_id')}] "
            f"hash={lab.get('lab_hash')}"
        )
    return ToolResult("\n".join(lines) or "No labs on the engine.")


class PurgeIn(BaseModel):
    lab_hash: str = Field(min_length=4, max_length=128)


@tool(
    "purge_lab",
    "Remove one lab's containers and networks from the host by its hash (from list_labs). "
    "Always asks the user.",
    PurgeIn,
    tier="admin",
    risk="risky",
    always_ask=True,
)
async def purge_lab(ctx: ToolContext, args: PurgeIn) -> ToolResult:
    with ctx.db() as db:
        result = await reconcile.purge(db, ctx.engine, args.lab_hash)
    return ToolResult(f"Purged lab {args.lab_hash}: {result}")
