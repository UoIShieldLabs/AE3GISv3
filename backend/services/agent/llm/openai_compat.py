"""Any OpenAI-compatible chat-completions endpoint: Ollama, vLLM, LM Studio,
llama.cpp's server, OpenAI itself. Tool calls stream as deltas and are assembled
here. Local models have small context windows, so the oldest tool output is
trimmed to fit ``context_tokens`` (estimated at ~4 characters a token)."""

from __future__ import annotations

import json
import logging
from typing import Any

import openai

from services.agent.llm.base import (
    Message,
    OnEvent,
    ProviderError,
    ToolCall,
    ToolSpec,
    Turn,
    model_messages,
)

log = logging.getLogger(__name__)

TRIMMED = "[earlier output trimmed to fit the model's context]"


def _tokens(messages: list[dict[str, Any]]) -> int:
    return sum(len(json.dumps(m, default=str)) for m in messages) // 4


def to_openai(system: str, history: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in model_messages(history):
        if m.role == "user":
            text = str(m.content.get("text") or "").strip()
            if text:
                out.append({"role": "user", "content": text})
        elif m.role == "assistant":
            calls = m.content.get("tool_calls") or []
            if not m.content.get("text") and not calls:
                continue
            msg: dict[str, Any] = {"role": "assistant", "content": m.content.get("text") or None}
            if calls:
                msg["tool_calls"] = [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {
                            "name": c["name"],
                            "arguments": json.dumps(c.get("input") or {}),
                        },
                    }
                    for c in calls
                ]
            out.append(msg)
        elif m.role == "tool":
            for r in m.content.get("results") or []:
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": r["tool_call_id"],
                        "content": ("Error: " if r.get("is_error") else "") + (r.get("text") or ""),
                    }
                )
    return out


def fit(messages: list[dict[str, Any]], budget: int) -> list[dict[str, Any]]:
    """Trim the oldest tool output, then drop the oldest turns, to fit ``budget``.
    The system prompt and the latest user message always stay."""
    msgs = [dict(m) for m in messages]
    if _tokens(msgs) <= budget:
        return msgs
    for m in msgs[1:-4]:
        if m["role"] == "tool" and m.get("content") != TRIMMED:
            m["content"] = TRIMMED
            if _tokens(msgs) <= budget:
                return msgs
    # Still too long: drop whole turns from the start (a user message and all
    # that followed it), never splitting a tool call from its results.
    while _tokens(msgs) > budget:
        starts = [i for i, m in enumerate(msgs) if m["role"] == "user"]
        if len(starts) < 2:
            break
        del msgs[starts[0] : starts[1]]
    return msgs


class OpenAICompatProvider:
    name = "openai"

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "",
        api_key: str = "",
        context_tokens: int = 32000,
        client: openai.AsyncOpenAI | None = None,
    ) -> None:
        if not model:
            raise ProviderError("Set AE3GIS_AGENT_MODEL to the model your endpoint serves")
        self.model = model
        self.context_tokens = context_tokens
        self.client = client or openai.AsyncOpenAI(
            api_key=api_key or "not-needed", base_url=base_url or None
        )

    async def complete(
        self, *, system: str, history: list[Message], tools: list[ToolSpec], on_event: OnEvent
    ) -> Turn:
        tool_defs = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools
        ]
        tool_chars = len(json.dumps(tool_defs)) // 4
        messages = fit(to_openai(system, history), max(2000, self.context_tokens - tool_chars))
        text_parts: list[str] = []
        calls: dict[int, dict[str, str]] = {}
        finish = "stop"
        usage: dict[str, int] = {}
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tool_defs or openai.NOT_GIVEN,
                stream=True,
            )
            async for chunk in stream:
                if getattr(chunk, "usage", None):
                    usage = {
                        "input_tokens": chunk.usage.prompt_tokens or 0,
                        "output_tokens": chunk.usage.completion_tokens or 0,
                    }
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta
                if delta.content:
                    text_parts.append(delta.content)
                    on_event("text", delta.content)
                for tc in delta.tool_calls or []:
                    slot = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function and tc.function.name:
                        if not slot["name"]:
                            on_event("tool", tc.function.name)
                        slot["name"] += tc.function.name
                    if tc.function and tc.function.arguments:
                        slot["arguments"] += tc.function.arguments
                if choice.finish_reason:
                    finish = choice.finish_reason
        except openai.AuthenticationError as exc:
            raise ProviderError("The model endpoint rejected the API key") from exc
        except openai.APIStatusError as exc:
            raise ProviderError(
                f"The model endpoint answered {exc.status_code}: {exc.message}"
            ) from exc
        except openai.APIConnectionError as exc:
            raise ProviderError(
                f"Could not reach the model endpoint ({self.client.base_url})"
            ) from exc
        tool_calls = []
        for i, slot in sorted(calls.items()):
            try:
                args: Any = json.loads(slot["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {"INVALID_JSON": slot["arguments"]}
            tool_calls.append(ToolCall(id=slot["id"] or f"call_{i}", name=slot["name"], input=args))
        stop = {"length": "max_tokens", "content_filter": "refusal"}.get(
            finish, "tool_use" if tool_calls else "end_turn"
        )
        text = "".join(text_parts)
        return Turn(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop,  # type: ignore[arg-type]
            refusal="The model's content filter stopped this reply." if stop == "refusal" else None,
            model=self.model,
            usage=usage,
            raw=None,
        )
