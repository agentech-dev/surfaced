"""Post-response analysis for brand mentions and recommendation status."""

from __future__ import annotations

import os
from collections.abc import Callable

import anthropic

from surfaced.models.brand import Brand


DEFAULT_RECOMMENDATION_JUDGE_MODEL = "claude-haiku-4-5"
RECOMMENDATION_STATUS_NOT_MENTIONED = "not_mentioned"
RECOMMENDATION_STATUS_NOT_JUDGED = "not_judged"
RECOMMENDATION_STATUS_JUDGE_FAILED = "judge_failed"
JUDGED_RECOMMENDATION_STATUSES = {"recommended", "neutral", "negative"}
RECOMMENDATION_STATUSES = {
    RECOMMENDATION_STATUS_NOT_MENTIONED,
    RECOMMENDATION_STATUS_NOT_JUDGED,
    RECOMMENDATION_STATUS_JUDGE_FAILED,
    *JUDGED_RECOMMENDATION_STATUSES,
}
RecommendationJudge = Callable[[str, Brand], str]


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


def is_recommendation_judge_enabled() -> bool:
    """Return global recommendation-judge config, defaulting to enabled."""
    value = os.environ.get("SURFACED_RECOMMENDATION_JUDGE_ENABLED", "true")
    return value.strip().casefold() not in {"0", "false", "no", "off"}


def classify_recommendation(
    response_text: str,
    brand: Brand,
    *,
    brand_mentioned: bool | None = None,
    enabled: bool = True,
    judge: RecommendationJudge | None = None,
) -> str:
    """Classify whether the response recommends the tracked brand."""
    if brand_mentioned is None:
        brand_mentioned = check_brand_mentioned(response_text, brand)
    if not brand_mentioned:
        return RECOMMENDATION_STATUS_NOT_MENTIONED
    if not enabled:
        return RECOMMENDATION_STATUS_NOT_JUDGED

    try:
        raw_status = (judge or _call_recommendation_judge)(response_text, brand)
    except Exception:
        return RECOMMENDATION_STATUS_JUDGE_FAILED

    status = raw_status.strip().casefold()
    if status in JUDGED_RECOMMENDATION_STATUSES:
        return status
    return RECOMMENDATION_STATUS_JUDGE_FAILED


def _call_recommendation_judge(response_text: str, brand: Brand) -> str:
    """Ask Haiku to classify the tracked brand mention."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for recommendation judging")

    client = anthropic.Anthropic(api_key=api_key)
    model = os.environ.get(
        "SURFACED_RECOMMENDATION_JUDGE_MODEL",
        DEFAULT_RECOMMENDATION_JUDGE_MODEL,
    )
    response = client.messages.create(
        model=model,
        max_tokens=8,
        temperature=0,
        system=(
            "Classify whether the answer recommends the tracked brand. "
            "Reply with exactly one label: recommended, neutral, negative."
        ),
        messages=[{
            "role": "user",
            "content": "\n".join([
                f"Brand: {brand.name}",
                f"Aliases: {', '.join(brand.aliases) if brand.aliases else '-'}",
                "Answer:",
                response_text,
            ]),
        }],
    )

    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text
    return text
