"""A scripted provider (``AE3GIS_AGENT_PROVIDER=fake``), like ``engine/fake.py``.

Tests queue replies with ``FakeProvider.script`` (each a ``Turn``, or a callable
of the history returning one). With nothing queued it plays a small demo so the
sidebar can be worked on without a model: it reads the open topology (if the
message names one), then answers with a summary of what it saw.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from collections.abc import Callable
from typing import ClassVar

from services.agent.llm.base import Message, OnEvent, ToolCall, ToolSpec, Turn

Scripted = Turn | Callable[[list[Message]], Turn]


def call(name: str, **args: object) -> ToolCall:
    return ToolCall(id=f"fake_{uuid.uuid4().hex[:12]}", name=name, input=dict(args))


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
        """A few canned flows on the open topology, enough to drive every part of
        the sidebar: "add …" (read, then edit), "deploy", "destroy" (asks for
        approval), anything else (read and summarise)."""
        start = max((i for i, m in enumerate(history) if m.role == "user"), default=0)
        text = str(history[start].content.get("text") or "") if history else ""
        words = text.split("</context>")[-1].lower()
        open_id = re.search(r"open topology: .*?\[([A-Za-z0-9_-]+)\]", text)
        tid = open_id.group(1) if open_id else None
        last = history[-1] if history else None
        # The tools called since the user's last message.
        done = [
            c["name"]
            for m in history[start:]
            if m.role == "assistant"
            for c in m.content.get("tool_calls") or []
        ]

        if last is not None and last.role == "tool":
            result = (last.content.get("results") or [{}])[0]
            if "add" in words and done == ["get_topology"] and not result.get("is_error"):
                subnet = re.search(
                    r"^\s+Subnet .*? \[([A-Za-z0-9_-]+)\]", result.get("text") or "", re.M
                )
                if subnet and "edit_topology" in tools:
                    kind = next(
                        (t for t in ("attacker", "plc", "hmi", "web-server") if t in words),
                        "workstation",
                    )
                    return reply(
                        f"Adding {'an' if kind[0] in 'aeiou' else 'a'} {kind} to that subnet.",
                        call(
                            "edit_topology",
                            topology_id=tid,
                            ops=[{"op": "add_device", "subnet": subnet.group(1), "type": kind}],
                        ),
                    )
            first = (result.get("text") or "").splitlines()[:8]
            verdict = "It failed:" if result.get("is_error") else "Done. Here is what I saw:"
            return reply(f"{verdict}\n\n```\n" + "\n".join(first) + "\n```")
        if tid and "destroy" in words and "destroy" in tools:
            return reply(
                "Destroying the lab (you'll be asked first).", call("destroy", topology_id=tid)
            )
        if tid and "deploy" in words and "deploy" in tools:
            return reply("Deploying it.", call("deploy", topology_id=tid))
        if tid and "get_topology" in tools:
            return reply("Let me look at the open topology.", call("get_topology", topology_id=tid))
        if "list_topologies" in tools:
            return reply("Let me see which topologies you have.", call("list_topologies"))
        return reply("I'm the fake agent: set AE3GIS_AGENT_PROVIDER to talk to a real model.")
