"""Campaign model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Campaign:
    name: str
    id: UUID = field(default_factory=uuid4)
    status: str = "running"
    filters: str = "{}"
    total_prompts: int = 0
    completed_prompts: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, d: dict) -> Campaign:
        finished = d.get("finished_at")
        if finished and isinstance(finished, str):
            finished = datetime.fromisoformat(finished)
        return cls(
            id=UUID(str(d["id"])) if not isinstance(d["id"], UUID) else d["id"],
            name=d["name"],
            status=d["status"],
            filters=d.get("filters", "{}"),
            total_prompts=d.get("total_prompts", 0),
            completed_prompts=d.get("completed_prompts", 0),
            started_at=d["started_at"] if isinstance(d["started_at"], datetime) else datetime.fromisoformat(str(d["started_at"])),
            finished_at=finished,
            created_at=d["created_at"] if isinstance(d["created_at"], datetime) else datetime.fromisoformat(str(d["created_at"])),
            updated_at=d["updated_at"] if isinstance(d["updated_at"], datetime) else datetime.fromisoformat(str(d["updated_at"])),
        )
