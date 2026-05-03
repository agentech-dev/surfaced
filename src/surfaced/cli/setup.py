"""Interactive setup wizard."""

import json
import os
import shutil

import click
import questionary

from surfaced.db.queries import QueryService
from surfaced.engine.analyzer import is_prompt_branded
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

    choices = [
        questionary.Choice(title=label, value=i)
        for i, (_, label) in enumerate(key_defs)
    ]
    selected = questionary.checkbox(
        "Which API keys do you want to configure?",
        choices=choices,
    ).ask()

    if selected is None:  # user cancelled
        return

    for idx in selected:
        env_key, label = key_defs[idx]
        current = env.get(env_key, "")
        hint = f" (current: {current[:8]}...)" if current else ""
        value = questionary.text(
            f"Enter {label} API key{hint}:",
            default=current,
        ).ask()
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
        add_another = questionary.confirm("Add another brand?", default=False).ask()
        if not add_another:
            return brands[0]

    name = questionary.text("Brand name:").ask()
    if not name:
        return brands[0] if brands else None

    domain = questionary.text("Domain (e.g. example.com):", default="").ask() or ""

    aliases = _prompt_list("Add brand aliases (enter each one, empty to finish):")
    competitors = _prompt_list("Add competitors (enter each one, empty to finish):")

    brand = Brand(
        name=name,
        domain=domain,
        aliases=aliases,
        competitors=competitors,
    )
    qs.insert_brand(brand)
    click.echo(f"  ✓ Brand '{name}' created ({brand.id})")
    return brand


def _prompt_list(label: str) -> list[str]:
    """Prompt for items one at a time until the user enters an empty value."""
    click.echo(f"  {label}")
    items = []
    while True:
        value = questionary.text(f"  [{len(items) + 1}]:", default="").ask()
        if not value:
            break
        items.append(value.strip())
    if items:
        click.echo(f"    Added: {', '.join(items)}")
    return items


# ── Step 3: Providers ─────────────────────────────────────────────────

def _step_providers():
    click.echo("\n── Step 3: Providers ────────────────────────────")

    env = _parse_env(_env_path())
    qs = QueryService()
    existing = {p.name for p in qs.get_providers()}

    # API providers based on configured keys
    api_providers = [
        ("ANTHROPIC_API_KEY", "Claude Sonnet 4.6", "anthropic", "api", "claude-sonnet-4-6"),
        ("OPENAI_API_KEY", "GPT-5.2", "openai", "api", "gpt-5.2"),
        ("GEMINI_API_KEY", "Gemini 3.1 Pro", "google", "api", "gemini-3.1-pro-preview"),
    ]

    for env_key, name, ptype, mode, model in api_providers:
        if env_key in env:
            if name in existing:
                click.echo(f"  - {name} already exists")
            else:
                provider = Provider(
                    name=name,
                    provider=ptype,
                    execution_mode=mode,
                    model=model,
                )
                qs.insert_provider(provider)
                click.echo(f"  ✓ Created provider: {name} ({model})")
        else:
            click.echo(f"  - Skipping {name} (no {env_key} in .env)")

    # CLI providers based on installed tools
    cli_providers = [
        ("claude", "Claude CLI", "anthropic", "cli", "claude-sonnet-4-6"),
        ("codex", "Codex CLI", "openai", "cli", "codex"),
        ("gemini", "Gemini CLI", "google", "cli", "gemini-3.1-pro-preview"),
    ]

    cli_found = [(binary, name, ptype, mode, model) for binary, name, ptype, mode, model in cli_providers if shutil.which(binary)]
    if cli_found:
        choices = [
            questionary.Choice(
                title=f"{name} ({binary})",
                value=(binary, name, ptype, mode, model),
                checked=True,
            )
            for binary, name, ptype, mode, model in cli_found
        ]
        selected = questionary.checkbox(
            "Detected CLI tools — which to add as providers?",
            choices=choices,
        ).ask()

        if selected:
            for binary, name, ptype, mode, model in selected:
                if name in existing:
                    click.echo(f"  - {name} already exists")
                else:
                    provider = Provider(
                        name=name,
                        provider=ptype,
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

    choice = questionary.select(
        "How would you like to add prompts?",
        choices=[
            questionary.Choice("Import starter prompts", value="starter"),
            questionary.Choice("Import from JSON file", value="file"),
            questionary.Choice("Skip", value="skip"),
        ],
    ).ask()

    if not choice or choice == "skip":
        click.echo("  Skipping prompts.")
        return

    qs = QueryService()

    if choice == "starter":
        starter_path = _find_starter_prompts()
        if not starter_path:
            click.echo("  ✗ Could not find prompts_import.json")
            return
        _import_prompts_file(qs, starter_path, brand)

    elif choice == "file":
        path = questionary.path("Path to JSON file:").ask()
        if not path:
            return
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
            branded=item["branded"] if "branded" in item else is_prompt_branded(item["text"], brand),
            tags=item.get("tags", []),
        )
        qs.insert_prompt(prompt)
        count += 1

    click.echo(f"  ✓ Imported {count} prompts for brand '{brand.name}'")


# ── Main command ──────────────────────────────────────────────────────

@click.command()
@click.option("--step", type=click.Choice(["keys", "brand", "providers", "prompts"]), default=None, help="Run a single step")
def setup(step):
    """Interactive setup wizard.

    \b
    Walks through 4 steps:
      Step 1 (keys)      — Configure API keys (written to ~/.surfaced/.env)
      Step 2 (brand)     — Create a brand to track (name, aliases, competitors)
      Step 3 (providers) — Auto-create providers from detected keys and CLI tools
      Step 4 (prompts)   — Import starter prompts or load from a JSON file

    \b
    Use --step to run a single step, e.g.:
      surfaced setup --step keys
      surfaced setup --step providers

    \b
    CONTEXT FOR AGENTS:
      This command is interactive and requires terminal input. If you are
      automating setup, use the individual non-interactive commands instead:
        - Write API keys directly to ~/.surfaced/.env
        - surfaced brands add --name "X" --aliases "A,B" --competitors "C,D"
        - surfaced providers add --provider anthropic --mode api
        - surfaced prompts import prompts_import.json
      After setup, run 'surfaced run --brand <name>' to execute prompts.
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
    click.echo(" Run your first prompts:")
    click.echo("   surfaced run --brand <YourBrand>")
    click.echo("")
    click.echo(" View results:")
    click.echo("   surfaced analytics summary --brand <YourBrand> --days 30")
    click.echo("")
