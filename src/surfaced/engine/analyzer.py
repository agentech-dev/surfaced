"""Post-response analysis for brand mentions."""

from __future__ import annotations

from surfaced.models.brand import Brand


def check_brand_mentioned(response_text: str, brand: Brand) -> bool:
    """Check if the brand name or any alias appears in the response."""
    text_lower = response_text.lower()
    names_to_check = [brand.name] + brand.aliases
    return any(name.lower() in text_lower for name in names_to_check)


def find_competitors_mentioned(response_text: str, brand: Brand) -> list[str]:
    """Return list of competitor names that appear in the response."""
    text_lower = response_text.lower()
    return [c for c in brand.competitors if c.lower() in text_lower]
