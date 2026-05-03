"""Canonical position CLI commands."""

import json
from uuid import UUID

import click

from surfaced.cli.formatting import format_markdown_table
from surfaced.cli.prompts import _resolve_brand_id
from surfaced.db.queries import QueryService
from surfaced.models.canonical_position import CanonicalPosition


def _qs():
    return QueryService()


def _format_position(position: CanonicalPosition, fmt: str) -> str:
    if fmt == "json":
        return json.dumps({
            "id": str(position.id),
            "brand_id": str(position.brand_id),
            "topic": position.topic,
            "statement": position.statement,
            "is_active": position.is_active,
            "created_at": position.created_at.isoformat(),
            "updated_at": position.updated_at.isoformat(),
        })
    lines = [
        f"ID:        {position.id}",
        f"Brand ID:  {position.brand_id}",
        f"Topic:     {position.topic}",
        f"Statement: {position.statement}",
        f"Active:    {'yes' if position.is_active else 'no'}",
        f"Created:   {position.created_at}",
        f"Updated:   {position.updated_at}",
    ]
    return "\n".join(lines)


@click.group()
def positions():
    """Manage canonical positions for alignment judging."""
    pass


@positions.command()
@click.option("--brand", required=True, help="Brand ID, name, or alias")
@click.option("--topic", required=True, help="Short topic name")
@click.option("--statement", required=True, help="Canonical position statement")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def add(brand, topic, statement, fmt):
    """Add a canonical position."""
    qs = _qs()
    position = CanonicalPosition(
        brand_id=_resolve_brand_id(qs, brand),
        topic=topic,
        statement=statement,
    )
    qs.insert_canonical_position(position)
    click.echo(_format_position(position, fmt))


@positions.command("list")
@click.option("--brand", default=None, help="Filter by brand ID, name, or alias")
@click.option("--active/--inactive", default=True)
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def list_positions(brand, active, fmt):
    """List canonical positions."""
    qs = _qs()
    brand_id = _resolve_brand_id(qs, brand, active_only=active) if brand else None
    position_list = qs.get_canonical_positions(
        active_only=active,
        brand_id=brand_id,
    )
    if fmt == "json":
        click.echo(json.dumps([
            json.loads(_format_position(p, "json")) for p in position_list
        ]))
        return
    if not position_list:
        click.echo("No canonical positions found.")
        return
    click.echo(format_markdown_table([
        {
            "id": p.id,
            "brand_id": p.brand_id,
            "topic": p.topic,
            "statement": p.statement,
            "status": "active" if p.is_active else "inactive",
        }
        for p in position_list
    ]))


@positions.command()
@click.argument("position_id")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def show(position_id, fmt):
    """Show canonical position details."""
    position = _qs().get_canonical_position(UUID(position_id), active_only=False)
    if not position:
        click.echo(f"Canonical position {position_id} not found.", err=True)
        raise SystemExit(1)
    click.echo(_format_position(position, fmt))


@positions.command()
@click.argument("position_id")
@click.option("--topic", default=None)
@click.option("--statement", default=None)
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def edit(position_id, topic, statement, fmt):
    """Edit a canonical position."""
    qs = _qs()
    position = qs.get_canonical_position(UUID(position_id), active_only=False)
    if not position:
        click.echo(f"Canonical position {position_id} not found.", err=True)
        raise SystemExit(1)
    if topic is not None:
        position.topic = topic
    if statement is not None:
        position.statement = statement
    qs.update_canonical_position(position)
    click.echo(_format_position(position, fmt))


@positions.command()
@click.argument("position_id")
def delete(position_id):
    """Soft-delete a canonical position."""
    _qs().delete_canonical_position(UUID(position_id))
    click.echo(f"Canonical position {position_id} deleted.")
