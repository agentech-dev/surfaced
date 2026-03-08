"""Tests for the brands CLI commands."""

from unittest.mock import MagicMock, patch
from uuid import UUID

from click.testing import CliRunner

from surfaced.cli.brands import brands
from surfaced.models.brand import Brand
from conftest import BRAND_ID, NOW


def _brand(**overrides):
    defaults = dict(
        id=BRAND_ID, name="Acme", domain="acme.com", description="Test",
        aliases=["ACME"], competitors=["Globex"],
        created_at=NOW, updated_at=NOW,
    )
    defaults.update(overrides)
    return Brand(**defaults)


@patch("surfaced.cli.brands._qs")
def test_add_brand(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.insert_brand.side_effect = lambda b: b
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(brands, [
        "add", "--name", "Acme", "--domain", "acme.com",
        "--aliases", "ACME,Acme Corp", "--competitors", "Globex",
    ])
    assert result.exit_code == 0
    assert "Acme" in result.output
    mock_qs.insert_brand.assert_called_once()


@patch("surfaced.cli.brands._qs")
def test_add_brand_json(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.insert_brand.side_effect = lambda b: b
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(brands, [
        "add", "--name", "Acme", "--format", "json",
    ])
    assert result.exit_code == 0
    assert '"name": "Acme"' in result.output


@patch("surfaced.cli.brands._qs")
def test_add_brand_no_aliases(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.insert_brand.side_effect = lambda b: b
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(brands, ["add", "--name", "Simple"])
    assert result.exit_code == 0
    brand_arg = mock_qs.insert_brand.call_args[0][0]
    assert brand_arg.aliases == []
    assert brand_arg.competitors == []


@patch("surfaced.cli.brands._qs")
def test_list_brands(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_brands.return_value = [_brand()]
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(brands, ["list"])
    assert result.exit_code == 0
    assert "Acme" in result.output


@patch("surfaced.cli.brands._qs")
def test_list_brands_empty(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_brands.return_value = []
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(brands, ["list"])
    assert result.exit_code == 0
    assert "No brands found" in result.output


@patch("surfaced.cli.brands._qs")
def test_list_brands_json(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_brands.return_value = [_brand()]
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(brands, ["list", "--format", "json"])
    assert result.exit_code == 0
    assert '"name": "Acme"' in result.output


@patch("surfaced.cli.brands._qs")
def test_show_brand(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_brand.return_value = _brand()
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(brands, ["show", str(BRAND_ID)])
    assert result.exit_code == 0
    assert "Acme" in result.output


@patch("surfaced.cli.brands._qs")
def test_show_brand_json(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_brand.return_value = _brand()
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(brands, ["show", str(BRAND_ID), "--format", "json"])
    assert result.exit_code == 0
    assert '"name": "Acme"' in result.output
    assert '"domain": "acme.com"' in result.output


@patch("surfaced.cli.brands._qs")
def test_show_brand_not_found(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_brand.return_value = None
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(brands, ["show", str(BRAND_ID)])
    assert result.exit_code != 0


@patch("surfaced.cli.brands._qs")
def test_edit_brand(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_brand.return_value = _brand()
    mock_qs.update_brand.side_effect = lambda b: b
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(brands, [
        "edit", str(BRAND_ID), "--name", "Acme Inc",
    ])
    assert result.exit_code == 0
    updated = mock_qs.update_brand.call_args[0][0]
    assert updated.name == "Acme Inc"


@patch("surfaced.cli.brands._qs")
def test_edit_brand_not_found(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_brand.return_value = None
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(brands, ["edit", str(BRAND_ID), "--name", "X"])
    assert result.exit_code != 0


@patch("surfaced.cli.brands._qs")
def test_delete_brand(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(brands, ["delete", str(BRAND_ID)])
    assert result.exit_code == 0
    assert "deleted" in result.output
    mock_qs.delete_brand.assert_called_once()
