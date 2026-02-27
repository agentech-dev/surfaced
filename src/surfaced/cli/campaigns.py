"""Campaign management CLI commands."""

import json
from uuid import UUID

import click

from surfaced.db.queries import QueryService
from surfaced.models.campaign import Campaign


def _qs():
    return QueryService()


def _format_campaign(campaign: Campaign, fmt: str) -> str:
    if fmt == "json":
        return json.dumps({
            "id": str(campaign.id),
            "name": campaign.name,
            "status": campaign.status,
            "filters": campaign.filters,
            "total_prompts": campaign.total_prompts,
            "completed_prompts": campaign.completed_prompts,
            "started_at": campaign.started_at.isoformat(),
            "finished_at": campaign.finished_at.isoformat() if campaign.finished_at else None,
            "created_at": campaign.created_at.isoformat(),
        })
    lines = [
        f"ID:        {campaign.id}",
        f"Name:      {campaign.name}",
        f"Status:    {campaign.status}",
        f"Progress:  {campaign.completed_prompts}/{campaign.total_prompts}",
        f"Filters:   {campaign.filters}",
        f"Started:   {campaign.started_at}",
        f"Finished:  {campaign.finished_at or '-'}",
    ]
    return "\n".join(lines)


@click.group()
def campaigns():
    """View campaign history."""
    pass


@campaigns.command("list")
@click.option("--limit", default=20, type=int, help="Max campaigns to show")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def list_campaigns(limit, fmt):
    """List recent campaigns."""
    campaign_list = _qs().get_campaigns(limit=limit)
    if fmt == "json":
        click.echo(json.dumps([json.loads(_format_campaign(c, "json")) for c in campaign_list]))
        return
    if not campaign_list:
        click.echo("No campaigns found.")
        return
    for c in campaign_list:
        click.echo(f"  {c.id}  [{c.status}] {c.name}  ({c.completed_prompts}/{c.total_prompts})")


@campaigns.command()
@click.argument("campaign_id")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def show(campaign_id, fmt):
    """Show campaign details."""
    campaign = _qs().get_campaign(UUID(campaign_id))
    if not campaign:
        click.echo(f"Campaign {campaign_id} not found.", err=True)
        raise SystemExit(1)
    click.echo(_format_campaign(campaign, fmt))
