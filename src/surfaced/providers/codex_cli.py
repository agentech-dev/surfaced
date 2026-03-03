"""OpenAI Codex CLI provider implementation."""

from __future__ import annotations

import json
import subprocess
import time

from surfaced.providers.base import AIProvider, ProviderResponse


class CodexCLIProvider(AIProvider):
    def __init__(self, model: str | None = None):
        self.model = model

    def execute(self, prompt: str, no_history: bool = False) -> ProviderResponse:
        cmd = ["codex", "exec", prompt, "--json"]
        if self.model:
            cmd.extend(["-m", self.model])
        if no_history:
            cmd.append("--ephemeral")

        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        latency_ms = int((time.time() - start) * 1000)

        if result.returncode != 0:
            raise RuntimeError(f"Codex CLI error: {result.stderr}")

        # Parse JSONL events - collect assistant message content
        text_parts = []
        model_name = self.model or "codex-cli"
        input_tokens = 0
        output_tokens = 0

        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type", "")

            if event_type == "message" and event.get("role") == "assistant":
                for block in event.get("content", []):
                    if block.get("type") == "output_text":
                        text_parts.append(block.get("text", ""))
                model_name = event.get("model", model_name)
                usage = event.get("usage", {})
                input_tokens += usage.get("input_tokens", 0)
                output_tokens += usage.get("output_tokens", 0)

        return ProviderResponse(
            text="".join(text_parts),
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    def provider_name(self) -> str:
        return "codex_cli"
