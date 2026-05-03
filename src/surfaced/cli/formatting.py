"""CLI output formatting helpers."""

from collections.abc import Mapping, Sequence

from tabulate import tabulate


def _format_markdown_cell(value: object) -> str:
    """Format a single value for use inside a Markdown table cell."""
    if value is None:
        return "-"
    text = str(value)
    text = " ".join(text.splitlines())
    return text.replace("|", r"\|")


def format_markdown_table(
    rows: Sequence[Mapping[str, object]],
    columns: Sequence[str] | None = None,
) -> str:
    """Format rows as a GitHub-style Markdown table."""
    if not rows:
        return ""

    column_names = list(columns) if columns is not None else list(rows[0].keys())
    table_rows = [
        [_format_markdown_cell(row.get(col)) for col in column_names]
        for row in rows
    ]
    return tabulate(
        table_rows,
        headers=[_format_markdown_cell(col) for col in column_names],
        tablefmt="github",
        disable_numparse=True,
    )
