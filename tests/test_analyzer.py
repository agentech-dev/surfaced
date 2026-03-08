"""Tests for the brand mention analyzer."""

from uuid import uuid4

from surfaced.engine.analyzer import check_brand_mentioned, find_competitors_mentioned
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


def test_empty_response():
    brand = _make_brand()
    assert not check_brand_mentioned("", brand)
    assert find_competitors_mentioned("", brand) == []


def test_empty_aliases():
    brand = _make_brand(aliases=[])
    # Brand name "Acme" still matches case-insensitively
    assert check_brand_mentioned("Acme is great.", brand)
    assert check_brand_mentioned("ACME is great.", brand)
    # But an alias-only term like "Acme Corp" should NOT match
    assert not check_brand_mentioned("Acme Corp is great.", _make_brand(name="XYZ", aliases=[]))


def test_competitors_case_insensitive():
    brand = _make_brand()
    result = find_competitors_mentioned("globex is a competitor.", brand)
    assert result == ["Globex"]


def test_empty_competitors():
    brand = _make_brand(competitors=[])
    result = find_competitors_mentioned("Globex and Initech", brand)
    assert result == []
