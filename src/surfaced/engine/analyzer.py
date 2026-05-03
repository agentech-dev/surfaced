"""Post-response analysis for brand mentions and recommendation status."""

from __future__ import annotations

import os
import re
import json
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

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


@dataclass
class RecommendationJudgmentResult:
    status: str
    judge_model: str
    raw_output: str = ""
    error_message: str = ""
    latency_ms: int = 0
    attempted: bool = False


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
    return judge_recommendation(
        response_text,
        brand,
        brand_mentioned=brand_mentioned,
        enabled=enabled,
        judge=judge,
    ).status


def judge_recommendation(
    response_text: str,
    brand: Brand,
    *,
    brand_mentioned: bool | None = None,
    enabled: bool = True,
    judge: RecommendationJudge | None = None,
) -> RecommendationJudgmentResult:
    """Classify a recommendation and retain audit details for judge attempts."""
    judge_model = get_recommendation_judge_model()
    if brand_mentioned is None:
        brand_mentioned = check_brand_mentioned(response_text, brand)
    if not brand_mentioned:
        return RecommendationJudgmentResult(
            status=RECOMMENDATION_STATUS_NOT_MENTIONED,
            judge_model=judge_model,
        )
    if not enabled:
        return RecommendationJudgmentResult(
            status=RECOMMENDATION_STATUS_NOT_JUDGED,
            judge_model=judge_model,
        )

    start = perf_counter()
    try:
        raw_status = (judge or _call_recommendation_judge)(response_text, brand)
    except Exception as exc:
        return RecommendationJudgmentResult(
            status=RECOMMENDATION_STATUS_JUDGE_FAILED,
            judge_model=judge_model,
            error_message=str(exc),
            latency_ms=int((perf_counter() - start) * 1000),
            attempted=True,
        )

    status = _parse_recommendation_status(raw_status)
    if status in JUDGED_RECOMMENDATION_STATUSES:
        return RecommendationJudgmentResult(
            status=status,
            judge_model=judge_model,
            raw_output=raw_status,
            latency_ms=int((perf_counter() - start) * 1000),
            attempted=True,
        )
    return RecommendationJudgmentResult(
        status=RECOMMENDATION_STATUS_JUDGE_FAILED,
        judge_model=judge_model,
        raw_output=raw_status,
        error_message="Could not parse a leading recommendation label",
        latency_ms=int((perf_counter() - start) * 1000),
        attempted=True,
    )


def get_recommendation_judge_model() -> str:
    """Return the configured recommendation judge model."""
    return os.environ.get(
        "SURFACED_RECOMMENDATION_JUDGE_MODEL",
        DEFAULT_RECOMMENDATION_JUDGE_MODEL,
    )


def _call_recommendation_judge(response_text: str, brand: Brand) -> str:
    """Ask Haiku to classify the tracked brand mention."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for recommendation judging")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=get_recommendation_judge_model(),
        max_tokens=32,
        temperature=0,
        system=(
            "Classify whether the answer recommends the tracked brand. "
            "Judge only the tracked brand, not competitors."
        ),
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["recommended", "neutral", "negative"],
                        },
                    },
                    "required": ["status"],
                    "additionalProperties": False,
                },
            },
        },
        messages=[{
            "role": "user",
            "content": _build_recommendation_judge_prompt(response_text, brand),
        }],
    )

    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text
    return text


def _build_recommendation_judge_prompt(response_text: str, brand: Brand) -> str:
    """Build the recommendation judge prompt with explicit tagged sections."""
    return "\n".join([
        "<instructions>",
        "Classify only the tracked brand reference in the answer.",
        "Return recommended when the answer endorses the brand or presents it as a good fit.",
        "Return negative when the answer discourages using the brand or presents it as a poor fit.",
        "Return neutral when the answer only mentions or compares the brand without a clear recommendation.",
        "</instructions>",
        f"<brand>{brand.name}</brand>",
        "<aliases>",
        "\n".join(brand.aliases) if brand.aliases else "-",
        "</aliases>",
        "<answer>",
        response_text,
        "</answer>",
    ])


def _parse_recommendation_status(raw_output: str) -> str:
    """Parse structured judge output, with a tolerant label fallback."""
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        status = str(parsed.get("status", "")).casefold()
        if status in JUDGED_RECOMMENDATION_STATUSES:
            return status

    match = re.match(
        r"^[\s*_`#>-]*(recommended|neutral|negative)\b",
        raw_output.strip(),
        flags=re.IGNORECASE,
    )
    return match.group(1).casefold() if match else ""
