"""Tests for the runs CLI commands."""

from unittest.mock import MagicMock, patch
from uuid import UUID

from click.testing import CliRunner

from surfaced.cli.runs import runs
from surfaced.models.run import Run
from conftest import RUN_ID, NOW


def _run(**overrides):
    defaults = dict(
        id=RUN_ID, name="Test Run", status="completed",
        total_prompts=5, completed_prompts=5,
        started_at=NOW, finished_at=NOW,
        created_at=NOW, updated_at=NOW,
    )
    defaults.update(overrides)
    return Run(**defaults)


@patch("surfaced.cli.runs._qs")
def test_list_runs(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_runs.return_value = [_run()]
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(runs, ["list"])
    assert result.exit_code == 0
    assert "Test Run" in result.output


@patch("surfaced.cli.runs._qs")
def test_list_runs_empty(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_runs.return_value = []
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(runs, ["list"])
    assert result.exit_code == 0
    assert "No runs found" in result.output


@patch("surfaced.cli.runs._qs")
def test_list_runs_json(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_runs.return_value = [_run()]
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(runs, ["list", "--format", "json"])
    assert result.exit_code == 0
    assert '"status": "completed"' in result.output


@patch("surfaced.cli.runs._qs")
def test_list_runs_custom_limit(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_runs.return_value = []
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(runs, ["list", "--limit", "5"])
    assert result.exit_code == 0
    mock_qs.get_runs.assert_called_once_with(limit=5)


@patch("surfaced.cli.runs._qs")
def test_show_run(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_run.return_value = _run()
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(runs, ["show", str(RUN_ID)])
    assert result.exit_code == 0
    assert "Test Run" in result.output


@patch("surfaced.cli.runs._qs")
def test_show_run_json(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_run.return_value = _run()
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(runs, ["show", str(RUN_ID), "--format", "json"])
    assert result.exit_code == 0
    assert '"status": "completed"' in result.output
    assert '"name": "Test Run"' in result.output


@patch("surfaced.cli.runs._qs")
def test_show_run_not_found(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_run.return_value = None
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(runs, ["show", str(RUN_ID)])
    assert result.exit_code != 0
