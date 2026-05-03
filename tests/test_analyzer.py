"""Tests for the brand mention analyzer."""

from uuid import uuid4

from surfaced.engine.analyzer import (
    check_brand_mentioned,
    classify_recommendation,
    find_competitors_mentioned,
    is_recommendation_judge_enabled,
    is_prompt_branded,
    judge_recommendation,
)
from surfaced.models.brand import Brand


def _make_brand(**kwargs):
    defaults = dict(name="Acme", aliases=["ACME", "Acme Corp"], competitors=["Globex", "Initech"])
    defaults.update(kwargs)
    return Brand(id=uuid4(), **defaults)


def test_brand_mentioned_by_name():
    brand = _make_brand()
    assert check_brand_mentioned("I recommend Acme for this task.", brand)


def test_brand_mentioned_by_alias():
    brand = _make_brand()
    assert check_brand_mentioned("ACME is a great choice.", brand)


def test_brand_not_mentioned():
    brand = _make_brand()
    assert not check_brand_mentioned("I recommend Widget Co for this task.", brand)


def test_brand_mentioned_case_insensitive():
    brand = _make_brand()
    assert check_brand_mentioned("acme is the best option.", brand)


def test_competitors_found():
    brand = _make_brand()
    result = find_competitors_mentioned(
        "Both Globex and Initech offer similar products.", brand
    )
    assert set(result) == {"Globex", "Initech"}


def test_no_competitors_found():
    brand = _make_brand()
    result = find_competitors_mentioned("No relevant companies mentioned.", brand)
    assert result == []


def test_partial_competitors():
    brand = _make_brand()
    result = find_competitors_mentioned("Globex has a strong offering.", brand)
    assert result == ["Globex"]


def test_prompt_branded_by_name():
    brand = _make_brand()
    assert is_prompt_branded("How does Acme compare to Globex?", brand)


def test_prompt_branded_by_alias():
    brand = _make_brand()
    assert is_prompt_branded("Is Acme Corp good for enterprise teams?", brand)


def test_prompt_branded_case_insensitive():
    brand = _make_brand()
    assert is_prompt_branded("is acme good for enterprise teams?", brand)


def test_prompt_unbranded():
    brand = _make_brand()
    assert not is_prompt_branded("What are the best CRM tools?", brand)


def test_recommendation_not_mentioned():
    brand = _make_brand()

    result = classify_recommendation(
        "Widget Co is a better fit.",
        brand,
        judge=lambda response, brand: "recommended",
    )

    assert result == "not_mentioned"


def test_recommendation_not_judged_when_disabled():
    brand = _make_brand()

    result = classify_recommendation(
        "Acme is a strong fit.",
        brand,
        enabled=False,
        judge=lambda response, brand: "recommended",
    )

    assert result == "not_judged"


def test_recommendation_not_judged_is_not_an_attempt():
    brand = _make_brand()

    result = judge_recommendation(
        "Acme is a strong fit.",
        brand,
        enabled=False,
        judge=lambda response, brand: "recommended",
    )

    assert result.status == "not_judged"
    assert result.attempted is False


def test_recommendation_recommended():
    brand = _make_brand()

    result = classify_recommendation(
        "Acme is a strong fit.",
        brand,
        judge=lambda response, brand: "recommended",
    )

    assert result == "recommended"


def test_recommendation_result_stores_raw_output():
    brand = _make_brand()

    result = judge_recommendation(
        "Acme is a strong fit.",
        brand,
        judge=lambda response, brand: '{"status":"recommended"}',
    )

    assert result.status == "recommended"
    assert result.raw_output == '{"status":"recommended"}'
    assert result.error_message == ""
    assert result.attempted is True


def test_recommendation_parses_structured_output():
    brand = _make_brand()

    result = judge_recommendation(
        "Acme is a strong fit.",
        brand,
        judge=lambda response, brand: '{"status": "recommended"}',
    )

    assert result.status == "recommended"
    assert result.raw_output == '{"status": "recommended"}'
    assert result.error_message == ""


def test_recommendation_parses_markdown_label_with_explanation():
    brand = _make_brand()

    result = judge_recommendation(
        "Acme is a strong fit.",
        brand,
        judge=lambda response, brand: "**recommended**  The answer recommends it.",
    )

    assert result.status == "recommended"
    assert result.raw_output == "**recommended**  The answer recommends it."
    assert result.error_message == ""


def test_recommendation_parses_plain_label_with_explanation():
    brand = _make_brand()

    result = judge_recommendation(
        "Acme is one of several tools.",
        brand,
        judge=lambda response, brand: "neutral  The answer only mentions it.",
    )

    assert result.status == "neutral"
    assert result.raw_output == "neutral  The answer only mentions it."
    assert result.error_message == ""


def test_recommendation_neutral():
    brand = _make_brand()

    result = classify_recommendation(
        "Acme is one of several available tools.",
        brand,
        judge=lambda response, brand: "neutral",
    )

    assert result == "neutral"


def test_recommendation_negative():
    brand = _make_brand()

    result = classify_recommendation(
        "I would avoid Acme for this use case.",
        brand,
        judge=lambda response, brand: "negative",
    )

    assert result == "negative"


def test_recommendation_invalid_judge_output_fails():
    brand = _make_brand()

    result = classify_recommendation(
        "Acme is a strong fit.",
        brand,
        judge=lambda response, brand: "probably",
    )

    assert result == "judge_failed"


def test_recommendation_invalid_result_stores_raw_output_and_error():
    brand = _make_brand()

    result = judge_recommendation(
        "Acme is a strong fit.",
        brand,
        judge=lambda response, brand: "probably",
    )

    assert result.status == "judge_failed"
    assert result.raw_output == "probably"
    assert "Could not parse" in result.error_message
    assert result.attempted is True


def test_recommendation_judge_exception_fails():
    brand = _make_brand()

    def judge(response, brand):
        raise RuntimeError("judge failed")

    result = classify_recommendation("Acme is a strong fit.", brand, judge=judge)

    assert result == "judge_failed"


def test_recommendation_exception_result_stores_error():
    brand = _make_brand()

    def judge(response, brand):
        raise RuntimeError("judge failed")

    result = judge_recommendation("Acme is a strong fit.", brand, judge=judge)

    assert result.status == "judge_failed"
    assert result.raw_output == ""
    assert result.error_message == "judge failed"
    assert result.attempted is True


def test_recommendation_global_toggle_defaults_enabled(monkeypatch):
    monkeypatch.delenv("SURFACED_RECOMMENDATION_JUDGE_ENABLED", raising=False)

    assert is_recommendation_judge_enabled()


def test_recommendation_global_toggle_false(monkeypatch):
    monkeypatch.setenv("SURFACED_RECOMMENDATION_JUDGE_ENABLED", "false")

    assert not is_recommendation_judge_enabled()
