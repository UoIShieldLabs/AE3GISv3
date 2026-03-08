"""Provider-agnostic LLM client using OpenAI-compatible chat completions API.

Works with Ollama, llama.cpp, vLLM, Gemini (via compatibility layer), and OpenAI.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

log = logging.getLogger(__name__)

# Reusable async client
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=300.0)
    return _client


async def chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None,
    temperature: float = 0.3,
) -> dict[str, Any]:
    """Send a chat completion request and return the full response JSON."""
    client = _get_client()
    url = f"{LLM_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
    }

    body: dict[str, Any] = {
        "model": model or LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    log.debug("LLM request: model=%s, messages=%d, tools=%d",
              body["model"], len(messages), len(tools or []))

    resp = await client.post(url, headers=headers, json=body)
    resp.raise_for_status()
    data = resp.json()

    log.debug("LLM response: finish_reason=%s",
              data.get("choices", [{}])[0].get("finish_reason"))
    return data


def extract_reply(response: dict[str, Any]) -> dict[str, Any]:
    """Extract the assistant message from a completion response."""
    return response["choices"][0]["message"]


def has_tool_calls(message: dict[str, Any]) -> bool:
    return bool(message.get("tool_calls"))


def get_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    return message.get("tool_calls", [])


def parse_tool_args(tool_call: dict[str, Any]) -> dict[str, Any]:
    args = tool_call["function"]["arguments"]
    if isinstance(args, str):
        return json.loads(args)
    return args
