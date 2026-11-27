"""Model providers for the agent, behind one neutral interface (``base``)."""

from __future__ import annotations

import os

from config import Settings
from services.agent.llm.base import Message, Provider, ProviderError, ToolCall, ToolSpec, Turn


def make_provider(settings: Settings, *, tutor: bool = False) -> Provider:
    """The provider the settings name, for a staff run or the student tutor."""
    kind = settings.agent_provider.strip().lower()
    model = (settings.agent_tutor_model if tutor else "") or settings.agent_model
    if kind == "anthropic":
        from services.agent.llm.anthropic import AnthropicProvider

        return AnthropicProvider(
            model=model,
            api_key=settings.agent_api_key or os.environ.get("ANTHROPIC_API_KEY", ""),
            base_url=settings.agent_base_url,
            effort=settings.agent_tutor_effort if tutor else settings.agent_effort,
            fallbacks=settings.agent_refusal_fallbacks,
        )
    if kind == "openai":
        from services.agent.llm.openai_compat import OpenAICompatProvider

        return OpenAICompatProvider(
            model=model,
            base_url=settings.agent_base_url,
            api_key=settings.agent_api_key or os.environ.get("OPENAI_API_KEY", ""),
            context_tokens=settings.agent_context_tokens,
        )
    if kind == "fake":
        from services.agent.llm.fake import FakeProvider

        return FakeProvider(model)
    raise ProviderError(f"The agent is not configured (AE3GIS_AGENT_PROVIDER={kind or 'off'})")


def describe(settings: Settings) -> dict[str, str | None]:
    """Provider and model for the status endpoint (never the key)."""
    kind = settings.agent_provider.strip().lower()
    model = settings.agent_model or ("claude-opus-5-5" if kind == "anthropic" else None)
    return {"provider": kind if settings.agent_enabled else None, "model": model}


__all__ = [
    "Message",
    "Provider",
    "ProviderError",
    "ToolCall",
    "ToolSpec",
    "Turn",
    "describe",
    "make_provider",
]
