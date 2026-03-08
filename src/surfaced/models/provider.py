"""Provider model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Provider:
    name: str
    provider: str
    execution_mode: str  # 'api' or 'cli'
    model: str
    id: UUID = field(default_factory=uuid4)
    config: str = "{}"
    rate_limit_rpm: int = 60
    is_active: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, d: dict) -> Provider:
        return cls(
            id=UUID(str(d["id"])) if not isinstance(d["id"], UUID) else d["id"],
            name=d["name"],
            provider=d["provider"],
            execution_mode=d["execution_mode"],
            model=d["model"],
            config=d.get("config", "{}"),
            rate_limit_rpm=d.get("rate_limit_rpm", 60),
            is_active=d.get("is_active", 1),
            created_at=d["created_at"] if isinstance(d["created_at"], datetime) else datetime.fromisoformat(str(d["created_at"])),
            updated_at=d["updated_at"] if isinstance(d["updated_at"], datetime) else datetime.fromisoformat(str(d["updated_at"])),
        )
