"""The agent sidebar: status, chats, sending messages, approvals, and a run's
live stream (``services.agent``). Stop a run with ``POST /jobs/{id}/stop``.

Who may do what (``services.agent.access``): a chat is read by its owner, the
owner's instructor and admins; only its owner sends to it, approves its tool
calls, changes or deletes it (admins may delete any).
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from api import access
from api.access import ws_chat_guard
from api.deps import get_db, get_runner, get_settings
from api.errors import Conflict, Forbidden, NotFound
from api.live_ws import ClientGone, forward, unless_disconnected
from api.schemas import (
    AgentChatDetail,
    AgentChatIn,
    AgentChatOut,
    AgentChatPatch,
    AgentDecisionIn,
    AgentMessageOut,
    AgentSendIn,
    AgentSendOut,
    AgentStatusOut,
)
from auth import current_identity
from config import Settings
from db.models import AgentChat, Job, Topology
from services import accounts, live
from services.accounts import Identity
from services.agent import mcp as agent_mcp
from services.agent import runner as agent_runner
from services.agent import store
from services.agent.access import agent_mode, can_drive_chat, can_read_chat
from services.agent.llm import describe
from services.jobs import JobRunner
from services.live import LiveHub

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


def _mode_or_403(db: Session, identity: Identity, settings: Settings) -> str:
    if not settings.agent_enabled:
        raise Conflict("The agent is not configured on this instance", code="agent_off")
    mode = agent_mode(db, identity)
    if mode is None:
        raise Forbidden("Your instructor hasn't turned the tutor on", code="tutor_off")
    return mode


def _chat(db: Session, identity: Identity, chat_id: str, *, drive: bool = False) -> AgentChat:
    chat = db.get(AgentChat, chat_id)
    if chat is None or not can_read_chat(db, identity, chat):
        raise NotFound("Chat")
    if drive and not can_drive_chat(identity, chat):
        raise Forbidden("Only the chat's owner can do this", code="not_owner")
    return chat


def _chat_out(db: Session, chats: list[AgentChat]) -> list[dict[str, Any]]:
    known = accounts.owners(db, {c.owner_id for c in chats if c.owner_id})
    topo_ids = {c.topology_id for c in chats if c.topology_id}
    names = (
        dict(db.execute(select(Topology.id, Topology.name).where(Topology.id.in_(topo_ids))).all())
        if topo_ids
        else {}
    )
    out = []
    for c in chats:
        out.append(
            {
                "id": c.id,
                "title": c.title,
                "mode": c.mode,
                "topology_id": c.topology_id,
                "topology_name": names.get(c.topology_id),
                "auto_approve": bool(c.auto_approve),
                "owner": accounts.owner_out(known, c.owner_id),
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "active_job_id": agent_runner.active_job_id(db, c.id),
            }
        )
    return out


@router.get("/status", response_model=AgentStatusOut)
def status(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    identity: Identity = Depends(current_identity),
):
    """Whether the agent is configured, and what the caller gets."""
    info = describe(settings)
    if not settings.agent_enabled:
        return AgentStatusOut(enabled=False, reason="agent_off", mcp_path=agent_mcp.PATH)
    mode = agent_mode(db, identity)
    return AgentStatusOut(
        enabled=True,
        provider=info["provider"],
        model=info["model"],
        mode=mode,  # type: ignore[arg-type]
        reason=None if mode else "tutor_off",
        mcp_path=agent_mcp.PATH,
    )


@router.get("/chats", response_model=list[AgentChatOut])
def list_chats(
    topology_id: str | None = Query(default=None, max_length=64),
    owner: str | None = Query(default=None, description="Staff: a student's chats", max_length=64),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
):
    """Your chats, newest first (``topology_id`` narrows them). Staff pass
    ``owner`` to read one of their students' chats."""
    stmt = select(AgentChat).order_by(AgentChat.updated_at.desc()).limit(limit)
    if owner and owner != identity.user_id:
        allowed = identity.is_admin or (
            identity.is_staff and accounts.teacher_of(db, owner) == identity.user_id
        )
        if not allowed:
            raise NotFound("User")
        stmt = stmt.where(AgentChat.owner_id == owner)
    else:
        stmt = (
            stmt.where(AgentChat.owner_id == identity.user_id)
            if identity.user_id
            else stmt.where(AgentChat.owner_id.is_(None))
        )
    if topology_id:
        stmt = stmt.where(AgentChat.topology_id == topology_id)
    return _chat_out(db, list(db.scalars(stmt)))


@router.post("/chats", response_model=AgentChatOut, status_code=201)
def create_chat(
    body: AgentChatIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    identity: Identity = Depends(current_identity),
):
    """A new chat, optionally on a topology the caller can see."""
    mode = _mode_or_403(db, identity, settings)
    topology_id = None
    if body.topology_id:
        topo = access.check_view(db, identity, db.get(Topology, body.topology_id))
        topology_id = topo.id
    chat = store.create_chat(
        db, owner_id=identity.user_id, mode=mode, topology_id=topology_id, title=body.title
    )
    return _chat_out(db, [chat])[0]


@router.get("/chats/{chat_id}", response_model=AgentChatDetail)
def get_chat(
    chat_id: str,
    after: int = Query(default=0, ge=0, description="Only messages after this seq"),
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
):
    chat = _chat(db, identity, chat_id)
    out = _chat_out(db, [chat])[0]
    return {
        **out,
        "messages": [store.message_out(m) for m in store.messages(db, chat.id, after=after)],
        "pending_approvals": agent_runner.pending_for(out["active_job_id"]),
        "can_send": can_drive_chat(identity, chat),
    }


@router.patch("/chats/{chat_id}", response_model=AgentChatOut)
def update_chat(
    chat_id: str,
    body: AgentChatPatch,
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
):
    """Rename a chat, or let its risky tool calls run without asking
    (``auto_approve``; deletes always ask). Applies to a run in progress too."""
    chat = _chat(db, identity, chat_id, drive=True)
    if body.title is not None:
        chat.title = body.title.strip()
    if body.auto_approve is not None:
        chat.auto_approve = body.auto_approve
    db.commit()
    db.refresh(chat)
    return _chat_out(db, [chat])[0]


@router.delete("/chats/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: str,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    identity: Identity = Depends(current_identity),
):
    """Delete a chat and its messages (its run, if any, is stopped first)."""
    chat = db.get(AgentChat, chat_id)
    if chat is None or not can_read_chat(db, identity, chat):
        raise NotFound("Chat")
    if not (can_drive_chat(identity, chat) or identity.is_admin):
        raise Forbidden("Only the chat's owner can do this", code="not_owner")
    job_id = agent_runner.active_job_id(db, chat.id)
    if job_id:
        runner.request_stop(job_id, "Chat deleted", code="user")
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(runner.wait(job_id), timeout=15)
    db.delete(db.get(AgentChat, chat_id))
    db.commit()
    return Response(status_code=204)


@router.post("/chats/{chat_id}/messages", response_model=AgentSendOut, status_code=202)
def send_message(
    chat_id: str,
    body: AgentSendIn,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    settings: Settings = Depends(get_settings),
    identity: Identity = Depends(current_identity),
):
    """Send a message: starts a run (202 + its job), or, while one is running,
    hands the message to it (``queued``: the agent reads it at its next turn)."""
    chat = _chat(db, identity, chat_id, drive=True)
    mode = _mode_or_403(db, identity, settings)
    if chat.mode == "full" and mode != "full":
        raise Forbidden("This chat needs the full agent", code="mode_changed")
    context = body.context.model_dump(exclude_none=True) if body.context else None
    if context and context.get("topology_id"):
        # Only a topology the caller can see is named to the agent.
        topo = db.get(Topology, context["topology_id"])
        if topo is None or not access.can_view(db, identity, topo):
            context.pop("topology_id", None)
            context.pop("topology_name", None)
    job, queued, msg = agent_runner.send_message(db, runner, chat, identity, body.text, context)
    return AgentSendOut(
        job_id=job.id, queued=queued, message=AgentMessageOut(**store.message_out(msg))
    )


@router.post("/chats/{chat_id}/approvals/{call_id}", status_code=204)
async def decide(
    chat_id: str,
    call_id: str,
    body: AgentDecisionIn,
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
):
    """Approve or decline a tool call the agent is waiting on."""
    chat = _chat(db, identity, chat_id, drive=True)
    job_id = agent_runner.active_job_id(db, chat.id)
    if not job_id or not agent_runner.decide(job_id, call_id, body.approve):
        raise Conflict("Nothing is waiting for that approval", code="no_pending_approval")
    return Response(status_code=204)


@router.websocket("/ws/{chat_id}/{job_id}")
async def agent_live(
    websocket: WebSocket,
    chat_id: str,
    job_id: str,
    token: str | None = Query(default=None),
):
    """A run's live stream. Messages (JSON): ``hello`` {job}, ``run``, ``turn``,
    ``text_delta`` / ``thinking_delta`` {text}, ``tool_pending`` {name},
    ``tool_start`` {call_id, name, input}, ``tool_output`` {call_id, stream,
    text}, ``tool_end`` {call_id, is_error, text}, ``approval`` {call_id, name,
    status}, ``ui`` {action}, ``message`` {message} (a persisted row), ``end``."""
    if not await ws_chat_guard(websocket, token, chat_id):
        return
    hub: LiveHub = websocket.app.state.live
    session_factory = websocket.app.state.session_factory

    def job_info() -> dict[str, Any] | None:
        with session_factory() as db:
            job = db.get(Job, job_id)
            if (
                not job
                or job.kind != agent_runner.KIND
                or (job.params or {}).get("chat_id") != chat_id
            ):
                return None
            return {"id": job.id, "status": job.status, "result": job.result}

    def is_active() -> bool:
        with session_factory() as db:
            job = db.get(Job, job_id)
            return bool(job and job.is_active)

    if await asyncio.to_thread(job_info) is None:
        await websocket.close(code=4004, reason="Run not found")
        return
    await websocket.accept()
    try:
        try:
            channel = await unless_disconnected(
                websocket, live.wait_for_channel(hub, job_id, is_active)
            )
        except ClientGone:
            return
        # A run that just ended keeps its (closed) channel a while: replay it.
        channel = channel or hub.get(job_id)
        sub = None
        backlog: list[dict[str, Any]] = []
        if channel is not None:
            sub, backlog = channel.subscribe(maxsize=2048)
        await websocket.send_json({"type": "hello", "job": await asyncio.to_thread(job_info)})
        for msg in backlog:
            await websocket.send_json(msg)
        if sub is None:
            await websocket.send_json({"type": "end", "status": "done"})
            await websocket.close()
            return
        try:
            await forward(websocket, sub)
        finally:
            channel.unsubscribe(sub)
        with contextlib.suppress(Exception):
            await websocket.close()
    except WebSocketDisconnect:
        pass
