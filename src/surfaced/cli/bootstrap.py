"""Bootstrap command — non-interactive infrastructure setup."""

import json
import os
import secrets
import shutil
import string
import subprocess
import time

import click

APP_USER = "surfaced"

# Special characters that are safe inside a single-quoted SQL literal
# (no single quote, no backslash) and accepted by ClickHouse Cloud's
# password policy.
_PASSWORD_SPECIALS = "!@#$%^&*+=?"


def _generate_password() -> str:
    """Generate a strong password that satisfies ClickHouse Cloud's policy.

    Cloud requires at least one uppercase, lowercase, digit and special
    character. `secrets.token_urlsafe` only emits [A-Za-z0-9_-], so we
    append one guaranteed character of each class.
    """
    base = secrets.token_urlsafe(24)
    suffix = (
        secrets.choice(string.ascii_uppercase)
        + secrets.choice(string.ascii_lowercase)
        + secrets.choice(string.digits)
        + secrets.choice(_PASSWORD_SPECIALS)
    )
    return base + suffix


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


def _ping_local_clickhouse(host: str = "localhost", port: int = 8123) -> bool:
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"http://{host}:{port}/ping", timeout=2)
        return resp.status == 200
    except Exception:
        return False


def _ensure_clickhousectl() -> None:
    click.echo("==> Checking clickhousectl...")
    if _cmd_exists("clickhousectl"):
        click.echo("  - clickhousectl already installed")
        return
    click.echo("  Installing clickhousectl...")
    _run("curl -sSL https://clickhouse.com/cli | sh")
    os.environ["PATH"] = os.path.join(os.path.expanduser("~"), ".local", "bin") + ":" + os.environ.get("PATH", "")
    click.echo("  ✓ clickhousectl installed")


def _ensure_env_file(project_dir: str) -> str:
    """Ensure .env exists (copy from .env.example if missing). Returns the path."""
    env_file = os.path.join(project_dir, ".env")
    env_example = os.path.join(project_dir, ".env.example")
    if os.path.exists(env_file):
        click.echo("==> .env already exists")
    elif os.path.exists(env_example):
        shutil.copy2(env_example, env_file)
        click.echo("==> Created .env from .env.example")
    else:
        click.echo("==> .env.example not found, skipping .env creation")
    return env_file


def _write_env_key(path: str, key: str, value: str) -> None:
    """Set a key in a .env file, updating in place or appending."""
    lines: list[str] = []
    found = False
    if os.path.exists(path):
        with open(path) as f:
            lines = f.readlines()

    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}\n")
            found = True
        elif stripped == f"# {key}=" or stripped.startswith(f"# {key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(path, "w") as f:
        f.writelines(new_lines)


def _setup_cron(project_dir: str) -> None:
    click.echo("==> Setting up cron...")
    cron_marker = "# surfaced-managed"
    result = _run("crontab -l", check=False, capture=True)
    existing_crontab = result.stdout if result.returncode == 0 else ""

    if cron_marker in existing_crontab:
        click.echo("  - Cron entries already exist")
        return

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


# ── App user provisioning ────────────────────────────────────────────────

def _provision_app_user(
    env_file: str,
    admin_host: str,
    admin_port: int,
    admin_user: str,
    admin_password: str,
    admin_secure: bool,
    database: str = "default",
) -> None:
    """Ensure the `surfaced` user exists with GRANT ALL on `database`.

    Persists user + generated password to .env and os.environ so that
    schema init and the application run as `surfaced`, not as the admin.
    Idempotent: if `surfaced` already exists, re-applies GRANT and keeps
    whatever password is already in .env.
    """
    from surfaced.db.client import DBClient

    click.echo(f"==> Provisioning '{APP_USER}' user...")

    admin = DBClient(
        host=admin_host,
        port=admin_port,
        username=admin_user,
        password=admin_password,
        database=database,
        secure=admin_secure,
    )

    try:
        rows = admin.execute(
            "SELECT name FROM system.users WHERE name = %(n)s",
            parameters={"n": APP_USER},
        )
    except Exception as exc:
        click.echo(f"  ✗ Failed to connect as admin user '{admin_user}': {exc}", err=True)
        raise SystemExit(1)

    if rows:
        # User exists — re-apply grants idempotently to bring older installs up to date.
        _apply_app_user_grants(admin, database)
        click.echo(f"  - User '{APP_USER}' already exists; grants re-applied")
        if not (os.environ.get("CLICKHOUSE_USER") == APP_USER and os.environ.get("CLICKHOUSE_PASSWORD")):
            click.echo(
                f"  ! User '{APP_USER}' exists on the server but no matching credentials in .env.",
                err=True,
            )
            click.echo(
                f"    Either populate CLICKHOUSE_USER={APP_USER} and CLICKHOUSE_PASSWORD in .env,"
                f" or DROP USER {APP_USER} on the server and rerun.",
                err=True,
            )
            raise SystemExit(1)
        return

    password = _generate_password()
    admin.execute_no_result(f"CREATE USER {APP_USER} IDENTIFIED BY '{password}'")
    _apply_app_user_grants(admin, database)
    click.echo(f"  ✓ Created user '{APP_USER}' with all privileges on '{database}'")

    _write_env_key(env_file, "CLICKHOUSE_USER", APP_USER)
    _write_env_key(env_file, "CLICKHOUSE_PASSWORD", password)
    os.environ["CLICKHOUSE_USER"] = APP_USER
    os.environ["CLICKHOUSE_PASSWORD"] = password


def _apply_app_user_grants(admin, database: str) -> None:
    """Apply the privileges the surfaced user needs. Idempotent."""
    # Database-scoped privileges (SELECT, INSERT, ALTER, CREATE TABLE, etc.)
    admin.execute_no_result(f"GRANT ALL ON {database}.* TO {APP_USER}")
    # Global TABLE ENGINE privilege — not implied by GRANT ALL ON db.*.
    # `ON *` covers every engine (MergeTree, ReplacingMergeTree, SummingMergeTree, ...).
    admin.execute_no_result(f"GRANT TABLE ENGINE ON * TO {APP_USER}")


# ── Local bootstrap ──────────────────────────────────────────────────────

def _bootstrap_local(host: str, port: int, env_file: str) -> None:
    # Install ClickHouse via clickhousectl
    click.echo("==> Checking ClickHouse...")
    result = _run("clickhousectl local which", check=False, capture=True)
    if result.returncode == 0 and result.stdout.strip():
        click.echo(f"  - ClickHouse already installed ({result.stdout.strip()})")
    else:
        click.echo("  Installing ClickHouse stable...")
        _run("clickhousectl local use stable")
        click.echo("  ✓ ClickHouse installed")

    # Start ClickHouse if not running
    click.echo("==> Checking ClickHouse server...")
    if _ping_local_clickhouse(host, port):
        click.echo("  - ClickHouse already running")
    else:
        click.echo("  Starting ClickHouse...")
        subprocess.Popen(
            ["clickhousectl", "local", "server", "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(15):
            if _ping_local_clickhouse(host, port):
                break
            time.sleep(1)
        if _ping_local_clickhouse(host, port):
            click.echo("  ✓ ClickHouse started")
        else:
            click.echo("  ✗ ClickHouse failed to start after 15s", err=True)
            raise SystemExit(1)

    # Provision the surfaced user using local default (no password) as admin
    _provision_app_user(
        env_file=env_file,
        admin_host=host,
        admin_port=port,
        admin_user="default",
        admin_password="",
        admin_secure=False,
    )


# ── Cloud bootstrap ──────────────────────────────────────────────────────

def _cloud_env(name: str, default: str = "") -> str:
    """Return the env var value if set and non-empty, else default."""
    value = os.environ.get(name, "").strip()
    return value or default


def _bootstrap_cloud(env_file: str) -> None:
    api_key = _cloud_env("CLICKHOUSE_CLOUD_API_KEY")
    api_secret = _cloud_env("CLICKHOUSE_CLOUD_API_SECRET")
    if not api_key or not api_secret:
        click.echo(
            "  ✗ CLICKHOUSE_CLOUD_API_KEY and CLICKHOUSE_CLOUD_API_SECRET are required.",
            err=True,
        )
        click.echo(
            f"    Create an Admin API key at https://console.clickhouse.cloud and set them in {env_file}, then rerun.",
            err=True,
        )
        raise SystemExit(1)

    service_name = _cloud_env("CLICKHOUSE_CLOUD_SERVICE_NAME", default="surfaced")
    provider = _cloud_env("CLICKHOUSE_CLOUD_PROVIDER", default="aws")
    region = _cloud_env("CLICKHOUSE_CLOUD_REGION", default="us-east-1")
    org_id = _cloud_env("CLICKHOUSE_CLOUD_ORG_ID")

    # Export canonical names so child clickhousectl invocations pick them up.
    os.environ["CLICKHOUSE_CLOUD_API_KEY"] = api_key
    os.environ["CLICKHOUSE_CLOUD_API_SECRET"] = api_secret

    # Non-interactive login persists creds to clickhousectl's config so subsequent
    # commands work even without env vars, and it actually validates the key/secret
    # (unlike `auth status`, which exits 0 even when no creds are configured).
    click.echo("==> Authenticating clickhousectl against ClickHouse Cloud...")
    login = _run(
        f"clickhousectl cloud auth login --api-key {shell_quote(api_key)} "
        f"--api-secret {shell_quote(api_secret)} --json",
        check=False,
        capture=True,
    )
    if login.returncode != 0:
        click.echo("  ✗ clickhousectl could not authenticate against ClickHouse Cloud.", err=True)
        click.echo(f"    {login.stderr.strip() or login.stdout.strip()}", err=True)
        raise SystemExit(1)
    click.echo("  ✓ Authenticated")

    # Locate or create the service
    click.echo(f"==> Resolving cloud service '{service_name}'...")
    list_cmd = "clickhousectl cloud service list --json"
    if org_id:
        list_cmd += f" --org-id {shell_quote(org_id)}"
    listed = _run(list_cmd, check=False, capture=True)
    if listed.returncode != 0:
        click.echo(f"  ✗ Failed to list services: {listed.stderr.strip()}", err=True)
        raise SystemExit(1)

    existing = None
    try:
        services = json.loads(listed.stdout or "[]")
        for svc in services:
            if svc.get("name") == service_name:
                existing = svc
                break
    except json.JSONDecodeError:
        click.echo("  ✗ Could not parse service list output.", err=True)
        raise SystemExit(1)

    service_id: str
    admin_password: str
    if existing:
        service_id = existing["id"]
        click.echo(f"  - Found existing service: {service_name} ({service_id})")
        host, port = _endpoint_from_service(existing)
        if not host:
            # Endpoints may not be populated until the service is running; fetch fresh
            host, port = _wait_for_endpoint(service_id, org_id=org_id)
        # Reuse: we don't have the default user password. The provisioning step
        # will short-circuit if .env already has the surfaced user credentials.
        if os.environ.get("CLICKHOUSE_USER") != APP_USER or not os.environ.get("CLICKHOUSE_PASSWORD"):
            click.echo(
                f"  ! Reusing existing service but no '{APP_USER}' credentials in .env.",
                err=True,
            )
            click.echo(
                "    Reset the default password and rerun to re-provision: "
                f"clickhousectl cloud service reset-password {service_id}",
                err=True,
            )
            raise SystemExit(1)
        admin_password = ""  # not used — provision will short-circuit
    else:
        click.echo(f"  Creating service '{service_name}' ({provider} / {region})...")
        create_cmd = (
            f"clickhousectl cloud service create --json "
            f"--name {shell_quote(service_name)} "
            f"--provider {shell_quote(provider)} "
            f"--region {shell_quote(region)}"
        )
        if org_id:
            create_cmd += f" --org-id {shell_quote(org_id)}"
        created = _run(create_cmd, check=False, capture=True)
        if created.returncode != 0:
            click.echo(f"  ✗ Service create failed: {created.stderr.strip() or created.stdout.strip()}", err=True)
            raise SystemExit(1)
        try:
            payload = json.loads(created.stdout)
        except json.JSONDecodeError:
            click.echo("  ✗ Could not parse service create response.", err=True)
            raise SystemExit(1)
        svc = payload.get("service", {})
        admin_password = payload.get("password", "")
        service_id = svc.get("id", "")
        host, port = _endpoint_from_service(svc)
        if not host:
            host, port = _wait_for_endpoint(service_id, org_id=org_id)
        click.echo(f"  ✓ Service created ({service_id})")

    # Persist host/port/secure to .env (user + password are written by provisioning)
    _write_env_key(env_file, "CLICKHOUSE_HOST", host)
    _write_env_key(env_file, "CLICKHOUSE_PORT", str(port))
    _write_env_key(env_file, "CLICKHOUSE_SECURE", "true")
    os.environ["CLICKHOUSE_HOST"] = host
    os.environ["CLICKHOUSE_PORT"] = str(port)
    os.environ["CLICKHOUSE_SECURE"] = "true"

    # Wait until service state is running
    click.echo("==> Waiting for service to be running...")
    if not _wait_for_state(service_id, "running", org_id=org_id, timeout_s=300):
        click.echo("  ✗ Service did not reach 'running' state within 5 minutes.", err=True)
        raise SystemExit(1)
    click.echo("  ✓ Service running")

    # Provision the surfaced user using default's freshly-issued password
    _provision_app_user(
        env_file=env_file,
        admin_host=host,
        admin_port=port,
        admin_user="default",
        admin_password=admin_password,
        admin_secure=True,
    )


def shell_quote(s: str) -> str:
    """Quote a string for safe inclusion in a shell command."""
    import shlex
    return shlex.quote(s)


def _endpoint_from_service(svc: dict) -> tuple[str, int]:
    """Extract the HTTPS endpoint from a service JSON object."""
    endpoints = svc.get("endpoints") or []
    https = next((e for e in endpoints if str(e.get("protocol", "")).lower() == "https"), None)
    endpoint = https or (endpoints[0] if endpoints else None)
    if not endpoint:
        return ("", 0)
    host = endpoint.get("host", "")
    port_raw = endpoint.get("port", 0)
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = 8443
    return (host, port)


def _service_get_cmd(service_id: str, org_id: str = "") -> str:
    cmd = f"clickhousectl cloud service get --json {shell_quote(service_id)}"
    if org_id:
        cmd += f" --org-id {shell_quote(org_id)}"
    return cmd


def _wait_for_endpoint(service_id: str, org_id: str = "", timeout_s: int = 300) -> tuple[str, int]:
    """Poll `cloud service get` until an endpoint is populated."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        result = _run(_service_get_cmd(service_id, org_id), check=False, capture=True)
        if result.returncode == 0:
            try:
                svc = json.loads(result.stdout)
            except json.JSONDecodeError:
                svc = {}
            host, port = _endpoint_from_service(svc)
            if host:
                return (host, port)
        time.sleep(5)
    return ("", 0)


def _wait_for_state(service_id: str, target: str, org_id: str = "", timeout_s: int = 300) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        result = _run(_service_get_cmd(service_id, org_id), check=False, capture=True)
        if result.returncode == 0:
            try:
                svc = json.loads(result.stdout)
            except json.JSONDecodeError:
                svc = {}
            if str(svc.get("state", "")).lower() == target:
                return True
        time.sleep(5)
    return False


# ── Command ──────────────────────────────────────────────────────────────

@click.command()
@click.option("--cloud", is_flag=True, help="Provision a ClickHouse Cloud service via clickhousectl instead of a local server.")
@click.option("--skip-cron", is_flag=True, help="Skip cron setup")
@click.option("--host", default="localhost", help="ClickHouse host (local mode only)")
@click.option("--port", default=8123, type=int, help="ClickHouse HTTP port (local mode only)")
def bootstrap(cloud, skip_cron, host, port):
    """Set up all infrastructure for surfaced.

    \b
    Local (default): installs clickhousectl, ClickHouse, starts the server,
    creates a dedicated `surfaced` database user, initializes the schema,
    creates .env, and optionally installs cron.

    \b
    Cloud (--cloud): installs clickhousectl, provisions a ClickHouse Cloud
    service (or reuses an existing one), creates a dedicated `surfaced`
    user, writes connection details to .env, initializes the schema, and
    installs cron.

    \b
    Idempotent — safe to run multiple times. The `surfaced` user is
    created with GRANT ALL on the database the first time only;
    subsequent runs reuse the credentials persisted in .env.

    \b
    Cloud mode reads these env vars (set in .env before running):
      CLICKHOUSE_CLOUD_API_KEY          Admin API key (from console; required)
      CLICKHOUSE_CLOUD_API_SECRET       Admin API secret (required)
      CLICKHOUSE_CLOUD_ORG_ID           Organization ID (auto-detected if unset)
      CLICKHOUSE_CLOUD_SERVICE_NAME     Service name (default: surfaced)
      CLICKHOUSE_CLOUD_PROVIDER         aws | gcp | azure (default: aws)
      CLICKHOUSE_CLOUD_REGION           Cloud region (default: us-east-1)

    \b
    CONTEXT FOR AGENTS:
      Run this once after installation. Non-interactive. After bootstrap,
      run 'surfaced setup' for API keys, brands, providers, and prompts.
      Use --cloud to host the database on ClickHouse Cloud; otherwise it
      runs ClickHouse locally via clickhousectl.
    """
    project_dir = _find_project_dir()

    # Step 1: install clickhousectl (common)
    _ensure_clickhousectl()

    # Step 2: ensure .env exists before cloud bootstrap (which writes to it)
    env_file = _ensure_env_file(project_dir)

    # Step 3: provision database + the surfaced app user
    if cloud:
        _bootstrap_cloud(env_file)
    else:
        _bootstrap_local(host, port, env_file)

    # Step 4: schema init runs as the surfaced user provisioned above (read from env)
    click.echo("==> Initializing schema...")
    from surfaced.cli.init import run_schema_init
    run_schema_init()

    # Step 5: cron
    if skip_cron:
        click.echo("==> Skipping cron (--skip-cron)")
    else:
        _setup_cron(project_dir)

    # Done
    click.echo("")
    click.echo("════════════════════════════════════════════════════")
    click.echo(" Surfaced infrastructure is ready!")
    click.echo("════════════════════════════════════════════════════")
    click.echo("")
    click.echo(" Next: run 'surfaced setup' for interactive configuration")
    click.echo("")
