"""Prompt management CLI commands."""

import json
from uuid import UUID

import click

from surfaced.cli.formatting import format_markdown_table
from surfaced.db.queries import QueryService
from surfaced.engine.analyzer import is_prompt_branded
from surfaced.models.prompt import Prompt


def _qs():
    return QueryService()


def _resolve_brand_id(qs: QueryService, brand: str, active_only: bool = True) -> UUID:
    """Resolve a brand UUID, name, or alias to a brand ID."""
    try:
        return UUID(brand)
    except ValueError:
        pass

    brand_obj = qs.get_brand_by_name(brand)
    if brand_obj and (brand_obj.is_active or not active_only):
        return brand_obj.id

    brand_lookup = brand.casefold()
    matches = [
        b for b in qs.get_brands(active_only=active_only)
        if b.name.casefold() == brand_lookup
        or any(alias.casefold() == brand_lookup for alias in b.aliases)
    ]
    if len(matches) == 1:
        return matches[0].id
    if len(matches) > 1:
        click.echo(f"Brand '{brand}' is ambiguous; use a UUID instead.", err=True)
    else:
        click.echo(f"Brand '{brand}' not found.", err=True)
    raise SystemExit(1)


def _resolve_branded(qs: QueryService, text: str, brand_id: UUID, override: bool | None) -> bool:
    """Use an explicit branded value or infer it from the brand name/aliases."""
    if override is not None:
        return override
    brand = qs.get_brand(brand_id)
    return is_prompt_branded(text, brand) if brand else False


def _format_prompt(prompt: Prompt, fmt: str) -> str:
    if fmt == "json":
        return json.dumps({
            "id": str(prompt.id),
            "text": prompt.text,
            "category": prompt.category,
            "branded": prompt.branded,
            "recommendation_enabled": prompt.recommendation_enabled,
            "brand_id": str(prompt.brand_id),
            "tags": prompt.tags,
            "is_template": prompt.is_template,
            "variables": prompt.variables,
            "is_active": prompt.is_active,
            "created_at": prompt.created_at.isoformat(),
            "updated_at": prompt.updated_at.isoformat(),
        })
    lines = [
        f"ID:        {prompt.id}",
        f"Text:      {prompt.text}",
        f"Category:  {prompt.category}",
        f"Branded:   {'yes' if prompt.branded else 'no'}",
        f"Recs:      {'enabled' if prompt.recommendation_enabled else 'disabled'}",
        f"Brand ID:  {prompt.brand_id}",
        f"Tags:      {', '.join(prompt.tags) if prompt.tags else '-'}",
        f"Template:  {'yes' if prompt.is_template else 'no'}",
        f"Variables: {', '.join(prompt.variables) if prompt.variables else '-'}",
        f"Active:    {'yes' if prompt.is_active else 'no'}",
        f"Created:   {prompt.created_at}",
    ]
    return "\n".join(lines)


@click.group()
def prompts():
    """Manage prompts.

    \b
    Prompts are the questions sent to AI providers during runs. Each prompt
    belongs to a brand, has a user-defined category for analytics grouping,
    and tracks whether the prompt text itself names the brand.

    \b
    Tags are used for scheduling (daily, weekly, monthly) and filtering.

    \b
    Examples:
      surfaced prompts add --text "Best tools for X?" --category data_warehouse --brand Acme --tags daily
      surfaced prompts add --text "How does Acme compare to Globex?" --category competitor_research --brand Acme --branded
      surfaced prompts list --brand Acme --category data_warehouse
      surfaced prompts import prompts.json

    \b
    CONTEXT FOR AGENTS:
      You need at least one brand before adding prompts. --brand accepts the
      brand UUID, name, or alias.
      For bulk setup, use 'surfaced prompts import' with a JSON file. The JSON
      format is: [{"text": "...", "category": "data_warehouse", "brand_id": "<uuid>", "tags": ["daily"]}].
      The optional "branded" field overrides auto-detection from the prompt
      text and brand name/aliases.
      The optional "recommendation_enabled" field controls recommendation judging
      for that prompt and defaults to true.
      Tags like 'daily', 'weekly', 'monthly' control which prompts run on cron schedules.
      After adding prompts, run them with 'surfaced run --brand <name>'.
    """
    pass


@prompts.command()
@click.option("--text", required=True, help="Prompt text")
@click.option("--category", required=True, help="User-defined analytics category")
@click.option("--brand", required=True, help="Brand ID, name, or alias")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--branded/--unbranded", default=None, help="Override brand-name auto-detection")
@click.option("--recommendations/--no-recommendations", default=True, help="Enable recommendation judging for this prompt")
@click.option("--template", is_flag=True, help="Mark as template")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def add(text, category, brand, tags, branded, recommendations, template, fmt):
    """Add a new prompt."""
    qs = _qs()
    brand_id = _resolve_brand_id(qs, brand)
    variables = Prompt.extract_variables(text) if template else []
    prompt = Prompt(
        text=text,
        category=category,
        brand_id=brand_id,
        branded=_resolve_branded(qs, text, brand_id, branded),
        recommendation_enabled=recommendations,
        tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else [],
        is_template=1 if template else 0,
        variables=variables,
    )
    qs.insert_prompt(prompt)
    click.echo(_format_prompt(prompt, fmt))


@prompts.command("list")
@click.option("--category", default=None, help="Filter by user-defined category")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--brand", default=None, help="Filter by brand ID, name, or alias")
@click.option("--active/--inactive", default=True)
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def list_prompts(category, tag, brand, active, fmt):
    """List prompts."""
    qs = _qs()
    brand_id = _resolve_brand_id(qs, brand, active_only=active) if brand else None
    prompt_list = qs.get_prompts(
        active_only=active, category=category, tag=tag, brand_id=brand_id,
    )
    if fmt == "json":
        click.echo(json.dumps([json.loads(_format_prompt(p, "json")) for p in prompt_list]))
        return
    if not prompt_list:
        click.echo("No prompts found.")
        return
    click.echo(format_markdown_table([
        {
            "id": p.id,
            "category": p.category,
            "branded": "yes" if p.branded else "no",
            "recommendations": "yes" if p.recommendation_enabled else "no",
            "text": p.text,
            "tags": ", ".join(p.tags) if p.tags else "-",
        }
        for p in prompt_list
    ]))


@prompts.command()
@click.argument("prompt_id")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def show(prompt_id, fmt):
    """Show prompt details."""
    prompt = _qs().get_prompt(UUID(prompt_id))
    if not prompt:
        click.echo(f"Prompt {prompt_id} not found.", err=True)
        raise SystemExit(1)
    click.echo(_format_prompt(prompt, fmt))


@prompts.command()
@click.argument("prompt_id")
@click.option("--text", default=None)
@click.option("--category", default=None, help="User-defined analytics category")
@click.option("--tags", default=None, help="Comma-separated tags (replaces existing)")
@click.option("--branded/--unbranded", default=None, help="Set branded metadata")
@click.option("--recommendations/--no-recommendations", default=None, help="Set recommendation judging metadata")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def edit(prompt_id, text, category, tags, branded, recommendations, fmt):
    """Edit a prompt."""
    qs = _qs()
    prompt = qs.get_prompt(UUID(prompt_id))
    if not prompt:
        click.echo(f"Prompt {prompt_id} not found.", err=True)
        raise SystemExit(1)
    if text is not None:
        prompt.text = text
        if prompt.is_template:
            prompt.variables = Prompt.extract_variables(text)
    if category is not None:
        prompt.category = category
    if tags is not None:
        prompt.tags = [t.strip() for t in tags.split(",") if t.strip()]
    if branded is not None:
        prompt.branded = branded
    if recommendations is not None:
        prompt.recommendation_enabled = recommendations
    qs.update_prompt(prompt)
    click.echo(_format_prompt(prompt, fmt))


@prompts.command()
@click.argument("prompt_id")
def delete(prompt_id):
    """Soft-delete a prompt."""
    _qs().delete_prompt(UUID(prompt_id))
    click.echo(f"Prompt {prompt_id} deleted.")


@prompts.command("import")
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def import_prompts(filepath, fmt):
    """Bulk import prompts from a JSON file.

    \b
    JSON format: [{"text": "...", "category": "data_warehouse", "brand_id": "<uuid>", "tags": ["daily"]}]
    Optional "branded": true/false overrides auto-detection.
    Optional "recommendation_enabled": true/false controls recommendation judging.

    \b
    CONTEXT FOR AGENTS:
      The starter prompts file is at ~/.surfaced/prompts_import.json (or
      prompts_import.json in the project root). You can use it as a template.
      The brand_id in the JSON must be a valid UUID from 'surfaced brands list'.
    """
    with open(filepath) as f:
        data = json.load(f)

    qs = _qs()
    count = 0
    for item in data:
        brand_id = UUID(item["brand_id"])
        variables = Prompt.extract_variables(item["text"]) if item.get("is_template") else []
        prompt = Prompt(
            text=item["text"],
            category=item["category"],
            brand_id=brand_id,
            branded=_resolve_branded(qs, item["text"], brand_id, item.get("branded")),
            recommendation_enabled=item.get("recommendation_enabled", True),
            tags=item.get("tags", []),
            is_template=1 if item.get("is_template") else 0,
            variables=variables,
        )
        qs.insert_prompt(prompt)
        count += 1

    click.echo(f"Imported {count} prompts.")
