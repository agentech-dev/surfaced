"""Tests for the analytics CLI command."""

from unittest.mock import MagicMock, patch
from uuid import UUID

from click.testing import CliRunner

from surfaced.cli.analytics import analytics, _format_table, _format_csv
from surfaced.models.brand import Brand
from conftest import BRAND_ID, NOW


@patch("surfaced.cli.analytics.QueryService")
@patch("surfaced.cli.analytics._find_queries_dir")
def test_analytics_table_format(mock_find, mock_qs_cls, tmp_path):
    sql_file = tmp_path / "summary.sql"
    sql_file.write_text("SELECT 1 as total")
    mock_find.return_value = str(tmp_path)

    mock_qs = MagicMock()
    mock_qs.db.execute.return_value = [{"total": 42}]
    mock_qs_cls.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(analytics, [
        "summary", "--brand", str(BRAND_ID),
    ])
    assert result.exit_code == 0
    assert "42" in result.output


@patch("surfaced.cli.analytics.QueryService")
@patch("surfaced.cli.analytics._find_queries_dir")
def test_analytics_json_format(mock_find, mock_qs_cls, tmp_path):
    sql_file = tmp_path / "summary.sql"
    sql_file.write_text("SELECT 1 as total")
    mock_find.return_value = str(tmp_path)

    mock_qs = MagicMock()
    mock_qs.db.execute.return_value = [{"total": 42}]
    mock_qs_cls.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(analytics, [
        "summary", "--brand", str(BRAND_ID), "--format", "json",
    ])
    assert result.exit_code == 0
    assert '"total": 42' in result.output


@patch("surfaced.cli.analytics.QueryService")
@patch("surfaced.cli.analytics._find_queries_dir")
def test_analytics_csv_format(mock_find, mock_qs_cls, tmp_path):
    sql_file = tmp_path / "summary.sql"
    sql_file.write_text("SELECT 1 as total")
    mock_find.return_value = str(tmp_path)

    mock_qs = MagicMock()
    mock_qs.db.execute.return_value = [{"total": 42, "rate": 0.5}]
    mock_qs_cls.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(analytics, [
        "summary", "--brand", str(BRAND_ID), "--format", "csv",
    ])
    assert result.exit_code == 0
    assert "total" in result.output
    assert "42" in result.output


@patch("surfaced.cli.analytics.QueryService")
@patch("surfaced.cli.analytics._find_queries_dir")
def test_analytics_unknown_query(mock_find, mock_qs_cls, tmp_path):
    mock_find.return_value = str(tmp_path)

    runner = CliRunner()
    result = runner.invoke(analytics, [
        "nonexistent", "--brand", str(BRAND_ID),
    ])
    assert result.exit_code != 0


@patch("surfaced.cli.analytics.QueryService")
@patch("surfaced.cli.analytics._find_queries_dir")
def test_analytics_brand_name_resolution(mock_find, mock_qs_cls, tmp_path):
    sql_file = tmp_path / "summary.sql"
    sql_file.write_text("SELECT 1")
    mock_find.return_value = str(tmp_path)

    mock_qs = MagicMock()
    mock_qs.get_brand_by_name.return_value = Brand(
        id=BRAND_ID, name="Acme", created_at=NOW, updated_at=NOW,
    )
    mock_qs.db.execute.return_value = []
    mock_qs_cls.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(analytics, [
        "summary", "--brand", "Acme",
    ])
    assert result.exit_code == 0
    mock_qs.get_brand_by_name.assert_called_once_with("Acme")


@patch("surfaced.cli.analytics.QueryService")
@patch("surfaced.cli.analytics._find_queries_dir")
def test_analytics_brand_not_found(mock_find, mock_qs_cls, tmp_path):
    sql_file = tmp_path / "summary.sql"
    sql_file.write_text("SELECT 1")
    mock_find.return_value = str(tmp_path)

    mock_qs = MagicMock()
    mock_qs.get_brand_by_name.return_value = None
    mock_qs_cls.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(analytics, [
        "summary", "--brand", "Missing",
    ])
    assert result.exit_code != 0


@patch("surfaced.cli.analytics._find_queries_dir")
def test_analytics_no_queries_dir(mock_find):
    mock_find.return_value = None

    runner = CliRunner()
    result = runner.invoke(analytics, [
        "summary", "--brand", str(BRAND_ID),
    ])
    assert result.exit_code != 0


# --- Helper tests ---

def test_format_table_empty():
    assert _format_table([]) == "No results."


def test_format_table_with_data():
    rows = [{"name": "Acme", "count": 10}, {"name": "Globex", "count": 5}]
    output = _format_table(rows)
    assert "name" in output
    assert "count" in output
    assert "Acme" in output
    assert "Globex" in output
    # Should have header separator
    assert "---" in output


def test_format_csv_empty():
    assert _format_csv([]) == ""


def test_format_csv_with_data():
    rows = [{"name": "Acme", "count": 10}]
    output = _format_csv(rows)
    assert "name,count" in output
    assert "Acme,10" in output
