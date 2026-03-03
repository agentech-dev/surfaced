"""Purge local CLI provider history stores."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import click

# Known history/memory store locations per provider type.
# Each entry is (description, path_pattern) where ~ is expanded.
KNOWN_STORES: dict[str, list[tuple[str, str]]] = {
    "claude_cli": [
        ("Claude Code projects (sessions, memory)", "~/.claude/projects"),
        ("Claude Code todos", "~/.claude/todos"),
    ],
    "codex_cli": [
        ("Codex sessions database", "~/.codex/sqlite"),
        ("Codex shell snapshots", "~/.codex/shell_snapshots"),
        ("Codex log", "~/.codex/log"),
        ("Codex tmp", "~/.codex/tmp"),
    ],
    "gemini_cli": [
        ("Gemini session history", "~/.gemini/history"),
        ("Gemini tmp", "~/.gemini/tmp"),
    ],
}


def _expand(path: str) -> Path:
    return Path(os.path.expanduser(path))


def _find_stores() -> list[tuple[str, str, Path]]:
    """Return (provider, description, path) for all stores that exist on disk."""
    found = []
    for provider, stores in KNOWN_STORES.items():
        for description, path_pattern in stores:
            path = _expand(path_pattern)
            if path.exists():
                found.append((provider, description, path))
    return found


@click.command()
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
def purge(yes):
    """Delete known CLI provider history and memory stores.

    This is a destructive operation. It finds and removes local history files
    for CLI providers (e.g. Claude Code sessions, memory, todos).

    Not called automatically by any command. Intended for manual use or
    future autonomous mode on clean machines.
    """
    found = _find_stores()

    if not found:
        click.echo("No known history stores found.")
        return

    click.echo("Found the following history stores:\n")
    total_size = 0
    for provider, description, path in found:
        size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        total_size += size
        size_mb = size / (1024 * 1024)
        click.echo(f"  [{provider}] {description}")
        click.echo(f"           {path}  ({size_mb:.1f} MB)")

    click.echo(f"\nTotal: {total_size / (1024 * 1024):.1f} MB across {len(found)} stores")
    click.echo("")

    if not yes:
        click.confirm(click.style("This will permanently delete all of the above. Continue?", fg="red"), abort=True)

    for provider, description, path in found:
        shutil.rmtree(path)
        click.echo(f"  Deleted {path}")

    click.echo("\nPurge complete.")
