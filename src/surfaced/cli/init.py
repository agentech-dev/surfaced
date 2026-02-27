"""Database initialization command."""

import glob
import os

import click


@click.command()
@click.option("--host", default="localhost", help="ClickHouse host")
@click.option("--port", default=8123, type=int, help="ClickHouse HTTP port")
def init(host, port):
    """Initialize the ClickHouse database schema.

    Runs all table and materialized view SQL files in order.
    Requires a running ClickHouse server (chv run server).
    """
    import clickhouse_connect

    client = clickhouse_connect.get_client(host=host, port=port)

    base_dir = _find_clickhouse_dir()
    if not base_dir:
        click.echo("Error: Could not find clickhouse/ directory.", err=True)
        raise SystemExit(1)

    sql_dirs = [
        os.path.join(base_dir, "tables"),
        os.path.join(base_dir, "materialized_views"),
    ]

    total = 0
    for sql_dir in sql_dirs:
        files = sorted(glob.glob(os.path.join(sql_dir, "*.sql")))
        for filepath in files:
            filename = os.path.basename(filepath)
            with open(filepath) as f:
                sql_content = f.read()

            # Split on semicolons to handle files with multiple statements
            statements = [s.strip() for s in sql_content.split(";") if s.strip()]
            for statement in statements:
                client.command(statement)

            click.echo(f"  Applied {filename}")
            total += 1

    click.echo(f"\nInitialized {total} schema files successfully.")


def _find_clickhouse_dir():
    """Walk up from CWD to find the clickhouse/ directory."""
    current = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(current, "clickhouse")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None
