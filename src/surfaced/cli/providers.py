"""Provider management CLI commands."""

import json
from uuid import UUID

import click

from surfaced.db.queries import QueryService
from surfaced.models.provider import Provider

VALID_PROVIDERS = ["anthropic", "openai", "google"]

VALID_MODES = ["api", "cli"]

# Provider presets: (provider, mode) → (default_name, default_model, env_var/binary, description)
PROVIDER_PRESETS = {
    ("anthropic", "api"): ("Claude Sonnet 4.6", "claude-sonnet-4-6", "ANTHROPIC_API_KEY", "Anthropic API (requires ANTHROPIC_API_KEY)"),
    ("openai", "api"):    ("GPT-5.2",           "gpt-5.2",          "OPENAI_API_KEY",    "OpenAI API (requires OPENAI_API_KEY)"),
    ("google", "api"):    ("Gemini 3.1 Pro",    "gemini-3.1-pro-preview", "GEMINI_API_KEY", "Google Gemini API (requires GEMINI_API_KEY)"),
    ("anthropic", "cli"): ("Claude CLI",         "claude-sonnet-4-6", "claude",            "Claude Code CLI subprocess"),
    ("openai", "cli"):    ("Codex CLI",          "codex",            "codex",              "OpenAI Codex CLI subprocess"),
    ("google", "cli"):    ("Gemini CLI",         "gemini-3.1-pro-preview", "gemini",       "Google Gemini CLI subprocess"),
}


def _qs():
    return QueryService()


def _format_provider(provider: Provider, fmt: str) -> str:
    if fmt == "json":
        return json.dumps({
            "id": str(provider.id),
            "name": provider.name,
            "provider": provider.provider,
            "execution_mode": provider.execution_mode,
            "model": provider.model,
            "config": provider.config,
            "rate_limit_rpm": provider.rate_limit_rpm,
            "is_active": provider.is_active,
            "created_at": provider.created_at.isoformat(),
            "updated_at": provider.updated_at.isoformat(),
        })
    lines = [
        f"ID:       {provider.id}",
        f"Name:     {provider.name}",
        f"Provider: {provider.provider}",
        f"Mode:     {provider.execution_mode}",
        f"Model:    {provider.model}",
        f"RPM:      {provider.rate_limit_rpm}",
        f"Active:   {'yes' if provider.is_active else 'no'}",
        f"Created:  {provider.created_at}",
    ]
    return "\n".join(lines)


def _build_provider_help() -> str:
    lines = ["Provider vendor. Available combinations:\n"]
    for (prov, mode), (name, model, req, desc) in PROVIDER_PRESETS.items():
        lines.append(f"  {prov:12s} + {mode:3s} → model={model} — {desc}")
    return "\n".join(lines)


@click.group()
def providers():
    """Manage AI providers.

    \b
    Available provider + mode combinations:
      anthropic + api   model=claude-sonnet-4-6       Anthropic API (requires ANTHROPIC_API_KEY)
      openai    + api   model=gpt-5.2                 OpenAI API (requires OPENAI_API_KEY)
      google    + api   model=gemini-3.1-pro-preview  Google Gemini API (requires GEMINI_API_KEY)
      anthropic + cli   model=claude-sonnet-4-6       Claude Code CLI subprocess
      openai    + cli   model=codex                   OpenAI Codex CLI subprocess
      google    + cli   model=gemini-3.1-pro-preview  Google Gemini CLI subprocess

    \b
    Examples:
      surfaced providers add --provider anthropic --mode api
      surfaced providers add --provider openai --mode cli --model codex
      surfaced providers add --interactive
      surfaced providers list

    \b
    CONTEXT FOR AGENTS:
      Providers define which AI models to query during runs. API providers
      need the corresponding API key in ~/.surfaced/.env. CLI providers need
      the binary installed (e.g. 'claude', 'codex', 'gemini').
      You need at least one provider before running prompts.
      Use 'surfaced providers add --provider <vendor> --mode <mode>' — defaults
      are filled in automatically. Only --provider and --mode are required.
      Use 'surfaced providers list' to verify what is configured.
      After adding providers, run prompts with 'surfaced run --brand <name>'.
    """
    pass


@providers.command()
@click.option("--interactive", "-i", is_flag=True, help="Interactive guided setup")
@click.option("--name", default=None, help="Provider display name (auto-set from preset if omitted)")
@click.option("--provider", "provider_vendor", default=None, type=click.Choice(VALID_PROVIDERS), help=_build_provider_help())
@click.option("--mode", default=None, type=click.Choice(VALID_MODES), help="Execution mode: api or cli")
@click.option("--model", default=None, help="Model identifier (auto-set from preset if omitted)")
@click.option("--rate-limit", default=60, type=int, help="Requests per minute limit (default: 60)")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def add(interactive, name, provider_vendor, mode, model, rate_limit, fmt):
    """Add a new AI provider.

    \b
    With --provider and --mode, defaults are filled in automatically:
      surfaced providers add --provider anthropic --mode api
        → name="Claude Sonnet 4.6", model=claude-sonnet-4-6

    \b
    Override any default:
      surfaced providers add --provider anthropic --mode api --model claude-opus-4-6 --name "Claude Opus"

    \b
    Interactive mode walks you through each option:
      surfaced providers add --interactive
    """
    if interactive:
        provider_vendor, name, mode, model, rate_limit = _interactive_add(
            provider_vendor, name, mode, model, rate_limit,
        )

    if not provider_vendor:
        click.echo("Error: --provider is required (or use --interactive).", err=True)
        click.echo(f"Valid providers: {', '.join(VALID_PROVIDERS)}", err=True)
        raise SystemExit(1)

    if not mode:
        click.echo("Error: --mode is required (or use --interactive).", err=True)
        click.echo(f"Valid modes: {', '.join(VALID_MODES)}", err=True)
        raise SystemExit(1)

    # Fill defaults from preset
    preset = PROVIDER_PRESETS.get((provider_vendor, mode))
    if preset:
        default_name, default_model, _, _ = preset
        name = name or default_name
        model = model or default_model
    else:
        if not all([name, model]):
            click.echo("Error: --name and --model are required for unknown provider combinations.", err=True)
            raise SystemExit(1)

    provider = Provider(
        name=name,
        provider=provider_vendor,
        execution_mode=mode,
        model=model,
        rate_limit_rpm=rate_limit,
    )
    _qs().insert_provider(provider)
    click.echo(_format_provider(provider, fmt))


def _interactive_add(
    provider_vendor: str | None,
    name: str | None,
    mode: str | None,
    model: str | None,
    rate_limit: int,
) -> tuple[str, str, str, str, int]:
    """Walk the user through provider creation with questionary."""
    import questionary

    # 1. Pick provider vendor
    if not provider_vendor:
        choices = [
            questionary.Choice(title="anthropic — Anthropic (Claude)", value="anthropic"),
            questionary.Choice(title="openai    — OpenAI (GPT, Codex)", value="openai"),
            questionary.Choice(title="google    — Google (Gemini)", value="google"),
        ]
        provider_vendor = questionary.select(
            "Provider:",
            choices=choices,
        ).ask()
        if not provider_vendor:
            raise SystemExit(0)

    # 2. Pick mode
    if not mode:
        mode = questionary.select(
            "Execution mode:",
            choices=[
                questionary.Choice("api — call via SDK with API key", value="api"),
                questionary.Choice("cli — run as subprocess", value="cli"),
            ],
        ).ask()
        if not mode:
            raise SystemExit(0)

    preset = PROVIDER_PRESETS.get((provider_vendor, mode))
    default_name, default_model, _, _ = preset if preset else ("", "", "", "")

    # 3. Name
    if not name:
        name = questionary.text(
            "Provider name:",
            default=default_name,
        ).ask()
        if not name:
            raise SystemExit(0)

    # 4. Model
    if not model:
        model = questionary.text(
            "Model identifier:",
            default=default_model,
        ).ask()
        if not model:
            raise SystemExit(0)

    # 5. Rate limit
    rate_str = questionary.text(
        "Rate limit (requests per minute):",
        default=str(rate_limit),
    ).ask()
    try:
        rate_limit = int(rate_str)
    except (TypeError, ValueError):
        rate_limit = 60

    return provider_vendor, name, mode, model, rate_limit


@providers.command("list")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def list_providers(fmt):
    """List all providers."""
    providers_list = _qs().get_providers()
    if fmt == "json":
        click.echo(json.dumps([json.loads(_format_provider(p, "json")) for p in providers_list]))
        return
    if not providers_list:
        click.echo("No providers found.")
        return
    for p in providers_list:
        click.echo(f"  {p.id}  {p.name} ({p.model}) [{p.provider}/{p.execution_mode}]")


@providers.command()
@click.argument("provider_id")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def show(provider_id, fmt):
    """Show provider details."""
    provider = _qs().get_provider(UUID(provider_id))
    if not provider:
        click.echo(f"Provider {provider_id} not found.", err=True)
        raise SystemExit(1)
    click.echo(_format_provider(provider, fmt))


@providers.command()
@click.argument("provider_id")
def delete(provider_id):
    """Soft-delete a provider."""
    _qs().delete_provider(UUID(provider_id))
    click.echo(f"Provider {provider_id} deleted.")
