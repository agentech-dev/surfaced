"""Canonical position model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class CanonicalPosition:
    brand_id: UUID
    topic: str
    statement: str
    id: UUID = field(default_factory=uuid4)
    is_active: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, d: dict) -> CanonicalPosition:
        return cls(
            id=UUID(str(d["id"])) if not isinstance(d["id"], UUID) else d["id"],
            brand_id=UUID(str(d["brand_id"])) if not isinstance(d["brand_id"], UUID) else d["brand_id"],
            topic=d["topic"],
            statement=d["statement"],
            is_active=d.get("is_active", 1),
            created_at=d["created_at"] if isinstance(d["created_at"], datetime) else datetime.fromisoformat(str(d["created_at"])),
            updated_at=d["updated_at"] if isinstance(d["updated_at"], datetime) else datetime.fromisoformat(str(d["updated_at"])),
        )
