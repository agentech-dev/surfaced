"""Main CLI entry point for surfaced."""

import os

import click

from surfaced.cli.init import init
from surfaced.cli.bootstrap import bootstrap
from surfaced.cli.setup import setup
from surfaced.cli.brands import brands
from surfaced.cli.prompts import prompts
from surfaced.cli.providers import providers
from surfaced.cli.run import run
from surfaced.cli.campaigns import campaigns
from surfaced.cli.analytics import analytics
from surfaced.cli.purge import purge


def _load_env():
    """Load .env file without overwriting already-exported variables.

    Checks ~/.surfaced/.env and ./.env in that order.
    Only sets a variable if it is not already present in the environment.
    """
    candidates = [
        os.path.join(os.path.expanduser("~"), ".surfaced", ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key and value and key not in os.environ:
                    os.environ[key] = value


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Surfaced - Open-source AI visibility tracking."""
    _load_env()


cli.add_command(init)
cli.add_command(bootstrap)
cli.add_command(setup)
cli.add_command(brands)
cli.add_command(prompts)
cli.add_command(providers)
cli.add_command(run)
cli.add_command(campaigns)
cli.add_command(analytics)
cli.add_command(purge)
