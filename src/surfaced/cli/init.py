"""Database initialization command."""

import glob
import os

import click

from surfaced.db.client import DBClient


def run_schema_init(
    host: str | None = None,
    port: int | None = None,
    username: str | None = None,
    password: str | None = None,
    database: str | None = None,
    secure: bool | None = None,
) -> int:
    """Initialize the ClickHouse schema. Returns count of applied files.

    Callable from both the `init` CLI command and `bootstrap`. Any parameter
    left as None falls back to its CLICKHOUSE_* environment variable.
    """
    db = DBClient(
        host=host,
        port=port,
        username=username,
        password=password,
        database=database,
        secure=secure,
    )

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
                db.execute_no_result(statement)

            click.echo(f"  Applied {filename}")
            total += 1

    click.echo(f"\nInitialized {total} schema files successfully.")
    return total


@click.command()
@click.option("--host", default=None, help="ClickHouse host (env: CLICKHOUSE_HOST)")
@click.option("--port", default=None, type=int, help="ClickHouse port (env: CLICKHOUSE_PORT)")
@click.option("--username", default=None, help="ClickHouse user (env: CLICKHOUSE_USER)")
@click.option("--password", default=None, help="ClickHouse password (env: CLICKHOUSE_PASSWORD)")
@click.option("--database", default=None, help="ClickHouse database (env: CLICKHOUSE_DATABASE)")
@click.option("--secure/--no-secure", default=None, help="Use HTTPS/TLS (env: CLICKHOUSE_SECURE). Required for ClickHouse Cloud.")
def init(host, port, username, password, database, secure):
    """Initialize the ClickHouse database schema.

    \b
    Runs all table and materialized view SQL files in order.
    Connects to a running ClickHouse server (local or ClickHouse Cloud).
    Safe to run multiple times — uses CREATE TABLE IF NOT EXISTS.

    \b
    Connection settings are read from CLICKHOUSE_* environment variables
    unless overridden via flags. For ClickHouse Cloud, set:
      CLICKHOUSE_HOST=<your-host>.clickhouse.cloud
      CLICKHOUSE_USER=default
      CLICKHOUSE_PASSWORD=<password>
      CLICKHOUSE_SECURE=true

    \b
    CONTEXT FOR AGENTS:
      For local-only setups, 'surfaced bootstrap' runs this automatically.
      For ClickHouse Cloud or any remote server, run this directly after
      populating .env. Tables are stored in clickhouse/tables/ and
      materialized views in clickhouse/materialized_views/.
    """
    run_schema_init(
        host=host,
        port=port,
        username=username,
        password=password,
        database=database,
        secure=secure,
    )


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
