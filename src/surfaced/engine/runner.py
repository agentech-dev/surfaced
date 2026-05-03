"""Core execution engine - runs prompts against providers and stores results."""

from __future__ import annotations

import json
import time
import traceback
from datetime import datetime
from uuid import UUID

import click

from surfaced.db.queries import QueryService
from surfaced.engine.analyzer import (
    check_brand_mentioned,
    find_competitors_mentioned,
    get_alignment_judge_model,
    get_recommendation_judge_model,
    is_recommendation_judge_enabled,
    judge_alignment,
    judge_recommendation,
)
from surfaced.engine.rate_limiter import RateLimiter
from surfaced.engine.template import render_prompt
from surfaced.models.alignment_judgment import AlignmentJudgment
from surfaced.models.answer import Answer
from surfaced.models.recommendation_judgment import RecommendationJudgment
from surfaced.models.run import Run
from surfaced.providers.registry import get_provider


MAX_RETRIES = 3
BACKOFF_BASE = 2.0
RUN_LOG_COLUMNS = ["#", "model", "prompt"]
RUN_LOG_WIDTHS = {
    "#": 4,
    "model": 20,
    "prompt": 64,
}


def execute_run(
    qs: QueryService,
    category: str | None = None,
    provider_name: str | None = None,
    tag: str | None = None,
    brand_id: UUID | None = None,
    prompt_id: UUID | None = None,
    dry_run: bool = False,
    no_history: bool = False,
) -> Run | None:
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

    # Create run record
    run_record = Run(
        name=f"Run {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        status="running",
        filters=filters,
        total_prompts=total,
    )
    qs.insert_run(run_record)
    click.echo(
        f"Run {run_record.id} started. "
        f"{len(prompts)} prompts x {len(providers)} providers = {total} executions."
    )
    _echo_run_log_header()

    completed = 0
    errors = 0
    rate_limiters: dict[UUID, RateLimiter] = {}
    recommendation_judge_enabled = is_recommendation_judge_enabled()
    recommendation_judge_model = get_recommendation_judge_model()
    alignment_judge_model = get_alignment_judge_model()

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
                        next_row = completed + errors + 1
                        _echo_run_log_row(
                            next_row,
                            prov_record.name,
                            rendered_text,
                        )
                        response = ai_provider.execute(rendered_text, no_history=no_history)

                        brand_mentioned = 0
                        competitors_mentioned = []
                        recommendation_status = "not_mentioned"
                        recommendation_judgment = None
                        alignment_status = "not_applicable"
                        alignment_position_id = None
                        alignment_rationale = ""
                        alignment_judgment = None
                        if brand:
                            brand_mentioned = 1 if check_brand_mentioned(response.text, brand) else 0
                            competitors_mentioned = find_competitors_mentioned(response.text, brand)
                            if (
                                brand_mentioned
                                and recommendation_judge_enabled
                                and prompt.recommendation_enabled
                            ):
                                _echo_run_log_row(
                                    next_row,
                                    recommendation_judge_model,
                                    f"JUDGE: Was {brand.name} recommended?",
                                )
                            recommendation_judgment = judge_recommendation(
                                response.text,
                                brand,
                                brand_mentioned=bool(brand_mentioned),
                                enabled=(
                                    recommendation_judge_enabled
                                    and prompt.recommendation_enabled
                                ),
                            )
                            recommendation_status = recommendation_judgment.status
                        if prompt.alignment_enabled and prompt.alignment_position_id:
                            canonical_position = qs.get_canonical_position(
                                prompt.alignment_position_id,
                            )
                            if canonical_position:
                                _echo_run_log_row(
                                    next_row,
                                    alignment_judge_model,
                                    f"JUDGE: Is answer aligned to {canonical_position.topic}?",
                                )
                                alignment_judgment = judge_alignment(
                                    response.text,
                                    canonical_position,
                                )
                                alignment_status = alignment_judgment.status
                                alignment_position_id = canonical_position.id
                                alignment_rationale = alignment_judgment.rationale

                        answer = Answer(
                            run_id=run_record.id,
                            prompt_id=prompt.id,
                            provider_id=prov_record.id,
                            brand_id=prompt.brand_id,
                            prompt_text=rendered_text,
                            prompt_category=prompt.category,
                            prompt_branded=prompt.branded,
                            response_text=response.text,
                            model=response.model,
                            provider_name=prov_record.name,
                            latency_ms=response.latency_ms,
                            input_tokens=response.input_tokens,
                            output_tokens=response.output_tokens,
                            status="success",
                            brand_mentioned=brand_mentioned,
                            recommendation_status=recommendation_status,
                            alignment_status=alignment_status,
                            alignment_position_id=alignment_position_id,
                            alignment_rationale=alignment_rationale,
                            competitors_mentioned=competitors_mentioned,
                        )
                        qs.insert_answer(answer)
                        if (
                            recommendation_judgment
                            and recommendation_judgment.attempted
                        ):
                            qs.insert_recommendation_judgment(
                                RecommendationJudgment(
                                    answer_id=answer.id,
                                    run_id=answer.run_id,
                                    prompt_id=answer.prompt_id,
                                    provider_id=answer.provider_id,
                                    brand_id=answer.brand_id,
                                    judge_model=recommendation_judgment.judge_model,
                                    recommendation_status=recommendation_judgment.status,
                                    raw_output=recommendation_judgment.raw_output,
                                    error_message=recommendation_judgment.error_message,
                                    latency_ms=recommendation_judgment.latency_ms,
                                )
                            )
                        if (
                            alignment_judgment
                            and alignment_judgment.attempted
                            and alignment_position_id
                        ):
                            qs.insert_alignment_judgment(
                                AlignmentJudgment(
                                    answer_id=answer.id,
                                    run_id=answer.run_id,
                                    prompt_id=answer.prompt_id,
                                    provider_id=answer.provider_id,
                                    brand_id=answer.brand_id,
                                    alignment_position_id=alignment_position_id,
                                    judge_model=alignment_judgment.judge_model,
                                    alignment_status=alignment_judgment.status,
                                    rationale=alignment_judgment.rationale,
                                    raw_output=alignment_judgment.raw_output,
                                    error_message=alignment_judgment.error_message,
                                    latency_ms=alignment_judgment.latency_ms,
                                )
                            )
                        completed += 1
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
                            answer = Answer(
                                run_id=run_record.id,
                                prompt_id=prompt.id,
                                provider_id=prov_record.id,
                                brand_id=prompt.brand_id,
                                prompt_text=rendered_text,
                                prompt_category=prompt.category,
                                prompt_branded=prompt.branded,
                                response_text="",
                                model=prov_record.model,
                                provider_name=prov_record.name,
                                latency_ms=0,
                                status="error",
                                error_message=traceback.format_exc(),
                            )
                            qs.insert_answer(answer)
                            _echo_run_log_row(
                                completed + errors,
                                prov_record.name,
                                f"FAILED: {e}",
                            )

    except KeyboardInterrupt:
        click.echo(f"\n\nRun interrupted. {completed} completed, {errors} failed before cancellation.")
        run_record.completed_prompts = completed
        run_record.status = "cancelled"
        run_record.finished_at = datetime.now()
        qs.update_run(run_record)
        return run_record

    # Update run
    run_record.completed_prompts = completed
    run_record.status = "completed" if errors == 0 else "failed"
    run_record.finished_at = datetime.now()
    qs.update_run(run_record)
    click.echo(f"\nRun {run_record.id} finished: {completed} succeeded, {errors} failed")
    return run_record

def _echo_run_log_header() -> None:
    """Print a Markdown-style streaming table header for run progress."""
    click.echo(_format_run_log_row(RUN_LOG_COLUMNS))
    click.echo(_format_run_log_separator())


def _echo_run_log_row(number: int, model: str, prompt: str) -> None:
    """Print a single Markdown-style run progress row."""
    click.echo(_format_run_log_row([str(number), model, prompt]))


def _format_run_log_row(values: list[str]) -> str:
    padded = []
    for column, value in zip(RUN_LOG_COLUMNS, values, strict=True):
        text = _truncate_run_log_cell(str(value), RUN_LOG_WIDTHS[column])
        padded.append(text.ljust(RUN_LOG_WIDTHS[column]))
    return "| " + " | ".join(padded) + " |"


def _format_run_log_separator() -> str:
    return "| " + " | ".join("-" * RUN_LOG_WIDTHS[c] for c in RUN_LOG_COLUMNS) + " |"


def _truncate_run_log_cell(value: str, width: int) -> str:
    cleaned = " ".join(value.split()).replace("|", "\\|")
    if len(cleaned) <= width:
        return cleaned
    return cleaned[: max(width - 3, 0)].rstrip() + "..."
