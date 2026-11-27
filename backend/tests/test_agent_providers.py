"""How each provider shapes its requests and reads its replies (no network)."""

from __future__ import annotations

import json

import httpx2

from services.agent.llm.anthropic import AnthropicProvider, to_anthropic
from services.agent.llm.base import Message, ToolSpec
from services.agent.llm.openai_compat import TRIMMED, fit, to_openai

TOOLS = [ToolSpec("get_topology", "Read a topology", {"type": "object", "properties": {}})]

HISTORY = [
    Message("user", {"text": "hi"}),
    Message(
        "assistant",
        {"text": "", "tool_calls": [{"id": "t1", "name": "get_topology", "input": {}}]},
        raw={
            "provider": "anthropic",
            "content": [
                {"type": "thinking", "thinking": "", "signature": "sig"},
                {"type": "tool_use", "id": "t1", "name": "get_topology", "input": {}},
            ],
        },
    ),
    Message("tool", {"results": [{"tool_call_id": "t1", "name": "get_topology", "text": "ok"}]}),
    Message("note", {"kind": "stopped", "text": "Stopped."}),
]


def test_claude_requests_cache_stream_tools_and_fall_back():
    p = AnthropicProvider(model="claude-opus-5-5", api_key="x")
    params = p.params("system prompt", HISTORY, TOOLS)
    assert params["model"] == "claude-opus-5-5"
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert params["cache_control"] == {"type": "ephemeral"}
    assert params["tools"][0]["eager_input_streaming"] is True
    assert params["thinking"]["type"] == "adaptive"
    assert params["output_config"] == {"effort": "high"}
    assert params["fallbacks"] == "default"
    assert params["betas"] == ["server-side-fallback-2026-07-01"]
    no_fallback = AnthropicProvider(api_key="x", fallbacks=False).params("s", HISTORY, TOOLS)
    assert "fallbacks" not in no_fallback and "betas" not in no_fallback


def test_claude_replays_its_own_turns_unchanged_and_drops_notes():
    msgs = to_anthropic(HISTORY)
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    assert msgs[1]["content"][0] == {"type": "thinking", "thinking": "", "signature": "sig"}
    assert msgs[2]["content"][0]["type"] == "tool_result"
    # A turn from another provider is rebuilt from the neutral record.
    other = [HISTORY[0], Message("assistant", HISTORY[1].content), HISTORY[2]]
    rebuilt = to_anthropic(other)
    assert rebuilt[1]["content"] == [
        {"type": "tool_use", "id": "t1", "name": "get_topology", "input": {}}
    ]


def _sse(events: list[dict]) -> bytes:
    return b"".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n".encode() for e in events)


def test_claude_streams_a_tool_call_into_a_turn():
    events = [
        {
            "type": "message_start",
            "message": {
                "id": "m1",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5-5",
                "content": [],
                "stop_reason": None,
                "usage": {"input_tokens": 10, "output_tokens": 0},
            },
        },
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "Looking."},
        },
        {"type": "content_block_stop", "index": 0},
        {
            "type": "content_block_start",
            "index": 1,
            "content_block": {
                "type": "tool_use",
                "id": "toolu_1",
                "name": "get_topology",
                "input": {},
            },
        },
        {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": '{"topology_id": "t"}'},
        },
        {"type": "content_block_stop", "index": 1},
        {
            "type": "message_delta",
            "delta": {"stop_reason": "tool_use"},
            "usage": {"output_tokens": 7},
        },
        {"type": "message_stop"},
    ]
    seen: list[dict] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(json.loads(request.content))
        return httpx2.Response(
            200, content=_sse(events), headers={"content-type": "text/event-stream"}
        )

    import anthropic

    client = anthropic.AsyncAnthropic(
        api_key="x",
        http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler)),
    )
    p = AnthropicProvider(api_key="x", client=client)
    deltas: list[tuple[str, str]] = []
    import asyncio

    turn = asyncio.run(
        p.complete(
            system="s",
            history=[HISTORY[0]],
            tools=TOOLS,
            on_event=lambda k, t: deltas.append((k, t)),
        )
    )
    assert turn.text == "Looking." and turn.stop_reason == "tool_use"
    assert turn.tool_calls[0].name == "get_topology" and turn.tool_calls[0].input == {
        "topology_id": "t"
    }
    assert ("text", "Looking.") in deltas and ("tool", "get_topology") in deltas
    assert turn.raw["provider"] == "anthropic" and turn.raw["content"][1]["type"] == "tool_use"
    assert turn.usage["input_tokens"] == 10 and turn.usage["output_tokens"] == 7
    assert seen[0]["fallbacks"] == "default"


def test_openai_messages_carry_tool_calls_and_results():
    msgs = to_openai("sys", HISTORY)
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "tool"]
    assert msgs[2]["tool_calls"][0]["function"] == {"name": "get_topology", "arguments": "{}"}
    assert msgs[3] == {"role": "tool", "tool_call_id": "t1", "content": "ok"}


def test_openai_context_is_trimmed_oldest_tool_output_first():
    big = "x" * 4000
    msgs = [{"role": "system", "content": "sys"}]
    for i in range(6):
        msgs += [
            {"role": "user", "content": f"q{i}"},
            {"role": "assistant", "content": None, "tool_calls": [{"id": f"c{i}"}]},
            {"role": "tool", "tool_call_id": f"c{i}", "content": big},
        ]
    fitted = fit(msgs, 3000)
    assert fitted[0]["content"] == "sys"
    assert fitted[3]["content"] == TRIMMED  # the first tool output went first
    assert fitted[-1]["content"] == big  # the latest stays
    tiny = fit(msgs, 1000)
    assert sum(1 for m in tiny if m["role"] == "user") < 6
    assert tiny[0]["role"] == "system"
