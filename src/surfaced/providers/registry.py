"""Provider registry - maps (provider, mode) to implementation class."""

from __future__ import annotations

from surfaced.models.provider import Provider
from surfaced.providers.anthropic_api import AnthropicAPIProvider
from surfaced.providers.base import AIProvider
from surfaced.providers.claude_cli import ClaudeCLIProvider
from surfaced.providers.codex_cli import CodexCLIProvider
from surfaced.providers.gemini_api import GeminiAPIProvider
from surfaced.providers.gemini_cli import GeminiCLIProvider
from surfaced.providers.openai_api import OpenAIAPIProvider

PROVIDER_MAP: dict[tuple[str, str], type[AIProvider]] = {
    ("anthropic", "api"): AnthropicAPIProvider,
    ("openai", "api"):    OpenAIAPIProvider,
    ("google", "api"):    GeminiAPIProvider,
    ("anthropic", "cli"): ClaudeCLIProvider,
    ("openai", "cli"):    CodexCLIProvider,
    ("google", "cli"):    GeminiCLIProvider,
}


def get_provider(provider: Provider) -> AIProvider:
    """Instantiate an AIProvider from a Provider database record."""
    key = (provider.provider, provider.execution_mode)
    cls = PROVIDER_MAP.get(key)
    if cls is None:
        raise ValueError(f"Unknown provider: {key}")
    return cls(model=provider.model)
