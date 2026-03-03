"""Google Gemini API provider implementation."""

from __future__ import annotations

import os
import time

from google import genai

from surfaced.providers.base import AIProvider, ProviderResponse


class GeminiAPIProvider(AIProvider):
    def __init__(self, model: str = "gemini-3.1-pro-preview", max_tokens: int = 4096):
        self.model = model
        self.max_tokens = max_tokens
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not set. "
                "Export it before running: export GEMINI_API_KEY=..."
            )
        self.client = genai.Client(api_key=api_key)

    def execute(self, prompt: str, no_history: bool = False) -> ProviderResponse:
        start = time.time()
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                max_output_tokens=self.max_tokens,
            ),
        )
        latency_ms = int((time.time() - start) * 1000)

        text = response.text or ""
        input_tokens = 0
        output_tokens = 0
        if response.usage_metadata:
            input_tokens = response.usage_metadata.prompt_token_count or 0
            output_tokens = response.usage_metadata.candidates_token_count or 0

        return ProviderResponse(
            text=text,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    def provider_name(self) -> str:
        return "gemini_api"
