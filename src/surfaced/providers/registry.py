"""Provider registry - maps provider_type to implementation class."""

from __future__ import annotations

from surfaced.models.provider import Provider
from surfaced.providers.anthropic_api import AnthropicAPIProvider
from surfaced.providers.base import AIProvider
from surfaced.providers.claude_cli import ClaudeCLIProvider
from surfaced.providers.codex_cli import CodexCLIProvider
from surfaced.providers.gemini_api import GeminiAPIProvider
from surfaced.providers.gemini_cli import GeminiCLIProvider
from surfaced.providers.openai_api import OpenAIAPIProvider

PROVIDER_MAP: dict[str, type[AIProvider]] = {
    "anthropic_api": AnthropicAPIProvider,
    "openai_api": OpenAIAPIProvider,
    "gemini_api": GeminiAPIProvider,
    "claude_cli": ClaudeCLIProvider,
    "codex_cli": CodexCLIProvider,
    "gemini_cli": GeminiCLIProvider,
}


def get_provider(provider: Provider) -> AIProvider:
    """Instantiate an AIProvider from a Provider database record."""
    cls = PROVIDER_MAP.get(provider.provider_type)
    if cls is None:
        raise ValueError(f"Unknown provider type: {provider.provider_type}")
    return cls(model=provider.model)
