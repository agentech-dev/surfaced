"""Database initialization command."""

import glob
import os

import click


def run_schema_init(host: str = "localhost", port: int = 8123) -> int:
    """Initialize the ClickHouse schema. Returns count of applied files.

    Callable from both the `init` CLI command and `bootstrap`.
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
    return total


@click.command()
@click.option("--host", default="localhost", help="ClickHouse host")
@click.option("--port", default=8123, type=int, help="ClickHouse HTTP port")
def init(host, port):
    """Initialize the ClickHouse database schema.

    \b
    Runs all table and materialized view SQL files in order.
    Requires a running ClickHouse server (clickhousectl local server start).
    Safe to run multiple times — uses CREATE TABLE IF NOT EXISTS.

    \b
    CONTEXT FOR AGENTS:
      You usually don't need to call this directly — 'surfaced bootstrap'
      runs it automatically. Use this only if you need to re-apply schema
      on an already-running ClickHouse instance. Tables are stored in
      clickhouse/tables/ and materialized views in clickhouse/materialized_views/.
    """
    run_schema_init(host, port)


def _find_clickhouse_dir():
    """Walk up from CWD to find the clickhouse/ directory."""
    # First check relative to the package installation (works after uv tool install)
    package_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    candidate = os.path.join(package_dir, "clickhouse")
    if os.path.isdir(candidate):
        return candidate

    # Also check ~/.surfaced/ (where install.sh clones the repo)
    home_candidate = os.path.join(os.path.expanduser("~"), ".surfaced", "clickhouse")
    if os.path.isdir(home_candidate):
        return home_candidate

    # Fall back to walking up from CWD
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
