"""Google Gemini CLI provider implementation."""

from __future__ import annotations

import json
import subprocess
import time

from surfaced.providers.base import AIProvider, ProviderResponse


class GeminiCLIProvider(AIProvider):
    def __init__(self, model: str | None = None):
        self.model = model

    def execute(self, prompt: str, no_history: bool = False) -> ProviderResponse:
        cmd = ["gemini", "-p", prompt, "-o", "json"]
        if self.model:
            cmd.extend(["-m", self.model])

        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        latency_ms = int((time.time() - start) * 1000)

        if result.returncode != 0:
            raise RuntimeError(f"Gemini CLI error: {result.stderr}")

        # Parse JSON output - extract response text and metadata
        text = ""
        model_name = self.model or "gemini-cli"
        input_tokens = 0
        output_tokens = 0

        try:
            data = json.loads(result.stdout)
            text = data.get("response", "")
            model_name = data.get("model", model_name)
            usage = data.get("usage", {})
            input_tokens = usage.get("inputTokens", usage.get("input_tokens", 0))
            output_tokens = usage.get("outputTokens", usage.get("output_tokens", 0))
        except json.JSONDecodeError:
            # Fall back to raw text output
            text = result.stdout.strip()

        return ProviderResponse(
            text=text,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    def provider_name(self) -> str:
        return "gemini_cli"
