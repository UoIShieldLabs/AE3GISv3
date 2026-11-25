"""A scripted provider (``AE3GIS_AGENT_PROVIDER=fake``), like ``engine/fake.py``.

Tests queue replies with ``FakeProvider.script`` (each a ``Turn``, or a callable
of the history returning one). With nothing queued it plays a small demo so the
sidebar can be worked on without a model: it reads the open topology (if the
message names one), then answers with a summary of what it saw.
"""

from __future__ import annotations

import asyncio
import itertools
import re
from collections.abc import Callable
from typing import ClassVar

from services.agent.llm.base import Message, OnEvent, ToolCall, ToolSpec, Turn

Scripted = Turn | Callable[[list[Message]], Turn]

_ids = itertools.count(1)


def call(name: str, **args: object) -> ToolCall:
    return ToolCall(id=f"fake_{next(_ids)}", name=name, input=dict(args))


def reply(text: str = "", *calls: ToolCall) -> Turn:
    return Turn(text=text, tool_calls=list(calls), stop_reason="tool_use" if calls else "end_turn")


class FakeProvider:
    name = "fake"
    # Replies queued by tests, served in order (shared: one per process).
    script: ClassVar[list[Scripted]] = []
    # What each call saw (system prompt, history, tool names), for assertions.
    calls: ClassVar[list[dict]] = []
    # Seconds each reply takes to "generate" (tests of stop / steering).
    delay: ClassVar[float] = 0.0

    def __init__(self, model: str = "fake-model") -> None:
        self.model = model or "fake-model"

    @classmethod
    def reset(cls) -> None:
        cls.script.clear()
        cls.calls.clear()
        cls.delay = 0.0

    async def complete(
        self, *, system: str, history: list[Message], tools: list[ToolSpec], on_event: OnEvent
    ) -> Turn:
        FakeProvider.calls.append(
            {"system": system, "history": list(history), "tools": [t.name for t in tools]}
        )
        if FakeProvider.delay:
            await asyncio.sleep(FakeProvider.delay)
        if FakeProvider.script:
            item = FakeProvider.script.pop(0)
            turn = item(history) if callable(item) else item
        else:
            turn = self._demo(history, {t.name for t in tools})
        for word in re.findall(r"\S+\s*", turn.text):
            on_event("text", word)
        for c in turn.tool_calls:
            on_event("tool", c.name)
        turn.model = self.model
        return turn

    def _demo(self, history: list[Message], tools: set[str]) -> Turn:
        last = history[-1] if history else None
        if last is not None and last.role == "tool":
            result = (last.content.get("results") or [{}])[0]
            first = (result.get("text") or "").splitlines()[:6]
            return reply("Here is what I found (fake agent):\n\n```\n" + "\n".join(first) + "\n```")
        text = str(last.content.get("text") or "") if last is not None else ""
        found = re.search(r"topology_id=([A-Za-z0-9_-]+)", text)
        if found and "get_topology" in tools:
            return reply(
                "Let me look at that topology.", call("get_topology", topology_id=found.group(1))
            )
        if "list_topologies" in tools:
            return reply("Let me see which topologies you have.", call("list_topologies"))
        return reply("I'm the fake agent: set AE3GIS_AGENT_PROVIDER to talk to a real model.")
