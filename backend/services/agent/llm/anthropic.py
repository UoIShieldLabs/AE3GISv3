"""Claude through the official Anthropic SDK (streaming, adaptive thinking).

- The tool list and system prompt are stable for a chat (tools sorted), with an
  explicit cache breakpoint on the system block and top-level automatic caching
  for the conversation tail.
- Tools stream their input as it is generated (``eager_input_streaming``); the
  input is validated against the tool's schema before anything runs
  (``tools.run_tool``), and a turn cut off at ``max_tokens`` or declined
  (``refusal``) runs no tools.
- Assistant turns are stored and replayed exactly as returned (thinking blocks
  must come back unchanged; the history is append-only).
- Server-side refusal fallbacks (``fallbacks: "default"``) are on unless the
  admin turns them off: a declined request is retried on a fallback model in the
  same call (security-lab work can trip the cyber classifier).
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

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

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_TOKENS = 64_000
JSON_RETRIES = 2


def _dump(block: Any) -> dict[str, Any]:
    return block.model_dump(mode="json", exclude_none=True)


def to_anthropic(history: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in model_messages(history):
        if m.role == "user":
            text = str(m.content.get("text") or "").strip()
            if text:
                out.append({"role": "user", "content": [{"type": "text", "text": text}]})
        elif m.role == "assistant":
            if m.raw and m.raw.get("provider") == "anthropic" and m.raw.get("content"):
                out.append({"role": "assistant", "content": m.raw["content"]})
                continue
            blocks: list[dict[str, Any]] = []
            if m.content.get("text"):
                blocks.append({"type": "text", "text": m.content["text"]})
            for call in m.content.get("tool_calls") or []:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call.get("input") or {},
                    }
                )
            if blocks:
                out.append({"role": "assistant", "content": blocks})
        elif m.role == "tool":
            results = [
                {
                    "type": "tool_result",
                    "tool_use_id": r["tool_call_id"],
                    "content": r.get("text") or "(no output)",
                    **({"is_error": True} if r.get("is_error") else {}),
                }
                for r in m.content.get("results") or []
            ]
            if results:
                out.append({"role": "user", "content": results})
    return out


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        model: str = "",
        api_key: str = "",
        base_url: str = "",
        effort: str = "high",
        fallbacks: bool = True,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        self.model = model or DEFAULT_MODEL
        self.effort = effort
        self.fallbacks = fallbacks
        kwargs: dict[str, Any] = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self.client = client or anthropic.AsyncAnthropic(**kwargs)

    def params(self, system: str, history: list[Message], tools: list[ToolSpec]) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": to_anthropic(history),
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                    "eager_input_streaming": True,
                }
                for t in tools
            ],
            "thinking": {"type": "adaptive", "display": "summarized"},
            "output_config": {"effort": self.effort},
            "cache_control": {"type": "ephemeral"},
        }
        if self.fallbacks:
            params["betas"] = [FALLBACK_BETA]
            params["fallbacks"] = "default"
        return params

    async def complete(
        self, *, system: str, history: list[Message], tools: list[ToolSpec], on_event: OnEvent
    ) -> Turn:
        params = self.params(system, history, tools)
        attempt = 0
        while True:
            try:
                async with self.client.beta.messages.stream(**params) as stream:
                    async for event in stream:
                        if event.type == "text":
                            on_event("text", event.text)
                        elif event.type == "thinking":
                            on_event("thinking", event.thinking)
                        elif (
                            event.type == "content_block_start"
                            and getattr(event.content_block, "type", "") == "tool_use"
                        ):
                            on_event("tool", event.content_block.name)
                    message = await stream.get_final_message()
                break
            except ValueError:
                # Tool input JSON the SDK could not parse at all: re-issue the turn.
                attempt += 1
                if attempt > JSON_RETRIES:
                    raise ProviderError("The model kept sending malformed tool input") from None
                log.warning("agent: unparseable tool input, retrying the turn")
            except anthropic.AuthenticationError as exc:
                raise ProviderError(
                    "The Anthropic API key was rejected (AE3GIS_AGENT_API_KEY)"
                ) from exc
            except anthropic.RateLimitError as exc:
                raise ProviderError(
                    "The model is rate-limited right now; try again shortly"
                ) from exc
            except anthropic.APIStatusError as exc:
                raise ProviderError(
                    f"The model service answered {exc.status_code}: {exc.message}"
                ) from exc
            except anthropic.APIConnectionError as exc:
                raise ProviderError("Could not reach the Anthropic API") from exc
        return self._turn(message)

    def _turn(self, message: Any) -> Turn:
        text = "".join(b.text for b in message.content if getattr(b, "type", "") == "text")
        calls = [
            ToolCall(id=b.id, name=b.name, input=b.input)
            for b in message.content
            if getattr(b, "type", "") == "tool_use"
        ]
        stop = message.stop_reason
        refusal = None
        if stop == "refusal":
            details = getattr(message, "stop_details", None)
            refusal = getattr(details, "explanation", None) or "The model declined this request."
        elif stop not in ("end_turn", "tool_use", "max_tokens"):
            stop = "tool_use" if calls else "end_turn"
        usage = message.usage
        return Turn(
            text=text,
            tool_calls=calls,
            stop_reason=stop,
            refusal=refusal,
            model=getattr(message, "model", self.model),
            raw={
                "provider": "anthropic",
                "model": message.model,
                "content": [_dump(b) for b in message.content],
            },
            usage={
                "input_tokens": usage.input_tokens or 0,
                "output_tokens": usage.output_tokens or 0,
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
                "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0)
                or 0,
            },
        )
