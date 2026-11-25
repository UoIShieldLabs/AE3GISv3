"""Teaching tools: tutorials, reference docs, publishing a lesson."""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from api import presets as presets_api
from api.errors import Forbidden, NotFound
from config import BASE_DIR
from domain.agent_views import _dicts, clip, node_names, tutorial_text
from services import lessons, topologies
from services.agent.tools.base import ToolContext, ToolResult, tool
from services.agent.tools.common import TopologyArg, own_topology, view_topology

DOCS_DIR = BASE_DIR / "agent_docs"


class TutorialIn(TopologyArg):
    tutorial_id: str = Field(default="", description="Omit for every tutorial of the topology.")


@tool(
    "get_tutorial",
    "A topology's tutorials: each note and command cell in order (with ids), and what "
    "'Configure lab' runs first.",
    TutorialIn,
    tier="tutor",
)
async def get_tutorial(ctx: ToolContext, args: TutorialIn) -> ToolResult:
    with ctx.db() as db:
        topo = view_topology(db, ctx, args.topology_id)
        data = topo.data or {}
    tutorials = _dicts(data.get("tutorials"))
    if args.tutorial_id:
        tutorials = [t for t in tutorials if t.get("id") == args.tutorial_id]
        if not tutorials:
            raise NotFound("Tutorial")
    if not tutorials:
        return ToolResult("This topology has no tutorials.")
    names = node_names(data)
    return ToolResult("\n\n".join(tutorial_text(t, names) for t in tutorials))


def doc_topics() -> list[str]:
    topics = sorted(p.stem for p in DOCS_DIR.glob("*.md")) if DOCS_DIR.exists() else []
    return [*topics, "presets"]


class DocsIn(BaseModel):
    topic: str = Field(
        default="",
        description="A topic name; omit to list them. 'presets' lists the preset topologies.",
    )


@tool(
    "read_docs",
    "AE3GIS reference for the agent: how topologies, routing, images, tutorials and scenarios "
    "work, and the ICS scenario guide. Call with no topic to list the topics.",
    DocsIn,
    tier="tutor",
)
async def read_docs(ctx: ToolContext, args: DocsIn) -> ToolResult:
    topic = args.topic.strip().lower().removesuffix(".md")
    if not topic:
        return ToolResult("Topics: " + ", ".join(doc_topics()))
    if topic == "presets":
        rows = []
        for f in sorted(presets_api.PRESETS_DIR.glob("*.json")):
            try:
                preset = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            rows.append(
                f"- {f.stem}: {preset.get('name')} — {clip(str(preset.get('description') or ''), 300)}"
            )
        return ToolResult("Presets (create_topology preset=<id>):\n" + "\n".join(rows))
    path = (DOCS_DIR / f"{topic}.md").resolve()
    if path.parent != DOCS_DIR.resolve() or not path.is_file():
        return ToolResult(f"No topic '{topic}'. Topics: {', '.join(doc_topics())}", is_error=True)
    return ToolResult(clip(path.read_text(), 7_900))


class PublishIn(TopologyArg):
    published: bool = Field(description="True: students see it as a lesson; false: stop.")


@tool(
    "publish_topology",
    "Publish one of your topologies to your students as a lesson (each opens their own copy), "
    "or unpublish it (their copies and labs are removed). Asks the user.",
    PublishIn,
    risk="risky",
)
async def publish_topology(ctx: ToolContext, args: PublishIn) -> ToolResult:
    if not ctx.identity.is_staff:
        raise Forbidden("Only an instructor can do this", code="staff_only")
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        if args.published:
            topologies.check_publishable(db, topo)
        retired = topologies.set_published(db, topo, args.published)
        name, tid = topo.name, topo.id
    lessons.schedule(ctx.runner, ctx.engine, retired)
    verb = "Published" if args.published else "Unpublished"
    return ToolResult(
        f"{verb} {name} [{tid}].", ui=[{"type": "topology_meta_changed", "topology_id": tid}]
    )
