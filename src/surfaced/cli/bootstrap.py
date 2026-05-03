"""Bootstrap command — non-interactive infrastructure setup."""

import os
import shutil
import subprocess
import time

import click


def _find_project_dir() -> str:
    """Find the surfaced project directory."""
    # Check ~/.surfaced (install.sh location)
    home = os.path.join(os.path.expanduser("~"), ".surfaced")
    if os.path.isdir(os.path.join(home, "clickhouse")):
        return home

    # Check relative to package
    pkg = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if os.path.isdir(os.path.join(pkg, "clickhouse")):
        return pkg

    # Fall back to CWD
    if os.path.isdir(os.path.join(os.getcwd(), "clickhouse")):
        return os.getcwd()

    return home  # default


def _cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _run(cmd: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, shell=True, check=check,
        capture_output=capture, text=True,
    )


def _ping_clickhouse(host: str = "localhost", port: int = 8123) -> bool:
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"http://{host}:{port}/ping", timeout=2)
        return resp.status == 200
    except Exception:
        return False


@click.command()
@click.option("--skip-cron", is_flag=True, help="Skip cron setup")
@click.option("--host", default="localhost", help="ClickHouse host")
@click.option("--port", default=8123, type=int, help="ClickHouse HTTP port")
def bootstrap(skip_cron, host, port):
    """Set up all infrastructure for surfaced.

    \b
    Installs clickhousectl, ClickHouse, starts the server, initializes the schema,
    creates .env, and optionally installs cron entries.
    Idempotent — safe to run multiple times.

    \b
    What it does (in order):
      1. Install clickhousectl (ClickHouse version manager)
      2. Install ClickHouse binary via clickhousectl
      3. Start ClickHouse server if not running
      4. Run schema migrations (CREATE TABLE statements)
      5. Copy .env.example → .env if missing
      6. Set up cron for scheduled runs

    \b
    CONTEXT FOR AGENTS:
      Run this once after installation. It is non-interactive and requires
      no input. After bootstrap completes, run 'surfaced setup' to
      configure API keys, brands, providers, and prompts interactively.
      Use --skip-cron if you don't want scheduled runs.
    """
    project_dir = _find_project_dir()

    # ---------- 1. Install clickhousectl ----------
    click.echo("==> Checking clickhousectl...")
    if _cmd_exists("clickhousectl"):
        click.echo("  - clickhousectl already installed")
    else:
        click.echo("  Installing clickhousectl...")
        _run("curl -sSL https://clickhouse.com/cli | sh")
        # Ensure PATH includes clickhousectl
        os.environ["PATH"] = os.path.join(os.path.expanduser("~"), ".local", "bin") + ":" + os.environ.get("PATH", "")
        click.echo("  ✓ clickhousectl installed")

    # ---------- 2. Install ClickHouse via clickhousectl ----------
    click.echo("==> Checking ClickHouse...")
    result = _run("clickhousectl local which", check=False, capture=True)
    if result.returncode == 0 and result.stdout.strip():
        click.echo(f"  - ClickHouse already installed ({result.stdout.strip()})")
    else:
        click.echo("  Installing ClickHouse stable...")
        _run("clickhousectl local use stable")
        click.echo("  ✓ ClickHouse installed")

    # ---------- 3. Start ClickHouse if not running ----------
    click.echo("==> Checking ClickHouse server...")
    if _ping_clickhouse(host, port):
        click.echo("  - ClickHouse already running")
    else:
        click.echo("  Starting ClickHouse...")
        subprocess.Popen(
            ["clickhousectl", "local", "server", "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for i in range(15):
            if _ping_clickhouse(host, port):
                break
            time.sleep(1)
        if _ping_clickhouse(host, port):
            click.echo("  ✓ ClickHouse started")
        else:
            click.echo("  ✗ ClickHouse failed to start after 15s", err=True)
            raise SystemExit(1)

    # ---------- 4. Run schema init ----------
    click.echo("==> Initializing schema...")
    from surfaced.cli.init import run_schema_init
    run_schema_init(host, port)

    # ---------- 5. Copy .env.example → .env ----------
    env_file = os.path.join(project_dir, ".env")
    env_example = os.path.join(project_dir, ".env.example")
    if os.path.exists(env_file):
        click.echo("==> .env already exists")
    elif os.path.exists(env_example):
        shutil.copy2(env_example, env_file)
        click.echo("==> Created .env from .env.example")
    else:
        click.echo("==> .env.example not found, skipping .env creation")

    # ---------- 6. Setup cron ----------
    if skip_cron:
        click.echo("==> Skipping cron (--skip-cron)")
    else:
        click.echo("==> Setting up cron...")
        cron_marker = "# surfaced-managed"
        result = _run("crontab -l", check=False, capture=True)
        existing_crontab = result.stdout if result.returncode == 0 else ""

        if cron_marker in existing_crontab:
            click.echo("  - Cron entries already exist")
        else:
            new_entries = f"""
{cron_marker}
0 6 * * *   cd {project_dir} && ./scripts/surfaced-runner.sh daily   {cron_marker}
0 6 * * 1   cd {project_dir} && ./scripts/surfaced-runner.sh weekly  {cron_marker}
0 6 1 * *   cd {project_dir} && ./scripts/surfaced-runner.sh monthly {cron_marker}
"""
            full_crontab = existing_crontab.rstrip() + "\n" + new_entries
            cron_result = subprocess.run(
                ["crontab", "-"],
                input=full_crontab, text=True,
                check=False, capture_output=True,
            )
            if cron_result.returncode == 0:
                click.echo("  ✓ Cron entries added (daily 6am, weekly Mon 6am, monthly 1st 6am)")
            else:
                click.echo("  ✗ Failed to set crontab — add entries manually")

    # ---------- Done ----------
    click.echo("")
    click.echo("════════════════════════════════════════════════════")
    click.echo(" Surfaced infrastructure is ready!")
    click.echo("════════════════════════════════════════════════════")
    click.echo("")
    click.echo(" Next: run 'surfaced setup' for interactive configuration")
    click.echo("")
