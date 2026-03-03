"""OpenAI API provider implementation."""

from __future__ import annotations

import os
import time

import openai

from surfaced.providers.base import AIProvider, ProviderResponse


class OpenAIAPIProvider(AIProvider):
    def __init__(self, model: str = "gpt-5.2", max_tokens: int = 4096):
        self.model = model
        self.max_tokens = max_tokens
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable is not set. "
                "Export it before running: export OPENAI_API_KEY=sk-..."
            )
        self.client = openai.OpenAI(api_key=api_key)

    def execute(self, prompt: str, no_history: bool = False) -> ProviderResponse:
        start = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            max_completion_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = int((time.time() - start) * 1000)

        choice = response.choices[0]
        text = choice.message.content or ""

        return ProviderResponse(
            text=text,
            model=response.model,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            latency_ms=latency_ms,
        )

    def provider_name(self) -> str:
        return "openai_api"
