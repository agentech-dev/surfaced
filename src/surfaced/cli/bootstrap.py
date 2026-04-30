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
@click.option("--skip-cli-tools", is_flag=True, help="Skip installing CLI tools (claude, codex, gemini)")
@click.option("--host", default="localhost", help="ClickHouse host")
@click.option("--port", default=8123, type=int, help="ClickHouse HTTP port")
def bootstrap(skip_cron, skip_cli_tools, host, port):
    """Set up all infrastructure for surfaced.

    \b
    Installs clickhousectl, ClickHouse, starts the server, initializes the schema,
    creates .env, and optionally installs CLI tools and cron entries.
    Idempotent — safe to run multiple times.

    \b
    What it does (in order):
      1. Install clickhousectl (ClickHouse version manager)
      2. Install ClickHouse binary via clickhousectl
      3. Start ClickHouse server if not running
      4. Run schema migrations (CREATE TABLE statements)
      5. Copy .env.example → .env if missing
      6. Install Node.js if needed, then claude/codex/gemini CLI tools
      7. Set up cron for scheduled runs

    \b
    CONTEXT FOR AGENTS:
      Run this once after installation. It is non-interactive and requires
      no input. After bootstrap completes, run 'surfaced setup' to
      configure API keys, brands, providers, and prompts interactively.
      Use --skip-cli-tools if you only want API providers (no Node.js needed).
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

    # ---------- 6. Install Node.js runtime if missing ----------
    if not skip_cli_tools:
        js_runtime = None
        for rt in ["bun", "pnpm", "npm"]:
            if _cmd_exists(rt):
                js_runtime = rt
                break

        if js_runtime:
            click.echo(f"==> Found JS runtime: {js_runtime}")
        else:
            click.echo("==> No JS runtime found, installing Node.js...")
            if _cmd_exists("brew"):
                _run("brew install node", check=False)
            elif _cmd_exists("apt-get"):
                _run("sudo apt-get update -qq && sudo apt-get install -y -qq nodejs npm", check=False)
            elif _cmd_exists("dnf"):
                _run("sudo dnf install -y nodejs npm", check=False)
            else:
                click.echo("  ✗ Could not auto-install Node.js — install manually and re-run")
                click.echo("    https://nodejs.org/en/download/")

            # Re-check
            for rt in ["bun", "pnpm", "npm"]:
                if _cmd_exists(rt):
                    js_runtime = rt
                    break

        # ---------- 7. Install CLI tools ----------
        if js_runtime:
            npm_cmd = "bun" if js_runtime == "bun" else js_runtime

            # Configure npm to install globals to ~/.local without sudo
            if npm_cmd == "npm":
                npm_prefix = os.path.join(os.path.expanduser("~"), ".local")
                _run(f"npm config set prefix {npm_prefix}", check=False, capture=True)
                # Ensure the npm global bin is on PATH for this process
                npm_bin = os.path.join(npm_prefix, "bin")
                if npm_bin not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = npm_bin + ":" + os.environ.get("PATH", "")

            install_flag = "add --global" if js_runtime == "bun" else "install -g"

            cli_tools = [
                ("claude", "@anthropic-ai/claude-code"),
                ("codex", "@openai/codex"),
                ("gemini", "@google/gemini-cli"),
            ]

            click.echo("==> Installing CLI tools...")
            for binary, package in cli_tools:
                if _cmd_exists(binary):
                    click.echo(f"  - {binary} already installed")
                else:
                    click.echo(f"  Installing {binary}...")
                    result = _run(f"{npm_cmd} {install_flag} {package}", check=False, capture=True)
                    if result.returncode == 0:
                        click.echo(f"  ✓ {binary} installed")
                    else:
                        click.echo(f"  ✗ Failed to install {binary} — install manually: {npm_cmd} {install_flag} {package}")
        else:
            click.echo("==> Skipping CLI tools (no JS runtime available)")
    else:
        click.echo("==> Skipping CLI tools (--skip-cli-tools)")

    # ---------- 8. Setup cron ----------
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
