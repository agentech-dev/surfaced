"""Tests for the init CLI command."""

import os
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from surfaced.cli.init import init


@patch("clickhouse_connect.get_client")
@patch("surfaced.cli.init._find_clickhouse_dir")
def test_init_default_host_port(mock_find, mock_get_client, tmp_path):
    tables_dir = tmp_path / "tables"
    tables_dir.mkdir()
    (tables_dir / "001_brands.sql").write_text("CREATE TABLE IF NOT EXISTS brands (id UUID)")

    # Create empty materialized_views dir
    (tmp_path / "materialized_views").mkdir()

    mock_find.return_value = str(tmp_path)
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(init, [])
    assert result.exit_code == 0
    assert "Applied" in result.output
    mock_get_client.assert_called_once_with(host="localhost", port=8123)
    mock_client.command.assert_called()


@patch("clickhouse_connect.get_client")
@patch("surfaced.cli.init._find_clickhouse_dir")
def test_init_custom_host_port(mock_find, mock_get_client, tmp_path):
    tables_dir = tmp_path / "tables"
    tables_dir.mkdir()
    (tables_dir / "001_brands.sql").write_text("CREATE TABLE t (id UUID)")
    (tmp_path / "materialized_views").mkdir()

    mock_find.return_value = str(tmp_path)
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(init, ["--host", "ch-server", "--port", "9000"])
    assert result.exit_code == 0
    mock_get_client.assert_called_once_with(host="ch-server", port=9000)


@patch("clickhouse_connect.get_client")
@patch("surfaced.cli.init._find_clickhouse_dir")
def test_init_applies_multiple_sql_files(mock_find, mock_get_client, tmp_path):
    tables_dir = tmp_path / "tables"
    tables_dir.mkdir()
    (tables_dir / "001_brands.sql").write_text("CREATE TABLE brands (id UUID)")
    (tables_dir / "002_providers.sql").write_text("CREATE TABLE providers (id UUID)")

    mv_dir = tmp_path / "materialized_views"
    mv_dir.mkdir()
    (mv_dir / "001_daily.sql").write_text("CREATE MATERIALIZED VIEW daily AS SELECT 1")

    mock_find.return_value = str(tmp_path)
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(init, [])
    assert result.exit_code == 0
    assert "Applied 001_brands.sql" in result.output
    assert "Applied 002_providers.sql" in result.output
    assert "Applied 001_daily.sql" in result.output
    assert "3 schema files" in result.output
