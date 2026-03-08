"""Run CLI command — execute prompts against providers."""

from uuid import UUID

import click

from surfaced.db.queries import QueryService
from surfaced.engine.runner import execute_run


@click.command()
@click.option("--category", default=None, help="Filter by prompt category")
@click.option("--provider", default=None, help="Filter by provider name")
@click.option("--tag", default=None, help="Filter by prompt tag")
@click.option("--brand", default=None, help="Filter by brand ID or name")
@click.option("--prompt", "prompt_id", default=None, help="Run a specific prompt ID")
@click.option("--dry-run", is_flag=True, help="Show what would execute without running")
@click.option("--no-history", is_flag=True, help="Best-effort: tell CLI providers not to load local history/memory")
def run(category, provider, tag, brand, prompt_id, dry_run, no_history):
    """Run prompts against AI providers and store results.

    \b
    Executes matching prompts against all active providers and stores the
    results (response text, brand mention detection, latency, token counts)
    in the prompt_runs table. Each execution creates a run record.

    \b
    Filter what runs:
      --brand       Only prompts for this brand (name or UUID)
      --category    Only prompts in this category
      --provider    Only run against this provider (by name)
      --tag         Only prompts with this tag (e.g. daily, weekly)
      --prompt      Run a single specific prompt by UUID

    \b
    Examples:
      surfaced run --brand "Acme"                       Run all prompts for Acme
      surfaced run --brand "Acme" --tag daily            Run daily-tagged prompts only
      surfaced run --brand "Acme" --provider "Claude Sonnet 4.6"  Run against one provider
      surfaced run --brand "Acme" --dry-run              Preview without executing

    \b
    CONTEXT FOR AGENTS:
      This is the main command that actually queries AI providers. It requires:
      (1) at least one brand with prompts, (2) at least one active provider,
      (3) API keys in ~/.surfaced/.env for API providers or CLI tools installed
      for CLI providers. Use --dry-run first to verify what will execute.
      After running, view results with 'surfaced analytics summary --brand <name>'.
      Use 'surfaced runs list' to see past runs.
    """
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

    execute_run(
        qs=qs,
        category=category,
        provider_name=provider,
        tag=tag,
        brand_id=brand_uuid,
        prompt_id=prompt_uuid,
        dry_run=dry_run,
        no_history=no_history,
    )
