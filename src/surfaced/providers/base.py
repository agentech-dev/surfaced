"""Base provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class AIProvider(ABC):
    @abstractmethod
    def execute(self, prompt: str, no_history: bool = False) -> ProviderResponse:
        """Execute a prompt and return the response.

        Args:
            prompt: The prompt text to send.
            no_history: If True, best-effort attempt to not load any local
                history or memory. Does not delete anything.
        """
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name for logging."""
        ...
