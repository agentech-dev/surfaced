"""Interactive setup wizard."""

import json
import os
import shutil

import click

from surfaced.db.queries import QueryService
from surfaced.models.brand import Brand
from surfaced.models.prompt import Prompt
from surfaced.models.provider import Provider


def _find_project_dir() -> str:
    """Find the surfaced project directory."""
    home = os.path.join(os.path.expanduser("~"), ".surfaced")
    if os.path.isdir(os.path.join(home, "clickhouse")):
        return home
    pkg = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if os.path.isdir(os.path.join(pkg, "clickhouse")):
        return pkg
    if os.path.isdir(os.path.join(os.getcwd(), "clickhouse")):
        return os.getcwd()
    return home


def _env_path() -> str:
    return os.path.join(_find_project_dir(), ".env")


def _numbered_select(label: str, options: list[str], allow_multiple: bool = False) -> list[int]:
    """Display a numbered menu and return selected indices (0-based)."""
    click.echo(f"\n{label}")
    for i, opt in enumerate(options, 1):
        click.echo(f"  [{i}] {opt}")

    if allow_multiple:
        raw = click.prompt("Enter numbers separated by commas (e.g. 1,2)", type=str)
        try:
            return [int(x.strip()) - 1 for x in raw.split(",") if x.strip()]
        except ValueError:
            click.echo("Invalid input, skipping.")
            return []
    else:
        raw = click.prompt("Enter number", type=int)
        return [raw - 1]


def _parse_env(path: str) -> dict[str, str]:
    """Parse a .env file into a dict. Only includes keys with non-empty values."""
    result = {}
    if not os.path.exists(path):
        return result
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if value:
                    result[key] = value
    return result


def _write_env_key(path: str, key: str, value: str) -> None:
    """Set a key in a .env file, updating in place or appending."""
    lines = []
    found = False

    if os.path.exists(path):
        with open(path) as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}\n")
            found = True
        elif stripped == key or stripped == f"# {key}=":
            # Replace commented-out or bare key
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(path, "w") as f:
        f.writelines(new_lines)


# ── Step 1: API Keys ──────────────────────────────────────────────────

def _step_keys():
    click.echo("\n── Step 1: API Keys ─────────────────────────────")

    env_path = _env_path()
    env = _parse_env(env_path)

    key_defs = [
        ("ANTHROPIC_API_KEY", "Anthropic"),
        ("OPENAI_API_KEY", "OpenAI"),
        ("GEMINI_API_KEY", "Google Gemini"),
    ]

    # Show current status
    for env_key, label in key_defs:
        status = "set" if env_key in env else "not set"
        click.echo(f"  {label}: {status}")

    options = [label for _, label in key_defs]
    selected = _numbered_select("Which API keys do you want to configure?", options, allow_multiple=True)

    for idx in selected:
        if 0 <= idx < len(key_defs):
            env_key, label = key_defs[idx]
            current = env.get(env_key, "")
            hint = f" (current: {current[:8]}...)" if current else ""
            value = click.prompt(f"  Enter {label} API key{hint}", default=current, show_default=False)
            if value:
                _write_env_key(env_path, env_key, value)
                click.echo(f"  ✓ {label} key saved")

    click.echo("  Done with API keys.")


# ── Step 2: Brand ─────────────────────────────────────────────────────

def _step_brand() -> Brand | None:
    click.echo("\n── Step 2: Brand ────────────────────────────────")

    qs = QueryService()
    brands = qs.get_brands()

    if brands:
        click.echo(f"  Found {len(brands)} existing brand(s):")
        for b in brands:
            click.echo(f"    - {b.name} ({b.id})")
        if not click.confirm("  Add another brand?", default=False):
            return brands[0]

    name = click.prompt("  Brand name")
    domain = click.prompt("  Domain (e.g. example.com)", default="")
    aliases_raw = click.prompt("  Aliases (comma-separated)", default="")
    competitors_raw = click.prompt("  Competitors (comma-separated)", default="")

    brand = Brand(
        name=name,
        domain=domain,
        aliases=[a.strip() for a in aliases_raw.split(",") if a.strip()] if aliases_raw else [],
        competitors=[c.strip() for c in competitors_raw.split(",") if c.strip()] if competitors_raw else [],
    )
    qs.insert_brand(brand)
    click.echo(f"  ✓ Brand '{name}' created ({brand.id})")
    return brand


# ── Step 3: Providers ─────────────────────────────────────────────────

def _step_providers():
    click.echo("\n── Step 3: Providers ────────────────────────────")

    env = _parse_env(_env_path())
    qs = QueryService()
    existing = {p.name for p in qs.get_providers()}

    # API providers based on configured keys
    api_providers = [
        ("ANTHROPIC_API_KEY", "Claude Sonnet", "anthropic_api", "api", "claude-sonnet-4-20250514"),
        ("OPENAI_API_KEY", "GPT-4o", "openai_api", "api", "gpt-4o"),
        ("GEMINI_API_KEY", "Gemini Flash", "gemini_api", "api", "gemini-2.5-flash"),
    ]

    for env_key, name, ptype, mode, model in api_providers:
        if env_key in env:
            if name in existing:
                click.echo(f"  - {name} already exists")
            else:
                provider = Provider(
                    name=name,
                    provider_type=ptype,
                    execution_mode=mode,
                    model=model,
                )
                qs.insert_provider(provider)
                click.echo(f"  ✓ Created provider: {name} ({model})")
        else:
            click.echo(f"  - Skipping {name} (no {env_key} in .env)")

    # CLI providers based on installed tools
    cli_providers = [
        ("claude", "Claude CLI", "claude_cli", "cli", "claude-sonnet-4-20250514"),
        ("codex", "Codex CLI", "openai_cli", "cli", "codex"),
        ("gemini", "Gemini CLI", "gemini_cli", "cli", "gemini-2.5-flash"),
    ]

    cli_found = [(binary, name, ptype, mode, model) for binary, name, ptype, mode, model in cli_providers if shutil.which(binary)]
    if cli_found:
        options = [f"{name} ({binary})" for binary, name, _, _, _ in cli_found]
        click.echo(f"\n  Detected {len(cli_found)} CLI tool(s):")
        if click.confirm("  Add CLI tools as providers?", default=True):
            for binary, name, ptype, mode, model in cli_found:
                if name in existing:
                    click.echo(f"  - {name} already exists")
                else:
                    provider = Provider(
                        name=name,
                        provider_type=ptype,
                        execution_mode=mode,
                        model=model,
                    )
                    qs.insert_provider(provider)
                    click.echo(f"  ✓ Created provider: {name} ({binary})")

    click.echo("  Done with providers.")


# ── Step 4: Prompts ───────────────────────────────────────────────────

def _step_prompts(brand: Brand | None):
    click.echo("\n── Step 4: Prompts ──────────────────────────────")

    if not brand:
        click.echo("  No brand configured — skipping prompts.")
        return

    selected = _numbered_select(
        "How would you like to add prompts?",
        ["Import starter prompts", "Import from JSON file", "Skip"],
    )

    if not selected or selected[0] == 2:
        click.echo("  Skipping prompts.")
        return

    qs = QueryService()

    if selected[0] == 0:
        # Load starter prompts from project
        starter_path = _find_starter_prompts()
        if not starter_path:
            click.echo("  ✗ Could not find prompts_import.json")
            return
        _import_prompts_file(qs, starter_path, brand)

    elif selected[0] == 1:
        path = click.prompt("  Path to JSON file")
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            click.echo(f"  ✗ File not found: {path}")
            return
        _import_prompts_file(qs, path, brand)


def _find_starter_prompts() -> str | None:
    """Find the prompts_import.json file."""
    candidates = [
        os.path.join(_find_project_dir(), "prompts_import.json"),
        os.path.join(os.path.expanduser("~"), ".surfaced", "prompts_import.json"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _import_prompts_file(qs: QueryService, path: str, brand: Brand) -> None:
    """Import prompts from a JSON file, overriding brand_id."""
    with open(path) as f:
        data = json.load(f)

    count = 0
    for item in data:
        prompt = Prompt(
            text=item["text"],
            category=item["category"],
            brand_id=brand.id,
            tags=item.get("tags", []),
        )
        qs.insert_prompt(prompt)
        count += 1

    click.echo(f"  ✓ Imported {count} prompts for brand '{brand.name}'")


# ── Main command ──────────────────────────────────────────────────────

STEPS = {
    "keys": _step_keys,
    "brand": _step_brand,
    "providers": _step_providers,
    "prompts": None,  # handled specially because it needs brand
}


@click.command()
@click.option("--step", type=click.Choice(["keys", "brand", "providers", "prompts"]), default=None, help="Run a single step")
def setup(step):
    """Interactive setup wizard.

    Walks through 4 steps: API keys, brand, providers, and prompts.
    Use --step to run a single step.
    """
    click.echo("════════════════════════════════════════════════════")
    click.echo(" Surfaced Setup Wizard")
    click.echo("════════════════════════════════════════════════════")

    brand = None

    if step:
        if step == "keys":
            _step_keys()
        elif step == "brand":
            _step_brand()
        elif step == "providers":
            _step_providers()
        elif step == "prompts":
            # Need to find existing brand
            qs = QueryService()
            brands = qs.get_brands()
            if brands:
                brand = brands[0]
            _step_prompts(brand)
    else:
        _step_keys()
        brand = _step_brand()
        _step_providers()
        _step_prompts(brand)

    click.echo("\n════════════════════════════════════════════════════")
    click.echo(" Setup complete!")
    click.echo("════════════════════════════════════════════════════")
    click.echo("")
    click.echo(" Run your first campaign:")
    click.echo("   surfaced run --brand <YourBrand>")
    click.echo("")
    click.echo(" View results:")
    click.echo("   surfaced analytics summary --brand <YourBrand> --days 30")
    click.echo("")
