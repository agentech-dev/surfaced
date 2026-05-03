"""Tests for run progress output formatting."""

from surfaced.engine.runner import (
    _format_run_log_row,
    _format_run_log_separator,
    _truncate_run_log_cell,
)


def test_run_log_row_formats_markdown_table_cells():
    row = _format_run_log_row([
        "1",
        "Claude Sonnet 4.6",
        "What are good open-source observability stacks for logs and traces?",
    ])

    assert row == (
        "| 1    | Claude Sonnet 4.6    | "
        "What are good open-source observability stacks for logs and t... |"
    )


def test_run_log_separator_uses_column_widths():
    assert _format_run_log_separator() == (
        "| ---- | -------------------- | "
        "---------------------------------------------------------------- |"
    )


def test_run_log_cell_truncates_and_escapes_pipes():
    assert _truncate_run_log_cell("abc | def ghi", 10) == r"abc \|..."


def test_run_log_row_can_show_configured_judge_model():
    row = _format_run_log_row([
        "1",
        "claude-haiku-4-5",
        "JUDGE: Was ClickHouse recommended?",
    ])

    assert "claude-haiku-4-5" in row
    assert "JUDGE: Was ClickHouse recommended?" in row
