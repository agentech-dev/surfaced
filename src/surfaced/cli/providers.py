"""Provider management CLI commands."""

import json
from uuid import UUID

import click

from surfaced.db.queries import QueryService
from surfaced.models.provider import Provider

VALID_MODES = ["api", "cli"]


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


@click.group()
def providers():
    """Manage AI providers."""
    pass


@providers.command()
@click.option("--name", required=True, help="Provider display name")
@click.option("--type", "provider_type", required=True, help="Provider type (e.g. anthropic_api, claude_cli)")
@click.option("--mode", required=True, type=click.Choice(VALID_MODES), help="Execution mode")
@click.option("--model", required=True, help="Model identifier")
@click.option("--rate-limit", default=60, type=int, help="Requests per minute limit")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def add(name, provider_type, mode, model, rate_limit, fmt):
    """Add a new AI provider."""
    provider = Provider(
        name=name,
        provider_type=provider_type,
        execution_mode=mode,
        model=model,
        rate_limit_rpm=rate_limit,
    )
    _qs().insert_provider(provider)
    click.echo(_format_provider(provider, fmt))


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
