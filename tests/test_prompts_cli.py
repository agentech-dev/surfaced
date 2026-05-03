"""Tests for prompt CLI helpers."""

from uuid import uuid4

import pytest
from click.testing import CliRunner

from surfaced.cli.main import cli
from surfaced.cli.prompts import _resolve_brand_id, prompts
from surfaced.models.brand import Brand


class _FakeQueryService:
    def __init__(self, brands):
        self._brands = brands

    def get_brand_by_name(self, name):
        return next((b for b in self._brands if b.name == name and b.is_active), None)

    def get_brands(self, active_only=True):
        if active_only:
            return [b for b in self._brands if b.is_active]
        return self._brands


def test_prompts_add_help_uses_free_form_category():
    result = CliRunner().invoke(prompts, ["add", "--help"])
    assert result.exit_code == 0
    assert "--category TEXT" in result.output
    assert "brand_query" not in result.output


def test_providers_add_help_omits_available_combinations():
    result = CliRunner().invoke(cli, ["providers", "add", "--help"])

    assert result.exit_code == 0
    assert "Available combinations" not in result.output
    assert "model=claude-sonnet-4-6" not in result.output


def test_resolve_brand_id_accepts_uuid():
    brand_id = uuid4()
    assert _resolve_brand_id(_FakeQueryService([]), str(brand_id)) == brand_id


def test_resolve_brand_id_accepts_case_insensitive_name():
    brand = Brand(id=uuid4(), name="ClickHouse")
    assert _resolve_brand_id(_FakeQueryService([brand]), "clickhouse") == brand.id


def test_resolve_brand_id_accepts_case_insensitive_alias():
    brand = Brand(id=uuid4(), name="ClickHouse", aliases=["CH"])
    assert _resolve_brand_id(_FakeQueryService([brand]), "ch") == brand.id


def test_resolve_brand_id_exits_for_missing_brand():
    with pytest.raises(SystemExit):
        _resolve_brand_id(_FakeQueryService([]), "missing")
