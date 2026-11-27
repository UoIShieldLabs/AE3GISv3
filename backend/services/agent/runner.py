"""An agent run: a stoppable job (kind ``agent``, subject ``agent:<chat>``) that
loops model → tools → model until the model is done, the user stops it, or a
limit is hit.

- **One run per chat.** A message sent while a run is active is appended to the
  chat and picked up at the next turn (steering), not a new run.
- **As the user.** The run re-resolves its user at start and calls tools with that
  identity; it never holds a token. The tools are the caller's (``tools_for``).
- **Approvals.** A risky tool call publishes an ``approval`` and waits for the
  owner's decision (``decide``), a stop, or ``agent_approval_timeout_s``.
- **Always a valid transcript.** Every tool call in an assistant turn gets a
  result row (run, declined or skipped), so a stopped chat can continue.
- **Live.** Text deltas, tool calls and output, approvals and UI actions go to the
  job's live channel (``api.agent`` serves it over a WebSocket); persisted rows
  are published as ``message`` so a viewer that joins late catches up.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from api.errors import Conflict
from db.models import AgentChat, Job, User
from domain.agent_views import clip
from services import accounts, jobs
from services.accounts import OPEN_ADMIN, Identity
from services.agent import store
from services.agent.access import agent_mode
from services.agent.llm import ProviderError, ToolSpec, make_provider
from services.agent.prompts import context_note, system_prompt
from services.agent.tools import ToolContext, ToolResult, needs_approval, run_tool, tools_for
from services.jobs import JobRunner
from services.live import Channel

log = logging.getLogger(__name__)

KIND = "agent"
UI_TEXT_CHARS = 4000


def subject(chat_id: str) -> str:
    return f"agent:{chat_id}"


# ── approvals (in memory: a pending approval lives as long as its run) ──


@dataclass
class Pending:
    call_id: str
    name: str
    input: Any
    future: asyncio.Future = field(repr=False)


_pending: dict[str, dict[str, Pending]] = {}


def pending_for(job_id: str | None) -> list[dict[str, Any]]:
    if not job_id:
        return []
    return [
        {"call_id": p.call_id, "name": p.name, "input": p.input}
        for p in _pending.get(job_id, {}).values()
    ]


def decide(job_id: str, call_id: str, approve: bool) -> bool:
    """The owner's answer to a pending approval (call on the app loop)."""
    p = _pending.get(job_id, {}).get(call_id)
    if p is None or p.future.done():
        return False
    p.future.set_result(approve)
    return True


# ── starting a run (from a request) ──


def send_message(
    db: Session,
    runner: JobRunner,
    chat: AgentChat,
    identity: Identity,
    text: str,
    context: dict[str, Any] | None,
) -> tuple[Job, bool, Any]:
    """Append the user's message; start a run, or hand it to the active one.
    Returns (job, queued_into_active_run, message)."""
    text = text.strip()
    if not text:
        raise Conflict("Write a message first", code="empty_message")
    content = {
        "text": text,
        "context": context or None,
        "note": context_note(context, username=identity.username, role=identity.role),
    }
    with runner.admission:
        active = jobs.active_for_subject(db, subject(chat.id))
        if active is not None:
            msg = store.append(db, chat.id, "user", content, job_id=active.id)
            return active, True, msg
        job = jobs.create_job(
            db,
            KIND,
            subject=subject(chat.id),
            params={"chat_id": chat.id, "user_id": identity.user_id, "mode": chat.mode},
        )
        chat.last_job_id = job.id
        if chat.title == store.DEFAULT_TITLE:
            chat.title = store.title_from(text)
        db.commit()
        msg = store.append(db, chat.id, "user", content, job_id=job.id)
    db.refresh(job)
    runner.submit(job.id)
    return job, False, msg


def active_job_id(db: Session, chat_id: str) -> str | None:
    job = jobs.active_for_subject(db, subject(chat_id))
    return job.id if job else None


# ── the job ──


class _Run:
    def __init__(self, runner: JobRunner, job_id: str) -> None:
        self.runner = runner
        self.job_id = job_id
        self.settings = runner.settings
        assert self.settings is not None and runner.live is not None
        self.channel: Channel = runner.live.open(job_id)
        self.stop = runner.stop_event(job_id)
        self.usage: dict[str, int] = {}
        self.steps = 0
        self.published = 0  # highest message seq sent to the channel
        self.ended = "done"

    # helpers
    def db(self) -> Session:
        return self.runner.session_factory()

    def publish(self, msg: dict[str, Any], *, replay: bool = True) -> None:
        self.channel.publish(msg, replay=replay)

    def save(
        self, chat_id: str, role: str, content: dict[str, Any], raw: dict | None = None
    ) -> None:
        with self.db() as db:
            msg = store.append(db, chat_id, role, content, raw=raw, job_id=self.job_id)
            self.published = max(self.published, msg.seq)
            self.publish({"type": "message", "message": jsonable(store.message_out(msg))})

    def note(self, chat_id: str, kind: str, text: str) -> None:
        self.save(chat_id, "note", {"kind": kind, "text": text})

    def add_usage(self, usage: dict[str, int]) -> None:
        for k, v in usage.items():
            self.usage[k] = self.usage.get(k, 0) + int(v or 0)

    async def until_stopped(self, aw: Any, timeout: float | None = None) -> tuple[str, Any]:
        task = asyncio.ensure_future(aw)
        stopper = asyncio.ensure_future(self.stop.wait())
        try:
            done, _ = await asyncio.wait(
                {task, stopper}, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            stopper.cancel()
        if task in done:
            return "done", task.result()
        task.cancel()
        with contextlib.suppress(BaseException):
            await task
        return ("stopped" if stopper in done else "timeout"), None

    # approvals
    async def ask(self, call: Any, tool_name: str) -> str:
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        _pending.setdefault(self.job_id, {})[call.id] = Pending(call.id, tool_name, call.input, fut)
        self.publish(
            {
                "type": "approval",
                "call_id": call.id,
                "name": tool_name,
                "input": call.input,
                "status": "pending",
            }
        )
        try:
            outcome, approved = await self.until_stopped(
                fut, timeout=float(self.settings.agent_approval_timeout_s)
            )
        finally:
            _pending.get(self.job_id, {}).pop(call.id, None)
        status = {
            "done": "approved" if approved else "denied",
            "timeout": "expired",
            "stopped": "stopped",
        }[outcome]
        self.publish({"type": "approval", "call_id": call.id, "name": tool_name, "status": status})
        return status


def jsonable(value: Any) -> Any:
    """Datetimes to ISO strings, for the live channel (JSON over a WebSocket)."""
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _identity(db: Session, user_id: str | None, auth_required: bool) -> Identity | None:
    if user_id is None:
        return None if auth_required else OPEN_ADMIN
    user = db.get(User, user_id)
    return accounts.identity_of(db, user) if user is not None else None


def _open_topology(rows: list[Any], fallback: str | None) -> str | None:
    for m in reversed(rows):
        if m.role == "user":
            ctx = (m.content or {}).get("context") or {}
            return ctx.get("topology_id") or fallback
    return fallback


async def run_agent(runner: JobRunner, job_id: str) -> None:
    run = _Run(runner, job_id)
    settings = run.settings
    with run.db() as db:
        job = db.get(Job, job_id)
        params = dict(job.params or {}) if job else {}
        chat = db.get(AgentChat, params.get("chat_id"))
        chat_id = chat.id if chat else ""
        mode = chat.mode if chat else "full"
        identity = _identity(db, params.get("user_id"), settings.auth_required)
        allowed = agent_mode(db, identity) if identity is not None else None
        rows = store.messages(db, chat_id) if chat else []
        run.published = max((m.seq for m in rows), default=0)
    run.publish({"type": "run", "status": "running", "job_id": job_id, "chat_id": chat_id})
    try:
        if chat is None:
            run.ended = "missing"
            return
        if identity is None or allowed is None or (mode == "full" and allowed != "full"):
            run.ended = "no_access"
            run.note(chat_id, "error", "You no longer have access to the agent.")
            return
        await _loop(run, chat_id, mode, identity)
    except ProviderError as exc:
        run.ended = "error"
        run.note(chat_id, "error", str(exc))
    except Exception:
        log.exception("agent run %s failed", job_id)
        run.ended = "error"
        run.note(chat_id, "error", "The agent failed unexpectedly (see the server log).")
        raise
    finally:
        for p in list(_pending.pop(job_id, {}).values()):
            if not p.future.done():
                p.future.cancel()
        runner.set_result(job_id, {"usage": run.usage, "steps": run.steps, "ended": run.ended})
        run.channel.close(
            {"type": "end", "status": run.ended, "usage": run.usage, "steps": run.steps}
        )
        assert runner.live is not None
        runner.live.prune()


async def _loop(run: _Run, chat_id: str, mode: str, identity: Identity) -> None:
    settings = run.settings
    tutor = mode == "tutor"
    provider = make_provider(settings, tutor=tutor)
    tools = tools_for(identity, mode)  # type: ignore[arg-type]
    by_name = {t.name: t for t in tools}
    specs = [ToolSpec(t.name, t.description, t.input_schema()) for t in tools]
    system = system_prompt(mode)
    max_steps = settings.agent_tutor_max_steps if tutor else settings.agent_max_steps
    deadline = time.monotonic() + settings.agent_max_run_seconds
    run.runner.log(run.job_id, f"agent run: {provider.name}/{provider.model}, {len(tools)} tools")

    while True:
        with run.db() as db:
            rows = store.messages(db, chat_id)
            history = store.history(db, chat_id)
            chat = db.get(AgentChat, chat_id)
            fallback_topology = chat.topology_id if chat else None
        # Messages the user sent while we worked (steering): show them to viewers.
        for m in rows:
            if m.seq > run.published:
                run.publish({"type": "message", "message": jsonable(store.message_out(m))})
                run.published = m.seq
        open_topology = _open_topology(rows, fallback_topology)
        if run.stop.is_set():
            run.ended = "stopped"
            run.note(chat_id, "stopped", "Stopped.")
            return
        if time.monotonic() > deadline:
            run.ended = "limit"
            run.note(
                chat_id, "limit", "This run reached its time limit; send a message to carry on."
            )
            return

        run.publish({"type": "turn", "status": "thinking"}, replay=False)

        def on_event(kind: str, text: str) -> None:
            if kind == "text":
                run.publish({"type": "text_delta", "text": text}, replay=False)
            elif kind == "thinking":
                run.publish({"type": "thinking_delta", "text": text}, replay=False)
            elif kind == "tool":
                run.publish({"type": "tool_pending", "name": text}, replay=False)

        outcome, turn = await run.until_stopped(
            provider.complete(system=system, history=history, tools=specs, on_event=on_event)
        )
        if outcome != "done":
            run.ended = "stopped"
            run.note(chat_id, "stopped", "Stopped.")
            return
        run.add_usage(turn.usage)
        run.save(chat_id, "assistant", turn.content(), raw=turn.raw)
        if turn.stop_reason == "refusal":
            run.ended = "refusal"
            run.note(chat_id, "refusal", turn.refusal or "The model declined this request.")
            if turn.tool_calls:  # a refusal can cut a call off: answer it, never run it
                run.save(
                    chat_id,
                    "tool",
                    {
                        "results": [
                            _skip(c, "not run (the model declined)") for c in turn.tool_calls
                        ]
                    },
                )
            return
        if not turn.tool_calls:
            with run.db() as db:
                newer = [
                    m for m in store.messages(db, chat_id, after=run.published) if m.role == "user"
                ]
            if newer:
                continue
            return
        if turn.stop_reason == "max_tokens":
            run.save(
                chat_id,
                "tool",
                {
                    "results": [
                        _skip(
                            c,
                            "Your reply was cut off at the length limit before this call was complete; send it again with less input.",
                        )
                        for c in turn.tool_calls
                    ]
                },
            )
            continue

        results: list[dict[str, Any]] = []
        for call in turn.tool_calls:
            if run.stop.is_set():
                results.append(_skip(call, "not run: the user stopped the agent"))
                continue
            if run.steps >= max_steps or time.monotonic() > deadline:
                results.append(_skip(call, "not run: this run's limit was reached"))
                continue
            results.append(await _call(run, call, by_name, identity, open_topology, chat_id))
            run.steps += 1
        run.save(chat_id, "tool", {"results": results})
        if run.stop.is_set():
            run.ended = "stopped"
            run.note(chat_id, "stopped", "Stopped.")
            return
        if run.steps >= max_steps:
            run.ended = "limit"
            run.note(
                chat_id,
                "limit",
                f"This run reached its limit of {max_steps} tool calls; send a message to carry on.",
            )
            return


def _skip(call: Any, why: str) -> dict[str, Any]:
    return {"tool_call_id": call.id, "name": call.name, "text": why, "is_error": True}


async def _call(
    run: _Run,
    call: Any,
    by_name: dict[str, Any],
    identity: Identity,
    open_topology: str | None,
    chat_id: str,
) -> dict[str, Any]:
    tool = by_name.get(call.name)
    run.publish({"type": "tool_start", "call_id": call.id, "name": call.name, "input": call.input})
    run.runner.log(run.job_id, f"tool {call.name}")
    result: ToolResult
    if tool is None:
        result = ToolResult(f"There is no tool named {call.name}.", is_error=True)
    else:
        with run.db() as db:
            chat = db.get(AgentChat, chat_id)
            auto = bool(chat.auto_approve) if chat else False
        status = "approved"
        if needs_approval(tool, auto_approve=auto):
            status = await run.ask(call, tool.name)
        if status == "approved":
            ctx = ToolContext(
                identity=identity,
                runner=run.runner,
                engine=run.runner.engine,
                settings=run.settings,
                session_factory=run.runner.session_factory,
                job_id=run.job_id,
                on_output=lambda stream, text: run.channel.publish_threadsafe(
                    {"type": "tool_output", "call_id": call.id, "stream": stream, "text": text},
                    replay=False,
                ),
                topology_id=open_topology,
                stop=run.stop,
            )
            result = await run_tool(tool, ctx, call.input)
        else:
            why = {
                "denied": "The user declined this action. Don't retry it another way; ask what they want instead.",
                "expired": "Nobody answered the approval request in time, so this did not run.",
                "stopped": "Not run: the user stopped the agent.",
            }[status]
            result = ToolResult(why, is_error=True)
    for action in result.ui:
        run.publish({"type": "ui", "action": action}, replay=False)
    run.publish(
        {
            "type": "tool_end",
            "call_id": call.id,
            "name": call.name,
            "is_error": result.is_error,
            "text": clip(result.text, UI_TEXT_CHARS),
        }
    )
    return {
        "tool_call_id": call.id,
        "name": call.name,
        "text": result.text,
        "is_error": result.is_error,
    }


def register(runner: JobRunner) -> None:
    runner.register(KIND, run_agent, stoppable=True)
