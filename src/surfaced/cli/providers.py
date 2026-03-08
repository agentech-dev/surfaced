"""Provider management CLI commands."""

import json
from uuid import UUID

import click

from surfaced.db.queries import QueryService
from surfaced.models.provider import Provider

VALID_TYPES = [
    "anthropic_api",
    "openai_api",
    "gemini_api",
    "claude_cli",
    "codex_cli",
    "gemini_cli",
]

VALID_MODES = ["api", "cli"]

# Provider presets: type → (default_name, mode, default_model, env_var/binary, description)
PROVIDER_PRESETS = {
    "anthropic_api": ("Claude Sonnet 4.6", "api", "claude-sonnet-4-6", "ANTHROPIC_API_KEY", "Anthropic API (requires ANTHROPIC_API_KEY)"),
    "openai_api":    ("GPT-5.2",           "api", "gpt-5.2",          "OPENAI_API_KEY",    "OpenAI API (requires OPENAI_API_KEY)"),
    "gemini_api":    ("Gemini 3.1 Pro",    "api", "gemini-3.1-pro-preview", "GEMINI_API_KEY", "Google Gemini API (requires GEMINI_API_KEY)"),
    "claude_cli":    ("Claude CLI",         "cli", "claude-sonnet-4-6", "claude",            "Claude Code CLI subprocess"),
    "codex_cli":     ("Codex CLI",          "cli", "codex",            "codex",              "OpenAI Codex CLI subprocess"),
    "gemini_cli":    ("Gemini CLI",         "cli", "gemini-3.1-pro-preview", "gemini",       "Google Gemini CLI subprocess"),
}


def _qs():
    return QueryService()


def _format_provider(provider: Provider, fmt: str) -> str:
    if fmt == "json":
        return json.dumps({
            "id": str(provider.id),
            "name": provider.name,
            "provider_type": provider.provider_type,
            "execution_mode": provider.execution_mode,
            "model": provider.model,
            "config": provider.config,
            "rate_limit_rpm": provider.rate_limit_rpm,
            "is_active": provider.is_active,
            "created_at": provider.created_at.isoformat(),
            "updated_at": provider.updated_at.isoformat(),
        })
    lines = [
        f"ID:        {provider.id}",
        f"Name:      {provider.name}",
        f"Type:      {provider.provider_type}",
        f"Mode:      {provider.execution_mode}",
        f"Model:     {provider.model}",
        f"RPM Limit: {provider.rate_limit_rpm}",
        f"Active:    {'yes' if provider.is_active else 'no'}",
        f"Created:   {provider.created_at}",
    ]
    return "\n".join(lines)


def _build_type_help() -> str:
    lines = ["Provider type. Available types:\n"]
    for ptype, (name, mode, model, req, desc) in PROVIDER_PRESETS.items():
        lines.append(f"  {ptype:16s} mode={mode}, model={model} — {desc}")
    return "\n".join(lines)


@click.group()
def providers():
    """Manage AI providers.

    \b
    Available provider types:
      anthropic_api    mode=api, model=claude-sonnet-4-6       Anthropic API (requires ANTHROPIC_API_KEY)
      openai_api       mode=api, model=gpt-5.2                 OpenAI API (requires OPENAI_API_KEY)
      gemini_api       mode=api, model=gemini-3.1-pro-preview  Google Gemini API (requires GEMINI_API_KEY)
      claude_cli       mode=cli, model=claude-sonnet-4-6       Claude Code CLI subprocess
      codex_cli        mode=cli, model=codex                   OpenAI Codex CLI subprocess
      gemini_cli       mode=cli, model=gemini-3.1-pro-preview  Google Gemini CLI subprocess

    \b
    Examples:
      surfaced providers add --type anthropic_api
      surfaced providers add --type codex_cli --model codex
      surfaced providers add --interactive
      surfaced providers list

    \b
    CONTEXT FOR AGENTS:
      Providers define which AI models to query during runs. API providers
      need the corresponding API key in ~/.surfaced/.env. CLI providers need
      the binary installed (e.g. 'claude', 'codex', 'gemini').
      You need at least one provider before running prompts.
      Use 'surfaced providers add --type <type>' — defaults are filled in
      automatically. Only --type is required. Use 'surfaced providers list' to
      verify what is configured. After adding providers, run prompts with
      'surfaced run --brand <name>'.
    """
    pass


@providers.command()
@click.option("--interactive", "-i", is_flag=True, help="Interactive guided setup")
@click.option("--name", default=None, help="Provider display name (auto-set from type if omitted)")
@click.option("--type", "provider_type", default=None, type=click.Choice(VALID_TYPES), help=_build_type_help())
@click.option("--mode", default=None, type=click.Choice(VALID_MODES), help="Execution mode: api or cli (auto-set from type if omitted)")
@click.option("--model", default=None, help="Model identifier (auto-set from type if omitted)")
@click.option("--rate-limit", default=60, type=int, help="Requests per minute limit (default: 60)")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def add(interactive, name, provider_type, mode, model, rate_limit, fmt):
    """Add a new AI provider.

    \b
    With --type only, defaults are filled in automatically:
      surfaced providers add --type anthropic_api
        → name="Claude Sonnet 4.6", mode=api, model=claude-sonnet-4-6

    \b
    Override any default:
      surfaced providers add --type anthropic_api --model claude-opus-4-6 --name "Claude Opus"

    \b
    Interactive mode walks you through each option:
      surfaced providers add --interactive
    """
    if interactive:
        provider_type, name, mode, model, rate_limit = _interactive_add(
            provider_type, name, mode, model, rate_limit,
        )

    if not provider_type:
        click.echo("Error: --type is required (or use --interactive).", err=True)
        click.echo(f"Valid types: {', '.join(VALID_TYPES)}", err=True)
        raise SystemExit(1)

    # Fill defaults from preset
    preset = PROVIDER_PRESETS.get(provider_type)
    if preset:
        default_name, default_mode, default_model, _, _ = preset
        name = name or default_name
        mode = mode or default_mode
        model = model or default_model
    else:
        if not all([name, mode, model]):
            click.echo("Error: --name, --mode, and --model are required for unknown provider types.", err=True)
            raise SystemExit(1)

    provider = Provider(
        name=name,
        provider_type=provider_type,
        execution_mode=mode,
        model=model,
        rate_limit_rpm=rate_limit,
    )
    _qs().insert_provider(provider)
    click.echo(_format_provider(provider, fmt))


def _interactive_add(
    provider_type: str | None,
    name: str | None,
    mode: str | None,
    model: str | None,
    rate_limit: int,
) -> tuple[str, str, str, str, int]:
    """Walk the user through provider creation with questionary."""
    import questionary

    # 1. Pick type
    if not provider_type:
        choices = [
            questionary.Choice(
                title=f"{ptype:16s} — {desc}",
                value=ptype,
            )
            for ptype, (_, _, _, _, desc) in PROVIDER_PRESETS.items()
        ]
        provider_type = questionary.select(
            "Provider type:",
            choices=choices,
        ).ask()
        if not provider_type:
            raise SystemExit(0)

    preset = PROVIDER_PRESETS.get(provider_type)
    default_name, default_mode, default_model, _, _ = preset if preset else ("", "", "", "", "")

    # 2. Name
    if not name:
        name = questionary.text(
            "Provider name:",
            default=default_name,
        ).ask()
        if not name:
            raise SystemExit(0)

    # 3. Mode
    if not mode:
        mode = questionary.select(
            "Execution mode:",
            choices=[
                questionary.Choice("api — call via SDK with API key", value="api"),
                questionary.Choice("cli — run as subprocess", value="cli"),
            ],
            default="api — call via SDK with API key" if default_mode == "api" else "cli — run as subprocess",
        ).ask()
        if not mode:
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

    return provider_type, name, mode, model, rate_limit


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
        click.echo(f"  {p.id}  {p.name} ({p.model}) [{p.execution_mode}]")


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
