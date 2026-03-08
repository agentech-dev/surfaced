"""PromptRun model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class PromptRun:
    run_id: UUID
    prompt_id: UUID
    provider_id: UUID
    brand_id: UUID
    prompt_text: str
    prompt_category: str
    response_text: str
    model: str
    provider_name: str
    latency_ms: int
    status: str  # 'success', 'error', 'timeout'
    id: UUID = field(default_factory=uuid4)
    input_tokens: int = 0
    output_tokens: int = 0
    error_message: str = ""
    brand_mentioned: int = 0
    competitors_mentioned: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, d: dict) -> PromptRun:
        return cls(
            id=UUID(str(d["id"])) if not isinstance(d["id"], UUID) else d["id"],
            run_id=UUID(str(d["run_id"])) if not isinstance(d["run_id"], UUID) else d["run_id"],
            prompt_id=UUID(str(d["prompt_id"])) if not isinstance(d["prompt_id"], UUID) else d["prompt_id"],
            provider_id=UUID(str(d["provider_id"])) if not isinstance(d["provider_id"], UUID) else d["provider_id"],
            brand_id=UUID(str(d["brand_id"])) if not isinstance(d["brand_id"], UUID) else d["brand_id"],
            prompt_text=d["prompt_text"],
            prompt_category=d["prompt_category"],
            response_text=d.get("response_text", ""),
            model=d["model"],
            provider_name=d["provider_name"],
            latency_ms=d.get("latency_ms", 0),
            input_tokens=d.get("input_tokens", 0),
            output_tokens=d.get("output_tokens", 0),
            status=d["status"],
            error_message=d.get("error_message", ""),
            brand_mentioned=d.get("brand_mentioned", 0),
            competitors_mentioned=list(d.get("competitors_mentioned", [])),
            created_at=d["created_at"] if isinstance(d["created_at"], datetime) else datetime.fromisoformat(str(d["created_at"])),
        )
