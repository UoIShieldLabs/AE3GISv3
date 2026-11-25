"""Running agent tools against a test app (on its loop, as a given caller)."""

from __future__ import annotations

from typing import Any

from db.models import User
from services import accounts
from services.accounts import OPEN_ADMIN, Identity
from services.agent.tools import REGISTRY, ToolContext, ToolResult, load_all, run_tool


def identity_of(app, user_id: str | None) -> Identity:
    if user_id is None:
        return OPEN_ADMIN
    with app.state.session_factory() as db:
        return accounts.identity_of(db, db.get(User, user_id))


def tool_context(app, identity: Identity, **extra: Any) -> ToolContext:
    st = app.state
    return ToolContext(
        identity=identity,
        runner=st.runner,
        engine=st.engine,
        settings=st.settings,
        session_factory=st.session_factory,
        **extra,
    )


def call_tool(
    client, app, tool_name: str, identity: Identity = OPEN_ADMIN, /, **args: Any
) -> ToolResult:
    load_all()
    ctx = tool_context(app, identity)

    async def go() -> ToolResult:
        return await run_tool(REGISTRY[tool_name], ctx, args)

    return client.portal.call(go)
