"""Run campaign CLI command."""

from uuid import UUID

import click

from surfaced.db.queries import QueryService
from surfaced.engine.runner import run_campaign


@click.command()
@click.option("--category", default=None, help="Filter by prompt category")
@click.option("--provider", default=None, help="Filter by provider name")
@click.option("--tag", default=None, help="Filter by prompt tag")
@click.option("--brand", default=None, help="Filter by brand ID or name")
@click.option("--prompt", "prompt_id", default=None, help="Run a specific prompt ID")
@click.option("--dry-run", is_flag=True, help="Show what would execute without running")
@click.option("--no-history", is_flag=True, help="Best-effort: tell CLI providers not to load local history/memory")
def run(category, provider, tag, brand, prompt_id, dry_run, no_history):
    """Run prompts against AI providers and store results."""
    qs = QueryService()

    # Resolve brand name to ID if needed
    brand_uuid = None
    if brand:
        try:
            brand_uuid = UUID(brand)
        except ValueError:
            brand_obj = qs.get_brand_by_name(brand)
            if not brand_obj:
                click.echo(f"Brand '{brand}' not found.", err=True)
                raise SystemExit(1)
            brand_uuid = brand_obj.id

    prompt_uuid = UUID(prompt_id) if prompt_id else None

    run_campaign(
        qs=qs,
        category=category,
        provider_name=provider,
        tag=tag,
        brand_id=brand_uuid,
        prompt_id=prompt_uuid,
        dry_run=dry_run,
        no_history=no_history,
    )
