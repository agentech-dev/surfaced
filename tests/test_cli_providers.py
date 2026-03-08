"""Tests for the providers CLI commands."""

from unittest.mock import MagicMock, patch
from uuid import UUID

from click.testing import CliRunner

from surfaced.cli.providers import providers
from surfaced.models.provider import Provider
from conftest import PROVIDER_ID, NOW


def _provider(**overrides):
    defaults = dict(
        id=PROVIDER_ID, name="Claude API", provider="anthropic",
        execution_mode="api", model="claude-sonnet-4-6",
        created_at=NOW, updated_at=NOW,
    )
    defaults.update(overrides)
    return Provider(**defaults)


@patch("surfaced.cli.providers._qs")
def test_add_provider_preset(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.insert_provider.side_effect = lambda p: p
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(providers, [
        "add", "--provider", "anthropic", "--mode", "api",
    ])
    assert result.exit_code == 0
    assert "Claude" in result.output
    mock_qs.insert_provider.assert_called_once()


@patch("surfaced.cli.providers._qs")
def test_add_provider_custom_overrides(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.insert_provider.side_effect = lambda p: p
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(providers, [
        "add", "--provider", "anthropic", "--mode", "api",
        "--name", "Custom Claude", "--model", "claude-opus-4-6",
    ])
    assert result.exit_code == 0
    prov = mock_qs.insert_provider.call_args[0][0]
    assert prov.name == "Custom Claude"
    assert prov.model == "claude-opus-4-6"


@patch("surfaced.cli.providers._qs")
def test_add_provider_missing_provider(mock_qs_fn):
    runner = CliRunner()
    result = runner.invoke(providers, ["add", "--mode", "api"])
    assert result.exit_code != 0


@patch("surfaced.cli.providers._qs")
def test_add_provider_missing_mode(mock_qs_fn):
    runner = CliRunner()
    result = runner.invoke(providers, ["add", "--provider", "anthropic"])
    assert result.exit_code != 0


@patch("surfaced.cli.providers._qs")
def test_list_providers(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_providers.return_value = [_provider()]
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(providers, ["list"])
    assert result.exit_code == 0
    assert "Claude API" in result.output


@patch("surfaced.cli.providers._qs")
def test_list_providers_empty(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_providers.return_value = []
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(providers, ["list"])
    assert result.exit_code == 0
    assert "No providers found" in result.output


@patch("surfaced.cli.providers._qs")
def test_list_providers_json(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_providers.return_value = [_provider()]
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(providers, ["list", "--format", "json"])
    assert result.exit_code == 0
    assert '"provider": "anthropic"' in result.output


@patch("surfaced.cli.providers._qs")
def test_show_provider(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_provider.return_value = _provider()
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(providers, ["show", str(PROVIDER_ID)])
    assert result.exit_code == 0
    assert "Claude API" in result.output


@patch("surfaced.cli.providers._qs")
def test_show_provider_json(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_provider.return_value = _provider()
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(providers, ["show", str(PROVIDER_ID), "--format", "json"])
    assert result.exit_code == 0
    assert '"provider": "anthropic"' in result.output
    assert '"model": "claude-sonnet-4-6"' in result.output


@patch("surfaced.cli.providers._qs")
def test_show_provider_not_found(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_provider.return_value = None
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(providers, ["show", str(PROVIDER_ID)])
    assert result.exit_code != 0


@patch("surfaced.cli.providers._qs")
def test_delete_provider(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(providers, ["delete", str(PROVIDER_ID)])
    assert result.exit_code == 0
    assert "deleted" in result.output
