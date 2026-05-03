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
from surfaced.models.canonical_position import CanonicalPosition


DEFAULT_RECOMMENDATION_JUDGE_MODEL = "claude-haiku-4-5"
DEFAULT_ALIGNMENT_JUDGE_MODEL = "claude-haiku-4-5"
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
ALIGNMENT_STATUS_NOT_APPLICABLE = "not_applicable"
ALIGNMENT_STATUS_JUDGE_FAILED = "judge_failed"
JUDGED_ALIGNMENT_STATUSES = {"aligned", "partial", "misaligned", "silent"}
ALIGNMENT_STATUSES = {
    ALIGNMENT_STATUS_NOT_APPLICABLE,
    ALIGNMENT_STATUS_JUDGE_FAILED,
    *JUDGED_ALIGNMENT_STATUSES,
}
RecommendationJudge = Callable[[str, Brand], str]
AlignmentJudge = Callable[[str, CanonicalPosition], str]


@dataclass
class RecommendationJudgmentResult:
    status: str
    judge_model: str
    raw_output: str = ""
    error_message: str = ""
    latency_ms: int = 0
    attempted: bool = False


@dataclass
class AlignmentJudgmentResult:
    status: str
    judge_model: str
    rationale: str = ""
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


def get_alignment_judge_model() -> str:
    """Return the configured alignment judge model."""
    return os.environ.get(
        "SURFACED_ALIGNMENT_JUDGE_MODEL",
        DEFAULT_ALIGNMENT_JUDGE_MODEL,
    )


def classify_alignment(
    response_text: str,
    canonical_position: CanonicalPosition | None,
    *,
    enabled: bool = True,
    judge: AlignmentJudge | None = None,
) -> str:
    """Classify whether the response aligns to a canonical position."""
    return judge_alignment(
        response_text,
        canonical_position,
        enabled=enabled,
        judge=judge,
    ).status


def judge_alignment(
    response_text: str,
    canonical_position: CanonicalPosition | None,
    *,
    enabled: bool = True,
    judge: AlignmentJudge | None = None,
) -> AlignmentJudgmentResult:
    """Classify response alignment and retain audit details for judge attempts."""
    judge_model = get_alignment_judge_model()
    if not enabled or canonical_position is None:
        return AlignmentJudgmentResult(
            status=ALIGNMENT_STATUS_NOT_APPLICABLE,
            judge_model=judge_model,
        )

    start = perf_counter()
    try:
        raw_output = (judge or _call_alignment_judge)(response_text, canonical_position)
    except Exception as exc:
        return AlignmentJudgmentResult(
            status=ALIGNMENT_STATUS_JUDGE_FAILED,
            judge_model=judge_model,
            error_message=str(exc),
            latency_ms=int((perf_counter() - start) * 1000),
            attempted=True,
        )

    status, rationale = _parse_alignment_output(raw_output)
    if status in JUDGED_ALIGNMENT_STATUSES:
        return AlignmentJudgmentResult(
            status=status,
            judge_model=judge_model,
            rationale=rationale,
            raw_output=raw_output,
            latency_ms=int((perf_counter() - start) * 1000),
            attempted=True,
        )
    return AlignmentJudgmentResult(
        status=ALIGNMENT_STATUS_JUDGE_FAILED,
        judge_model=judge_model,
        raw_output=raw_output,
        error_message="Could not parse an alignment status",
        latency_ms=int((perf_counter() - start) * 1000),
        attempted=True,
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


def _call_alignment_judge(
    response_text: str,
    canonical_position: CanonicalPosition,
) -> str:
    """Ask Haiku to classify response alignment to the canonical position."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for alignment judging")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=get_alignment_judge_model(),
        max_tokens=128,
        temperature=0,
        system=(
            "Classify whether the answer reflects the canonical position. "
            "Return a short rationale."
        ),
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["aligned", "partial", "misaligned", "silent"],
                        },
                        "rationale": {
                            "type": "string",
                        },
                    },
                    "required": ["status", "rationale"],
                    "additionalProperties": False,
                },
            },
        },
        messages=[{
            "role": "user",
            "content": _build_alignment_judge_prompt(
                response_text,
                canonical_position,
            ),
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


def _build_alignment_judge_prompt(
    response_text: str,
    canonical_position: CanonicalPosition,
) -> str:
    """Build the alignment judge prompt with explicit tagged sections."""
    return "\n".join([
        "<instructions>",
        "Judge whether the answer reflects the canonical position.",
        "Return aligned when the answer clearly supports the canonical position.",
        "Return partial when the answer is directionally compatible but incomplete or mixed.",
        "Return misaligned when the answer contradicts the canonical position.",
        "Return silent when the answer does not address the canonical position.",
        "Keep the rationale to one short sentence.",
        "</instructions>",
        f"<topic>{canonical_position.topic}</topic>",
        "<canonical_position>",
        canonical_position.statement,
        "</canonical_position>",
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


def _parse_alignment_output(raw_output: str) -> tuple[str, str]:
    """Parse structured alignment output, with a tolerant label fallback."""
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        status = str(parsed.get("status", "")).casefold()
        if status in JUDGED_ALIGNMENT_STATUSES:
            return status, str(parsed.get("rationale", "")).strip()

    match = re.match(
        r"^[\s*_`#>-]*(aligned|partial|misaligned|silent)\b[:\s-]*(.*)",
        raw_output.strip(),
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(1).casefold(), " ".join(match.group(2).split())
    return "", ""
