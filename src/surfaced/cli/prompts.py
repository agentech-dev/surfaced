"""Prompt management CLI commands."""

import json
from uuid import UUID

import click

from surfaced.db.queries import QueryService
from surfaced.models.prompt import Prompt

VALID_CATEGORIES = [
    "brand_query", "competitor_comparison", "industry_query",
    "feature_query", "problem_solving",
]


def _qs():
    return QueryService()


def _format_prompt(prompt: Prompt, fmt: str) -> str:
    if fmt == "json":
        return json.dumps({
            "id": str(prompt.id),
            "text": prompt.text,
            "category": prompt.category,
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
    """Manage prompts."""
    pass


@prompts.command()
@click.option("--text", required=True, help="Prompt text")
@click.option("--category", required=True, type=click.Choice(VALID_CATEGORIES))
@click.option("--brand", required=True, help="Brand ID")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--template", is_flag=True, help="Mark as template")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def add(text, category, brand, tags, template, fmt):
    """Add a new prompt."""
    variables = Prompt.extract_variables(text) if template else []
    prompt = Prompt(
        text=text,
        category=category,
        brand_id=UUID(brand),
        tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else [],
        is_template=1 if template else 0,
        variables=variables,
    )
    _qs().insert_prompt(prompt)
    click.echo(_format_prompt(prompt, fmt))


@prompts.command("list")
@click.option("--category", default=None, type=click.Choice(VALID_CATEGORIES))
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--brand", default=None, help="Filter by brand ID")
@click.option("--active/--inactive", default=True)
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def list_prompts(category, tag, brand, active, fmt):
    """List prompts."""
    brand_id = UUID(brand) if brand else None
    prompt_list = _qs().get_prompts(
        active_only=active, category=category, tag=tag, brand_id=brand_id,
    )
    if fmt == "json":
        click.echo(json.dumps([json.loads(_format_prompt(p, "json")) for p in prompt_list]))
        return
    if not prompt_list:
        click.echo("No prompts found.")
        return
    for p in prompt_list:
        tags_str = f" [{', '.join(p.tags)}]" if p.tags else ""
        click.echo(f"  {p.id}  [{p.category}] {p.text[:60]}...{tags_str}")


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
@click.option("--category", default=None, type=click.Choice(VALID_CATEGORIES))
@click.option("--tags", default=None, help="Comma-separated tags (replaces existing)")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def edit(prompt_id, text, category, tags, fmt):
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

    JSON file should contain an array of objects with: text, category, brand_id, tags (optional).
    """
    with open(filepath) as f:
        data = json.load(f)

    qs = _qs()
    count = 0
    for item in data:
        variables = Prompt.extract_variables(item["text"]) if item.get("is_template") else []
        prompt = Prompt(
            text=item["text"],
            category=item["category"],
            brand_id=UUID(item["brand_id"]),
            tags=item.get("tags", []),
            is_template=1 if item.get("is_template") else 0,
            variables=variables,
        )
        qs.insert_prompt(prompt)
        count += 1

    click.echo(f"Imported {count} prompts.")
