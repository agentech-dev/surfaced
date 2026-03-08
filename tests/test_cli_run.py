"""Tests for the run CLI command."""

from unittest.mock import MagicMock, patch
from uuid import UUID

from click.testing import CliRunner

from surfaced.cli.run import run
from surfaced.models.brand import Brand
from surfaced.models.run import Run
from conftest import BRAND_ID, NOW


@patch("surfaced.cli.run.execute_run")
@patch("surfaced.cli.run.QueryService")
def test_run_default(mock_qs_cls, mock_execute):
    mock_execute.return_value = Run(name="R", created_at=NOW, updated_at=NOW)
    runner = CliRunner()
    result = runner.invoke(run, [])
    assert result.exit_code == 0
    mock_execute.assert_called_once()
    kwargs = mock_execute.call_args[1]
    assert kwargs["brand_id"] is None
    assert kwargs["dry_run"] is False


@patch("surfaced.cli.run.execute_run")
@patch("surfaced.cli.run.QueryService")
def test_run_brand_name_resolution(mock_qs_cls, mock_execute):
    mock_qs = MagicMock()
    mock_qs.get_brand_by_name.return_value = Brand(
        id=BRAND_ID, name="Acme", created_at=NOW, updated_at=NOW,
    )
    mock_qs_cls.return_value = mock_qs
    mock_execute.return_value = None

    runner = CliRunner()
    result = runner.invoke(run, ["--brand", "Acme"])
    assert result.exit_code == 0
    kwargs = mock_execute.call_args[1]
    assert kwargs["brand_id"] == BRAND_ID


@patch("surfaced.cli.run.execute_run")
@patch("surfaced.cli.run.QueryService")
def test_run_brand_uuid(mock_qs_cls, mock_execute):
    mock_execute.return_value = None
    runner = CliRunner()
    result = runner.invoke(run, ["--brand", str(BRAND_ID)])
    assert result.exit_code == 0
    kwargs = mock_execute.call_args[1]
    assert kwargs["brand_id"] == BRAND_ID


@patch("surfaced.cli.run.execute_run")
@patch("surfaced.cli.run.QueryService")
def test_run_brand_not_found(mock_qs_cls, mock_execute):
    mock_qs = MagicMock()
    mock_qs.get_brand_by_name.return_value = None
    mock_qs_cls.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(run, ["--brand", "NonExistent"])
    assert result.exit_code != 0


@patch("surfaced.cli.run.execute_run")
@patch("surfaced.cli.run.QueryService")
def test_run_all_filters(mock_qs_cls, mock_execute):
    mock_execute.return_value = None
    runner = CliRunner()
    result = runner.invoke(run, [
        "--category", "brand_query", "--provider", "Claude API",
        "--tag", "daily", "--brand", str(BRAND_ID),
    ])
    assert result.exit_code == 0
    kwargs = mock_execute.call_args[1]
    assert kwargs["category"] == "brand_query"
    assert kwargs["provider_name"] == "Claude API"
    assert kwargs["tag"] == "daily"


@patch("surfaced.cli.run.execute_run")
@patch("surfaced.cli.run.QueryService")
def test_run_dry_run(mock_qs_cls, mock_execute):
    mock_execute.return_value = None
    runner = CliRunner()
    result = runner.invoke(run, ["--dry-run"])
    assert result.exit_code == 0
    kwargs = mock_execute.call_args[1]
    assert kwargs["dry_run"] is True
