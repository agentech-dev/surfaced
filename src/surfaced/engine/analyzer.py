"""Post-response analysis for brand mentions."""

from __future__ import annotations

from surfaced.models.brand import Brand


def check_brand_mentioned(response_text: str, brand: Brand) -> bool:
    """Check if the brand name or any alias appears in the response."""
    return _contains_brand_name(response_text, brand)


def is_prompt_branded(prompt_text: str, brand: Brand) -> bool:
    """Check if the prompt itself contains the brand name or any alias."""
    return _contains_brand_name(prompt_text, brand)


def _contains_brand_name(text: str, brand: Brand) -> bool:
    """Case-insensitive literal match for a brand name or alias."""
    text_lower = text.lower()
    names_to_check = [brand.name] + brand.aliases
    return any(name.lower() in text_lower for name in names_to_check)


def find_competitors_mentioned(response_text: str, brand: Brand) -> list[str]:
    """Return list of competitor names that appear in the response."""
    text_lower = response_text.lower()
    return [c for c in brand.competitors if c.lower() in text_lower]
