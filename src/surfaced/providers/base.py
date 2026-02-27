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
    def execute(self, prompt: str) -> ProviderResponse:
        """Execute a prompt and return the response."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name for logging."""
        ...
