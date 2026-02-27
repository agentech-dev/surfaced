"""Main CLI entry point for surfaced."""

import click

from surfaced.cli.init import init
from surfaced.cli.brands import brands
from surfaced.cli.prompts import prompts
from surfaced.cli.providers import providers
from surfaced.cli.run import run
from surfaced.cli.campaigns import campaigns
from surfaced.cli.analytics import analytics


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Surfaced - Open-source AI visibility tracking."""
    pass


cli.add_command(init)
cli.add_command(brands)
cli.add_command(prompts)
cli.add_command(providers)
cli.add_command(run)
cli.add_command(campaigns)
cli.add_command(analytics)
