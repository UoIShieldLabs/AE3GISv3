"""The agent's tool registry: what a tool is, who may call it, and how it runs.

A tool is an async handler over a typed input (a pydantic model: its JSON schema
is what the model sees) that calls the existing services and the plain access
checks in ``api.access`` — tools never re-implement permissions. The same
registry serves the in-app agent and the MCP endpoint.

- ``tier``: ``tutor`` (read-only, also offered to students in tutor mode),
  ``full`` (staff and accounts-off), ``admin``.
- ``risk``: ``read`` / ``write`` / ``risky``. A risky call waits for the user's
  approval in-app unless the chat auto-approves; ``always_ask`` ones ask anyway.
- ``surface``: ``all``, or ``app`` for tools that drive the browser (MCP has none).
"""

from __future__ import annotations

import asyncio
import copy
import logging
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session, sessionmaker

from api.errors import ApiError
from domain.agent_views import clip
from domain.topology_edit import EditError
from services.accounts import Identity

if TYPE_CHECKING:
    from config import Settings
    from engine.base import DeploymentEngine
    from services.jobs import JobRunner

log = logging.getLogger(__name__)

Tier = Literal["tutor", "full", "admin"]
Risk = Literal["read", "write", "risky"]
Mode = Literal["full", "tutor"]


@dataclass
class ToolResult:
    """``text`` goes to the model (clipped); ``data`` to the UI's tool card;
    ``ui`` are browser actions (navigate, open a view, reload a topology)."""

    text: str
    data: Any = None
    ui: list[dict[str, Any]] = field(default_factory=list)
    is_error: bool = False


@dataclass
class ToolContext:
    identity: Identity
    runner: JobRunner
    engine: DeploymentEngine
    settings: Settings
    session_factory: sessionmaker
    # The agent run's job (None over MCP): exec output is logged against it.
    job_id: str | None = None
    # Live command output for the UI (in-app only).
    on_output: Callable[[str, str], None] | None = None
    # The topology the user has open (default for tools that take one).
    topology_id: str | None = None
    # Set when the agent run is stopped: long waits inside a tool end early.
    stop: asyncio.Event | None = None

    @contextmanager
    def db(self) -> Iterator[Session]:
        with self.session_factory() as session:
            yield session

    async def until(self, aw: Awaitable[Any], timeout: float) -> tuple[str, Any]:
        """Await ``aw`` for at most ``timeout`` seconds, or until the run stops.
        Returns ``("done", value)``, ``("timeout", None)`` or ``("stopped", None)``;
        ``aw`` is cancelled unless it finished."""
        task = asyncio.ensure_future(aw)
        waits: set[asyncio.Future[Any]] = {task}
        stopper = asyncio.ensure_future(self.stop.wait()) if self.stop is not None else None
        if stopper is not None:
            waits.add(stopper)
        try:
            done, _ = await asyncio.wait(
                waits, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            if stopper is not None:
                stopper.cancel()
        if task in done:
            return "done", task.result()
        task.cancel()
        return ("stopped" if stopper is not None and stopper in done else "timeout"), None


Handler = Callable[[ToolContext, Any], Awaitable[ToolResult]]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input: type[BaseModel]
    handler: Handler
    tier: Tier = "full"
    risk: Risk = "read"
    surface: Literal["all", "app"] = "all"
    always_ask: bool = False

    def input_schema(self) -> dict[str, Any]:
        return inline_schema(self.input.model_json_schema())


REGISTRY: dict[str, Tool] = {}


def tool(
    name: str,
    description: str,
    input: type[BaseModel],
    *,
    tier: Tier = "full",
    risk: Risk = "read",
    surface: Literal["all", "app"] = "all",
    always_ask: bool = False,
) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        if name in REGISTRY:
            raise RuntimeError(f"tool {name} registered twice")
        REGISTRY[name] = Tool(name, description.strip(), input, fn, tier, risk, surface, always_ask)
        return fn

    return register


def tools_for(
    identity: Identity, mode: Mode, *, surface: Literal["app", "mcp"] = "app"
) -> list[Tool]:
    """The tools this caller gets, sorted by name (a stable list keeps prompt
    caches warm). Tutor mode: read-only tutor tools only."""
    load_all()
    out: list[Tool] = []
    for t in REGISTRY.values():
        if surface == "mcp" and t.surface == "app":
            continue
        if mode == "tutor":
            if t.tier != "tutor" or t.risk != "read":
                continue
        elif t.tier == "admin" and not identity.is_admin:
            continue
        elif t.tier == "full" and not identity.is_staff:
            continue
        out.append(t)
    return sorted(out, key=lambda t: t.name)


def needs_approval(t: Tool, *, auto_approve: bool) -> bool:
    if t.always_ask:
        return True
    return t.risk == "risky" and not auto_approve


async def run_tool(t: Tool, ctx: ToolContext, args: Any) -> ToolResult:
    """Validate ``args`` and run the tool; every failure becomes an error result
    the model can read (and retry from), never an exception."""
    try:
        parsed = t.input.model_validate(args if isinstance(args, dict) else {})
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or 'input'}: {e['msg']}" for e in exc.errors()[:8]
        )
        return ToolResult(f"Invalid input for {t.name}: {problems}", is_error=True)
    try:
        result = await t.handler(ctx, parsed)
    except ApiError as exc:
        extra = {k: v for k, v in exc.extra.items() if k != "diagnostics"}
        diags = exc.extra.get("diagnostics")
        text = f"Error ({exc.code}): {exc.detail}"
        if extra:
            text += f" {extra}"
        if diags:
            text += "\n" + "\n".join(
                f"- {d.get('severity')}: {d.get('message')}" for d in diags[:20]
            )
        return ToolResult(clip(text), is_error=True)
    except EditError as exc:
        return ToolResult(f"Edit rejected, nothing was changed: {exc}", is_error=True)
    except (LookupError, ValueError) as exc:
        return ToolResult(f"Error: {exc}", is_error=True)
    except Exception:
        log.exception("agent tool %s failed", t.name)
        return ToolResult(
            f"Error: {t.name} failed unexpectedly (see the server log)", is_error=True
        )
    result.text = clip(result.text)
    return result


def inline_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """A JSON schema without ``$ref``/``$defs`` (some model servers reject refs)."""
    defs = schema.get("$defs", {})

    def resolve(node: Any, depth: int = 0) -> Any:
        if depth > 12:
            return {}
        if isinstance(node, dict):
            if "$ref" in node:
                target = defs.get(str(node["$ref"]).rsplit("/", 1)[-1], {})
                merged = {**copy.deepcopy(target), **{k: v for k, v in node.items() if k != "$ref"}}
                return resolve(merged, depth + 1)
            # Drop schema metadata ("title": "Foo"), not a property named title,
            # and OpenAPI's discriminator (its mapping points at the $defs removed here).
            return {
                k: resolve(v, depth)
                for k, v in node.items()
                if k != "$defs"
                and not (k == "title" and isinstance(v, str))
                and not (k == "discriminator" and isinstance(v, dict) and "propertyName" in v)
            }
        if isinstance(node, list):
            return [resolve(v, depth) for v in node]
        return node

    out = resolve(schema)
    out.setdefault("type", "object")
    out.setdefault("properties", {})
    return out


_LOADED = False


def load_all() -> None:
    """Import every tool module once (they register on import)."""
    global _LOADED
    if _LOADED:
        return
    from services.agent.tools import (  # noqa: F401
        admin,
        lab,
        observe,
        teaching,
        topologies,
        ui,
    )

    _LOADED = True
