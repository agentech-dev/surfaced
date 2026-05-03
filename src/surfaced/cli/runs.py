"""Run history CLI commands."""

import json
from uuid import UUID

import click

from surfaced.cli.formatting import format_markdown_table
from surfaced.db.queries import QueryService
from surfaced.models.run import Run


def _qs():
    return QueryService()


def _format_run(run: Run, fmt: str) -> str:
    if fmt == "json":
        return json.dumps({
            "id": str(run.id),
            "name": run.name,
            "status": run.status,
            "filters": run.filters,
            "total_prompts": run.total_prompts,
            "completed_prompts": run.completed_prompts,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "created_at": run.created_at.isoformat(),
        })
    lines = [
        f"ID:        {run.id}",
        f"Name:      {run.name}",
        f"Status:    {run.status}",
        f"Progress:  {run.completed_prompts}/{run.total_prompts}",
        f"Filters:   {run.filters}",
        f"Started:   {run.started_at}",
        f"Finished:  {run.finished_at or '-'}",
    ]
    return "\n".join(lines)


@click.group("runs")
def runs():
    """View run history.

    \b
    A run record is created each time you execute 'surfaced run'. It records
    the filters used, how many prompts were executed, and the completion status.

    \b
    Examples:
      surfaced runs list
      surfaced runs show <id>

    \b
    CONTEXT FOR AGENTS:
      Runs are read-only records of past executions. Use 'runs list' to
      find a run ID, then 'runs show <id>' for details. For actual
      results data (mention rates, response text), use 'surfaced analytics'
      instead. Runs are created automatically by 'surfaced run'.
    """
    pass


@runs.command("list")
@click.option("--limit", default=20, type=int, help="Max runs to show")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def list_runs(limit, fmt):
    """List recent runs."""
    run_list = _qs().get_runs(limit=limit)
    if fmt == "json":
        click.echo(json.dumps([json.loads(_format_run(r, "json")) for r in run_list]))
        return
    if not run_list:
        click.echo("No runs found.")
        return
    click.echo(format_markdown_table([
        {
            "id": r.id,
            "status": r.status,
            "name": r.name,
            "progress": f"{r.completed_prompts}/{r.total_prompts}",
        }
        for r in run_list
    ]))


@runs.command()
@click.argument("run_id")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def show(run_id, fmt):
    """Show run details."""
    run = _qs().get_run(UUID(run_id))
    if not run:
        click.echo(f"Run {run_id} not found.", err=True)
        raise SystemExit(1)
    click.echo(_format_run(run, fmt))
