"""Core execution engine - runs prompts against providers and stores results."""

from __future__ import annotations

import json
import time
import traceback
from datetime import datetime
from uuid import UUID

import click

from surfaced.db.queries import QueryService
from surfaced.engine.analyzer import check_brand_mentioned, find_competitors_mentioned
from surfaced.engine.rate_limiter import RateLimiter
from surfaced.engine.template import render_prompt
from surfaced.models.campaign import Campaign
from surfaced.models.prompt_run import PromptRun
from surfaced.providers.registry import get_provider


MAX_RETRIES = 3
BACKOFF_BASE = 2.0


def run_campaign(
    qs: QueryService,
    category: str | None = None,
    provider_name: str | None = None,
    tag: str | None = None,
    brand_id: UUID | None = None,
    prompt_id: UUID | None = None,
    dry_run: bool = False,
    no_history: bool = False,
) -> Campaign | None:
    """Execute prompts against providers and store results."""
    # Gather prompts
    prompts = qs.get_prompts(active_only=True, category=category, tag=tag, brand_id=brand_id)
    if prompt_id:
        prompts = [p for p in prompts if p.id == prompt_id]

    if not prompts:
        click.echo("No prompts match the filters.")
        return None

    # Gather providers
    providers = qs.get_providers(active_only=True)
    if provider_name:
        providers = [p for p in providers if p.name == provider_name]

    if not providers:
        click.echo("No providers match the filters.")
        return None

    total = len(prompts) * len(providers)

    # Build filters record
    filters = json.dumps({
        k: v for k, v in {
            "category": category, "provider": provider_name,
            "tag": tag, "brand_id": str(brand_id) if brand_id else None,
            "prompt_id": str(prompt_id) if prompt_id else None,
        }.items() if v
    })

    if dry_run:
        click.echo(f"Dry run: {len(prompts)} prompts x {len(providers)} providers = {total} executions")
        for prompt in prompts:
            for prov in providers:
                click.echo(f"  [{prov.name}] {prompt.text[:80]}...")
        return None

    # Validate all providers before starting (fail fast on missing keys, etc.)
    ai_providers = {}
    for prov_record in providers:
        try:
            ai_providers[prov_record.id] = get_provider(prov_record)
        except Exception as e:
            click.echo(f"Error: Provider '{prov_record.name}' failed to initialize: {e}", err=True)
            raise SystemExit(1)

    # Create campaign
    campaign = Campaign(
        name=f"Campaign {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        status="running",
        filters=filters,
        total_prompts=total,
    )
    qs.insert_campaign(campaign)
    click.echo(f"Campaign {campaign.id} started ({total} executions)")

    completed = 0
    errors = 0
    rate_limiters: dict[UUID, RateLimiter] = {}

    try:
        for prov_record in providers:
            ai_provider = ai_providers[prov_record.id]
            if prov_record.id not in rate_limiters:
                rate_limiters[prov_record.id] = RateLimiter(rpm=prov_record.rate_limit_rpm)
            limiter = rate_limiters[prov_record.id]

            for prompt in prompts:
                rendered_text = render_prompt(prompt)
                brand = qs.get_brand(prompt.brand_id)

                # Retry loop
                for attempt in range(MAX_RETRIES):
                    try:
                        limiter.wait()
                        response = ai_provider.execute(rendered_text, no_history=no_history)

                        brand_mentioned = 0
                        competitors_mentioned = []
                        if brand:
                            brand_mentioned = 1 if check_brand_mentioned(response.text, brand) else 0
                            competitors_mentioned = find_competitors_mentioned(response.text, brand)

                        run = PromptRun(
                            campaign_id=campaign.id,
                            prompt_id=prompt.id,
                            provider_id=prov_record.id,
                            brand_id=prompt.brand_id,
                            prompt_text=rendered_text,
                            prompt_category=prompt.category,
                            response_text=response.text,
                            model=response.model,
                            provider_name=prov_record.name,
                            latency_ms=response.latency_ms,
                            input_tokens=response.input_tokens,
                            output_tokens=response.output_tokens,
                            status="success",
                            brand_mentioned=brand_mentioned,
                            competitors_mentioned=competitors_mentioned,
                        )
                        qs.insert_prompt_run(run)
                        completed += 1
                        click.echo(f"  [{completed}/{total}] {prov_record.name}: {prompt.text[:50]}... ({'mentioned' if brand_mentioned else 'not mentioned'})")
                        break

                    except KeyboardInterrupt:
                        raise
                    except Exception as e:
                        if attempt < MAX_RETRIES - 1:
                            wait = BACKOFF_BASE ** attempt
                            click.echo(f"  Retry {attempt + 1}/{MAX_RETRIES} after {wait}s: {e}")
                            time.sleep(wait)
                        else:
                            errors += 1
                            run = PromptRun(
                                campaign_id=campaign.id,
                                prompt_id=prompt.id,
                                provider_id=prov_record.id,
                                brand_id=prompt.brand_id,
                                prompt_text=rendered_text,
                                prompt_category=prompt.category,
                                response_text="",
                                model=prov_record.model,
                                provider_name=prov_record.name,
                                latency_ms=0,
                                status="error",
                                error_message=traceback.format_exc(),
                            )
                            qs.insert_prompt_run(run)
                            click.echo(f"  [{completed + errors}/{total}] FAILED: {e}")

    except KeyboardInterrupt:
        click.echo(f"\n\nCampaign interrupted. {completed} completed, {errors} failed before cancellation.")
        campaign.completed_prompts = completed
        campaign.status = "cancelled"
        campaign.finished_at = datetime.now()
        qs.update_campaign(campaign)
        return campaign

    # Update campaign
    campaign.completed_prompts = completed
    campaign.status = "completed" if errors == 0 else "failed"
    campaign.finished_at = datetime.now()
    qs.update_campaign(campaign)
    click.echo(f"\nCampaign {campaign.id} finished: {completed} succeeded, {errors} failed")
    return campaign
