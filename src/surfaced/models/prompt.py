"""Prompt model."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Prompt:
    text: str
    category: str
    brand_id: UUID
    id: UUID = field(default_factory=uuid4)
    branded: bool = False
    recommendation_enabled: bool = True
    tags: list[str] = field(default_factory=list)
    is_template: int = 0
    variables: list[str] = field(default_factory=list)
    is_active: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def render(self, variables: dict[str, str] | None = None) -> str:
        """Render template by substituting {{variable}} placeholders."""
        if not self.is_template or not variables:
            return self.text
        result = self.text
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", value)
        return result

    @classmethod
    def extract_variables(cls, text: str) -> list[str]:
        """Extract {{variable}} names from template text."""
        return re.findall(r"\{\{(\w+)\}\}", text)

    @classmethod
    def from_dict(cls, d: dict) -> Prompt:
        return cls(
            id=UUID(str(d["id"])) if not isinstance(d["id"], UUID) else d["id"],
            text=d["text"],
            category=d["category"],
            brand_id=UUID(str(d["brand_id"])) if not isinstance(d["brand_id"], UUID) else d["brand_id"],
            branded=bool(d.get("branded", False)),
            recommendation_enabled=bool(d.get("recommendation_enabled", True)),
            tags=list(d.get("tags", [])),
            is_template=d.get("is_template", 0),
            variables=list(d.get("variables", [])),
            is_active=d.get("is_active", 1),
            created_at=d["created_at"] if isinstance(d["created_at"], datetime) else datetime.fromisoformat(str(d["created_at"])),
            updated_at=d["updated_at"] if isinstance(d["updated_at"], datetime) else datetime.fromisoformat(str(d["updated_at"])),
        )
