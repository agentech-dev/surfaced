"""Brand model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Brand:
    name: str
    id: UUID = field(default_factory=uuid4)
    domain: str = ""
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    is_active: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, d: dict) -> Brand:
        return cls(
            id=UUID(str(d["id"])) if not isinstance(d["id"], UUID) else d["id"],
            name=d["name"],
            domain=d.get("domain", ""),
            description=d.get("description", ""),
            aliases=list(d.get("aliases", [])),
            competitors=list(d.get("competitors", [])),
            is_active=d.get("is_active", 1),
            created_at=d["created_at"] if isinstance(d["created_at"], datetime) else datetime.fromisoformat(str(d["created_at"])),
            updated_at=d["updated_at"] if isinstance(d["updated_at"], datetime) else datetime.fromisoformat(str(d["updated_at"])),
        )
