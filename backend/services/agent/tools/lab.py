"""Lab tools: status, deploy, destroy, jobs, commands in nodes, background runs,
scenario phases. Each starts the same job the matching API route starts."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from pydantic import BaseModel, Field

from api.errors import Conflict, Invalid
from db.models import Job
from domain.agent_views import clip, events_text, job_text, node_names, runtime_text
from domain.topology import find_container
from engine.base import EngineState
from services import accounts, activity, background, deployment, events, jobs, scenario
from services.agent.tools.base import ToolContext, ToolResult, tool
from services.agent.tools.common import (
    TopologyArg,
    job_for,
    own_topology,
    ui_runtime_changed,
)

# Longest a single tool call waits on a job or a command.
MAX_WAIT_S = 600
OUTPUT_CAP = 64_000


@tool(
    "get_lab_status",
    "A topology's lab: deploy status, the active job and its steps, what is running "
    "(captures, traffic, monitors, scenario, background runs), node states and recent events.",
    TopologyArg,
    tier="tutor",
)
async def get_lab_status(ctx: ToolContext, args: TopologyArg) -> ToolResult:
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        runtime = await deployment.runtime_view(db, ctx.engine, topo)
        recent = [
            {"ts": e.ts, "level": e.level, "type": e.type, "message": e.message}
            for e in events.list_events(db, topo.id, limit=200)
        ]
        names = node_names(topo.data or {})
        text = f"{topo.name} [{topo.id}]\n" + runtime_text(runtime, names)
        if recent:
            text += "\nRecent events:\n" + events_text(recent, 20)
    return ToolResult(text, data={"status": runtime.get("status")})


async def _wait_job(ctx: ToolContext, job_id: str, timeout: float) -> tuple[str, dict[str, Any]]:
    outcome, _ = await ctx.until(ctx.runner.wait(job_id), timeout)
    with ctx.db() as db:
        job = db.get(Job, job_id)
        data = jobs.job_to_dict(job) if job else {"id": job_id, "status": "unknown"}
    return outcome, data


def _log_tail(ctx: ToolContext, job_id: str, lines: int) -> str:
    if lines <= 0:
        return ""
    chunk = ctx.runner.logs.read(job_id, limit=max(4096, lines * 200))
    return "\n".join(chunk.text.splitlines()[-lines:])


def _waited(outcome: str, job: dict[str, Any], tail: str) -> str:
    text = job_text(job, tail)
    if outcome == "timeout":
        text += "\n(Still running: check again with wait_for_job.)"
    elif outcome == "stopped":
        text += "\n(Stopped waiting: the agent run was stopped; the job carries on.)"
    return text


class DeployIn(TopologyArg):
    wait: bool = Field(default=True, description="Wait for the deploy to finish.")
    timeout_s: int = Field(default=600, ge=5, le=MAX_WAIT_S)


@tool(
    "deploy",
    "Deploy a topology as a live lab (validate → images → plan → deploy → verify). Waits for it "
    "by default; images that need building are built first, which can take minutes.",
    DeployIn,
    risk="write",
)
async def deploy(ctx: ToolContext, args: DeployIn) -> ToolResult:
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)

        def admit() -> None:
            accounts.check_lab_cap(db, ctx.identity, topo, ctx.settings)

        job = deployment.start_deploy(db, ctx.runner, topo, admit=admit)
        job_id, tid = job.id, topo.id
    ui = [ui_runtime_changed(tid)]
    if not args.wait:
        return ToolResult(f"Deploy started: job [{job_id}].", data={"job_id": job_id}, ui=ui)
    outcome, data = await _wait_job(ctx, job_id, args.timeout_s)
    tail = _log_tail(ctx, job_id, 30) if data.get("status") == "failed" else ""
    return ToolResult(_waited(outcome, data, tail), data={"job_id": job_id}, ui=ui)


class DestroyIn(TopologyArg):
    save: bool = Field(
        default=False,
        description="Save every node's filesystem first; the next deploy resumes from it.",
    )
    wait: bool = True
    timeout_s: int = Field(default=300, ge=5, le=MAX_WAIT_S)


@tool(
    "destroy",
    "Destroy a topology's running lab (stops its captures and runs first). Asks the user.",
    DestroyIn,
    risk="risky",
)
async def destroy(ctx: ToolContext, args: DestroyIn) -> ToolResult:
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        job = deployment.start_destroy(db, ctx.runner, topo, save=args.save)
        job_id, tid = job.id, topo.id
    ui = [ui_runtime_changed(tid)]
    if not args.wait:
        return ToolResult(f"Destroy started: job [{job_id}].", data={"job_id": job_id}, ui=ui)
    outcome, data = await _wait_job(ctx, job_id, args.timeout_s)
    return ToolResult(_waited(outcome, data, ""), data={"job_id": job_id}, ui=ui)


class WaitIn(BaseModel):
    job_id: str
    timeout_s: int = Field(default=120, ge=1, le=MAX_WAIT_S)


@tool(
    "wait_for_job",
    "Wait for a job (deploy, destroy, build, capture, traffic, monitor, scenario run…) to "
    "finish, then return its steps and result.",
    WaitIn,
    tier="tutor",
)
async def wait_for_job(ctx: ToolContext, args: WaitIn) -> ToolResult:
    with ctx.db() as db:
        job_for(db, ctx, args.job_id)
    outcome, data = await _wait_job(ctx, args.job_id, args.timeout_s)
    tail = _log_tail(ctx, args.job_id, 30) if data.get("status") == "failed" else ""
    return ToolResult(_waited(outcome, data, tail), data={"status": data.get("status")})


class JobIn(BaseModel):
    job_id: str
    log_lines: int = Field(
        default=0, ge=0, le=400, description="Lines of the job's log to include."
    )


@tool(
    "get_job",
    "A job's status, steps, result (a run's totals, a capture's packet counts…) and "
    "optionally the end of its log.",
    JobIn,
    tier="tutor",
)
async def get_job(ctx: ToolContext, args: JobIn) -> ToolResult:
    with ctx.db() as db:
        job = job_for(db, ctx, args.job_id)
        data = jobs.job_to_dict(job)
    return ToolResult(job_text(data, _log_tail(ctx, args.job_id, args.log_lines)))


class StopIn(BaseModel):
    job_id: str


@tool(
    "stop_run",
    "Stop a capture, traffic run, monitor, scenario run or background run (it keeps what it "
    "recorded), or cancel a build.",
    StopIn,
    risk="write",
)
async def stop_run(ctx: ToolContext, args: StopIn) -> ToolResult:
    with ctx.db() as db:
        job = job_for(db, ctx, args.job_id, write=True)
        kind, status = job.kind, job.status
    if status not in jobs.ACTIVE:
        return ToolResult(f"{kind} [{args.job_id}] already ended ({status}).")
    if ctx.runner.request_stop(args.job_id, "Stopped by the agent", code="agent"):
        return ToolResult(f"Stopping {kind} [{args.job_id}].")
    if ctx.runner.cancel(args.job_id, reason="Cancelled by the agent"):
        return ToolResult(f"Cancelled {kind} [{args.job_id}].")
    raise Conflict(f"A {kind} job cannot be stopped", code="not_stoppable")


@tool(
    "list_activity",
    "What is running on a topology right now: captures, traffic runs, monitors, scenario and "
    "background runs, with their job ids.",
    TopologyArg,
    tier="tutor",
)
async def list_activity(ctx: ToolContext, args: TopologyArg) -> ToolResult:
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        items = activity.active_for_topology(db, topo.id)
    if not items:
        return ToolResult("Nothing is running.")
    return ToolResult(
        "\n".join(
            f"- {a['kind']} [{a['job_id']}] {a.get('label') or ''} {a.get('message') or ''}".rstrip()
            for a in items
        )
    )


class ExecIn(TopologyArg):
    node: str = Field(description="Device id (see get_topology).")
    command: str = Field(
        min_length=1, max_length=4000, description="Run through the node's sh -lc."
    )
    timeout_s: int = Field(default=60, ge=1, le=MAX_WAIT_S)


@tool(
    "run_in_node",
    "Run a shell command in a deployed node and return its exit code and output (cut to the "
    "last part when long). For something that must keep running (a server, a traffic loop), "
    "use start_background instead.",
    ExecIn,
    risk="write",
)
async def run_in_node(ctx: ToolContext, args: ExecIn) -> ToolResult:
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        if topo.status != "deployed" or not topo.engine_state:
            raise Conflict("Deploy the topology first", code="bad_state", status=topo.status)
        node = find_container(topo.data or {}, args.node)
        if node is None:
            raise Invalid(f"No device '{args.node}' in this topology", code="unknown_node")
        state = EngineState.from_dict(topo.engine_state)
        name = str(node.get("name") or args.node)
    assert state is not None
    out = bytearray()

    def emit(stream: str) -> Any:
        def feed(data: bytes) -> None:
            if len(out) < OUTPUT_CAP:
                out.extend(data)
            if ctx.on_output is not None:
                ctx.on_output(stream, data.decode("utf-8", "replace"))

        return feed

    if ctx.job_id:
        ctx.runner.log(ctx.job_id, f"exec on {args.node}: {args.command}")
    started = time.monotonic()
    try:
        stream = await ctx.engine.exec_stream(state, args.node, scenario.argv_for(args.command))
    except LookupError as exc:
        raise Conflict(str(exc), code="node_unavailable") from exc
    outcome, code = await ctx.until(stream.pump(emit("stdout"), emit("stderr")), args.timeout_s)
    if outcome != "done":
        await stream.remove()
    took = time.monotonic() - started
    output = bytes(out).decode("utf-8", "replace")
    head = {
        "done": f"exit {code}",
        "timeout": f"still running after {args.timeout_s}s (stopped waiting)",
        "stopped": "interrupted (the agent run was stopped)",
    }[outcome]
    text = f"{name}$ {args.command}\n[{head}, {took:.1f}s]\n" + (
        clip(output, 6000) or "(no output)"
    )
    return ToolResult(
        text,
        data={
            "node": args.node,
            "exit_code": code,
            "output": clip(output, 20_000),
            "outcome": outcome,
        },
    )


class BackgroundItem(BaseModel):
    node: str
    command: str = Field(min_length=1, max_length=4000)


class BackgroundIn(TopologyArg):
    items: list[BackgroundItem] = Field(min_length=1, max_length=32)
    label: str = Field(default="", max_length=80)


@tool(
    "start_background",
    "Start commands that keep running in their nodes (servers, traffic loops) until stopped "
    "with stop_run. One background run per topology at a time.",
    BackgroundIn,
    risk="write",
)
async def start_background(ctx: ToolContext, args: BackgroundIn) -> ToolResult:
    req = {
        "items": [
            {"id": f"agent-{i}", "containerId": it.node, "command": it.command}
            for i, it in enumerate(args.items)
        ],
        "label": args.label or "Agent background run",
        "tag": "agent",
    }
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        job = background.start_run(db, ctx.runner, topo, req)
        job_id = job.id
    await asyncio.sleep(1.0)
    with ctx.db() as db:
        data = jobs.job_to_dict(db.get(Job, job_id))
    return ToolResult(
        f"Background run [{job_id}] started ({len(args.items)} command(s)). Stop it with stop_run.\n"
        + job_text(data),
        data={"job_id": job_id},
    )


class PhaseIn(TopologyArg):
    phase_id: str
    wait: bool = True
    timeout_s: int = Field(default=300, ge=5, le=MAX_WAIT_S)


@tool(
    "run_scenario_phase",
    "Run every step of a stored scenario phase on the deployed lab, in order, and return each "
    "step's output.",
    PhaseIn,
    risk="write",
)
async def run_scenario_phase(ctx: ToolContext, args: PhaseIn) -> ToolResult:
    with ctx.db() as db:
        topo = own_topology(db, ctx, args.topology_id)
        job = scenario.start_phase(db, ctx.runner, topo, args.phase_id, label="Agent")
        job_id = job.id
    if not args.wait:
        return ToolResult(f"Scenario run [{job_id}] started.", data={"job_id": job_id})
    outcome, data = await _wait_job(ctx, job_id, args.timeout_s)
    return ToolResult(_waited(outcome, data, ""), data={"job_id": job_id})
