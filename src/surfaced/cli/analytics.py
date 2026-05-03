"""Analytics CLI commands."""

import csv
import io
import json
import os
from uuid import UUID

import click

from surfaced.db.queries import QueryService

def _find_queries_dir():
    """Find the clickhouse/queries/ directory."""
    # Check relative to the package installation
    pkg_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    candidate = os.path.join(pkg_dir, "clickhouse", "queries")
    if os.path.isdir(candidate):
        return candidate

    # Check ~/.surfaced/ (where install.sh clones the repo)
    home_candidate = os.path.join(os.path.expanduser("~"), ".surfaced", "clickhouse", "queries")
    if os.path.isdir(home_candidate):
        return home_candidate

    # Fall back to walking up from CWD
    current = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(current, "clickhouse", "queries")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def _available_queries(queries_dir: str) -> list[str]:
    """List available query names (filenames without .sql)."""
    if not queries_dir or not os.path.isdir(queries_dir):
        return []
    return sorted(
        f.replace(".sql", "")
        for f in os.listdir(queries_dir)
        if f.endswith(".sql")
    )


def _format_table(rows: list[dict]) -> str:
    """Format rows as an aligned text table."""
    if not rows:
        return "No results."
    columns = list(rows[0].keys())
    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            widths[col] = max(widths[col], len(str(row[col])))

    header = "  ".join(col.ljust(widths[col]) for col in columns)
    separator = "  ".join("-" * widths[col] for col in columns)
    lines = [header, separator]
    for row in rows:
        lines.append("  ".join(str(row[col]).ljust(widths[col]) for col in columns))
    return "\n".join(lines)


def _format_csv(rows: list[dict]) -> str:
    """Format rows as CSV."""
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


@click.command()
@click.argument("query_name")
@click.option("--brand", required=True, help="Brand ID or name")
@click.option("--days", default=30, type=int, help="Lookback period in days")
@click.option("--format", "fmt", default="table", type=click.Choice(["table", "json", "csv"]))
def analytics(query_name, brand, days, fmt):
    """Run a pre-built analytics query.

    \b
    Available queries:
      summary              Overall dashboard: total runs, mention rate, avg latency
      mention_frequency    Mention rate over time, grouped by day and branded split
      share_of_voice       Brand vs competitor mention share, by category and branded split
      provider_comparison  Visibility comparison across AI providers and branded split
      consistency          Response stability for repeated prompts

    \b
    Examples:
      surfaced analytics summary --brand "Acme" --days 30
      surfaced analytics mention_frequency --brand "Acme" --days 7
      surfaced analytics provider_comparison --brand "Acme" --days 30
      surfaced analytics share_of_voice --brand "Acme" --format json

    \b
    CONTEXT FOR AGENTS:
      This is the primary way to read results after running prompts.
      Start with 'summary' for an overview, then drill into specific queries.
      --brand accepts a name or UUID. --days controls the lookback window.
      Use --format json for structured output you can parse. Use --format csv
      for spreadsheet-compatible output. The queries are SQL files in
      clickhouse/queries/ — you can inspect them to understand the exact metrics.
    """
    queries_dir = _find_queries_dir()
    if not queries_dir:
        click.echo("Error: Could not find clickhouse/queries/ directory.", err=True)
        raise SystemExit(1)

    available = _available_queries(queries_dir)
    if query_name not in available:
        click.echo(f"Unknown query: {query_name}", err=True)
        click.echo(f"Available: {', '.join(available)}", err=True)
        raise SystemExit(1)

    # Resolve brand
    qs = QueryService()
    try:
        brand_id = UUID(brand)
    except ValueError:
        brand_obj = qs.get_brand_by_name(brand)
        if not brand_obj:
            click.echo(f"Brand '{brand}' not found.", err=True)
            raise SystemExit(1)
        brand_id = brand_obj.id

    # Read and execute query
    sql_path = os.path.join(queries_dir, f"{query_name}.sql")
    with open(sql_path) as f:
        sql = f.read()

    # Strip comment lines for clean execution
    sql_lines = [line for line in sql.strip().split("\n") if not line.strip().startswith("--")]
    sql_clean = "\n".join(sql_lines)

    rows = qs.db.execute(sql_clean, parameters={"brand_id": str(brand_id), "days": days})

    if fmt == "json":
        # Convert non-serializable types
        for row in rows:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
                elif isinstance(v, UUID):
                    row[k] = str(v)
        click.echo(json.dumps(rows, indent=2))
    elif fmt == "csv":
        click.echo(_format_csv(rows))
    else:
        click.echo(_format_table(rows))
