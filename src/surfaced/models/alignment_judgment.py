"""Alignment judgment model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class AlignmentJudgment:
    answer_id: UUID
    run_id: UUID
    prompt_id: UUID
    provider_id: UUID
    brand_id: UUID
    alignment_position_id: UUID
    judge_model: str
    alignment_status: str
    id: UUID = field(default_factory=uuid4)
    rationale: str = ""
    raw_output: str = ""
    error_message: str = ""
    latency_ms: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, d: dict) -> AlignmentJudgment:
        return cls(
            id=UUID(str(d["id"])) if not isinstance(d["id"], UUID) else d["id"],
            answer_id=UUID(str(d["answer_id"])) if not isinstance(d["answer_id"], UUID) else d["answer_id"],
            run_id=UUID(str(d["run_id"])) if not isinstance(d["run_id"], UUID) else d["run_id"],
            prompt_id=UUID(str(d["prompt_id"])) if not isinstance(d["prompt_id"], UUID) else d["prompt_id"],
            provider_id=UUID(str(d["provider_id"])) if not isinstance(d["provider_id"], UUID) else d["provider_id"],
            brand_id=UUID(str(d["brand_id"])) if not isinstance(d["brand_id"], UUID) else d["brand_id"],
            alignment_position_id=UUID(str(d["alignment_position_id"])) if not isinstance(d["alignment_position_id"], UUID) else d["alignment_position_id"],
            judge_model=d["judge_model"],
            alignment_status=d["alignment_status"],
            rationale=d.get("rationale", ""),
            raw_output=d.get("raw_output", ""),
            error_message=d.get("error_message", ""),
            latency_ms=d.get("latency_ms", 0),
            created_at=d["created_at"] if isinstance(d["created_at"], datetime) else datetime.fromisoformat(str(d["created_at"])),
        )
