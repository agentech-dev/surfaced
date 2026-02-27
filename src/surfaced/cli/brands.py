"""Brand management CLI commands."""

import json
from uuid import UUID

import click

from surfaced.db.queries import QueryService
from surfaced.models.brand import Brand


def _qs():
    return QueryService()


def _format_brand(brand: Brand, fmt: str) -> str:
    if fmt == "json":
        return json.dumps({
            "id": str(brand.id),
            "name": brand.name,
            "domain": brand.domain,
            "description": brand.description,
            "aliases": brand.aliases,
            "competitors": brand.competitors,
            "is_active": brand.is_active,
            "created_at": brand.created_at.isoformat(),
            "updated_at": brand.updated_at.isoformat(),
        })
    lines = [
        f"ID:          {brand.id}",
        f"Name:        {brand.name}",
        f"Domain:      {brand.domain}",
        f"Description: {brand.description}",
        f"Aliases:     {', '.join(brand.aliases) if brand.aliases else '-'}",
        f"Competitors: {', '.join(brand.competitors) if brand.competitors else '-'}",
        f"Active:      {'yes' if brand.is_active else 'no'}",
        f"Created:     {brand.created_at}",
    ]
    return "\n".join(lines)


@click.group()
def brands():
    """Manage brands."""
    pass


@brands.command()
@click.option("--name", required=True, help="Brand name")
@click.option("--domain", default="", help="Brand domain")
@click.option("--description", default="", help="Brand description")
@click.option("--aliases", default="", help="Comma-separated aliases")
@click.option("--competitors", default="", help="Comma-separated competitors")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def add(name, domain, description, aliases, competitors, fmt):
    """Add a new brand."""
    brand = Brand(
        name=name,
        domain=domain,
        description=description,
        aliases=[a.strip() for a in aliases.split(",") if a.strip()] if aliases else [],
        competitors=[c.strip() for c in competitors.split(",") if c.strip()] if competitors else [],
    )
    _qs().insert_brand(brand)
    click.echo(_format_brand(brand, fmt))


@brands.command("list")
@click.option("--active/--inactive", default=True, help="Filter by active status")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def list_brands(active, fmt):
    """List all brands."""
    brands_list = _qs().get_brands(active_only=active)
    if fmt == "json":
        click.echo(json.dumps([json.loads(_format_brand(b, "json")) for b in brands_list]))
        return
    if not brands_list:
        click.echo("No brands found.")
        return
    for b in brands_list:
        status = "" if b.is_active else " [inactive]"
        click.echo(f"  {b.id}  {b.name}{status}")


@brands.command()
@click.argument("brand_id")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def show(brand_id, fmt):
    """Show brand details."""
    brand = _qs().get_brand(UUID(brand_id))
    if not brand:
        click.echo(f"Brand {brand_id} not found.", err=True)
        raise SystemExit(1)
    click.echo(_format_brand(brand, fmt))


@brands.command()
@click.argument("brand_id")
@click.option("--name", default=None)
@click.option("--domain", default=None)
@click.option("--description", default=None)
@click.option("--aliases", default=None, help="Comma-separated aliases (replaces existing)")
@click.option("--competitors", default=None, help="Comma-separated competitors (replaces existing)")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def edit(brand_id, name, domain, description, aliases, competitors, fmt):
    """Edit a brand."""
    qs = _qs()
    brand = qs.get_brand(UUID(brand_id))
    if not brand:
        click.echo(f"Brand {brand_id} not found.", err=True)
        raise SystemExit(1)
    if name is not None:
        brand.name = name
    if domain is not None:
        brand.domain = domain
    if description is not None:
        brand.description = description
    if aliases is not None:
        brand.aliases = [a.strip() for a in aliases.split(",") if a.strip()]
    if competitors is not None:
        brand.competitors = [c.strip() for c in competitors.split(",") if c.strip()]
    qs.update_brand(brand)
    click.echo(_format_brand(brand, fmt))


@brands.command()
@click.argument("brand_id")
def delete(brand_id):
    """Soft-delete a brand."""
    _qs().delete_brand(UUID(brand_id))
    click.echo(f"Brand {brand_id} deleted.")
