"""Anthropic API provider implementation."""

from __future__ import annotations

import os
import time

import anthropic

from surfaced.providers.base import AIProvider, ProviderResponse


class AnthropicAPIProvider(AIProvider):
    def __init__(self, model: str = "claude-sonnet-4-20250514", max_tokens: int = 4096):
        self.model = model
        self.max_tokens = max_tokens
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Export it before running: export ANTHROPIC_API_KEY=sk-..."
            )
        self.client = anthropic.Anthropic(api_key=api_key)

    def execute(self, prompt: str, no_history: bool = False) -> ProviderResponse:
        start = time.time()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = int((time.time() - start) * 1000)

        text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text

        return ProviderResponse(
            text=text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms,
        )

    def provider_name(self) -> str:
        return "anthropic_api"
