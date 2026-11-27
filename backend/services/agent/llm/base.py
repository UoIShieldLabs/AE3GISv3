"""The provider-neutral shape of a conversation, and what a provider does with it.

A chat is stored as neutral messages (``agent_messages.content``) so any provider
can replay it; each provider also keeps its own record of an assistant turn
(``provider_raw``), replayed unchanged when the same provider continues the chat
(Claude's thinking blocks must come back exactly as they were sent).

- ``user``: ``{"text": str}``
- ``assistant``: ``{"text": str, "tool_calls": [{"id", "name", "input"}]}``
- ``tool``: ``{"results": [{"tool_call_id", "name", "text", "is_error"}]}``
- ``note``: UI only (stopped, limits, errors); never sent to a model.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Role = Literal["user", "assistant", "tool", "note"]
StopReason = Literal["end_turn", "tool_use", "max_tokens", "refusal"]


@dataclass
class Message:
    role: Role
    content: dict[str, Any]
    raw: dict[str, Any] | None = None


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolCall:
    id: str
    name: str
    input: Any


@dataclass
class Turn:
    """One model reply."""

    text: str
    tool_calls: list[ToolCall]
    stop_reason: StopReason
    raw: dict[str, Any] | None = None
    usage: dict[str, int] = field(default_factory=dict)
    # Why it declined (a refusal), when the provider says.
    refusal: str | None = None
    model: str = ""

    def content(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "tool_calls": [{"id": c.id, "name": c.name, "input": c.input} for c in self.tool_calls],
        }


# Streaming callbacks: ("text", delta) / ("thinking", delta) / ("tool", name).
OnEvent = Callable[[str, str], None]


class ProviderError(Exception):
    """The model service failed (auth, rate limit, unreachable): shown to the user."""


class Provider(Protocol):
    name: str
    model: str

    async def complete(
        self,
        *,
        system: str,
        history: list[Message],
        tools: list[ToolSpec],
        on_event: OnEvent,
    ) -> Turn: ...


def model_messages(history: list[Message]) -> list[Message]:
    """The history a model sees: notes dropped."""
    return [m for m in history if m.role != "note"]
