"""Claude Code CLI provider implementation."""

from __future__ import annotations

import json
import subprocess
import time

from surfaced.providers.base import AIProvider, ProviderResponse


class ClaudeCLIProvider(AIProvider):
    def __init__(self, model: str | None = None):
        self.model = model

    def execute(self, prompt: str) -> ProviderResponse:
        cmd = ["claude", "-p", prompt, "--output-format", "json"]
        if self.model:
            cmd.extend(["--model", self.model])

        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        latency_ms = int((time.time() - start) * 1000)

        if result.returncode != 0:
            raise RuntimeError(f"Claude CLI error: {result.stderr}")

        data = json.loads(result.stdout)
        text = data.get("result", "")
        model_name = data.get("model", self.model or "claude-cli")
        input_tokens = data.get("input_tokens", 0)
        output_tokens = data.get("output_tokens", 0)

        return ProviderResponse(
            text=text,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    def provider_name(self) -> str:
        return "claude_cli"
