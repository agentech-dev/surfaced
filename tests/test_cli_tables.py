"""Tests for Markdown table CLI output."""

from datetime import datetime
from uuid import UUID

from click.testing import CliRunner

import surfaced.cli.brands as brands_cli
import surfaced.cli.prompts as prompts_cli
import surfaced.cli.providers as providers_cli
import surfaced.cli.runs as runs_cli
from surfaced.cli.analytics import _format_table
from surfaced.cli.formatting import format_markdown_table
from surfaced.models.brand import Brand
from surfaced.models.prompt import Prompt
from surfaced.models.provider import Provider
from surfaced.models.run import Run


BRAND_ID = UUID("00000000-0000-0000-0000-000000000001")
PROMPT_ID = UUID("00000000-0000-0000-0000-000000000002")
PROVIDER_ID = UUID("00000000-0000-0000-0000-000000000003")
RUN_ID = UUID("00000000-0000-0000-0000-000000000004")


def test_format_markdown_table_escapes_cells():
    output = format_markdown_table([
        {"name": "Acme | Labs", "description": "first line\nsecond line", "empty": None},
    ])

    assert output == "\n".join([
        "| name         | description            | empty   |",
        "|--------------|------------------------|---------|",
        r"| Acme \| Labs | first line second line | -       |",
    ])


def test_analytics_table_uses_markdown():
    output = _format_table([
        {"category": "data|warehouse", "mention_rate": 0.5},
    ])

    assert output == "\n".join([
        "| category        | mention_rate   |",
        "|-----------------|----------------|",
        r"| data\|warehouse | 0.5            |",
    ])


def test_prompts_list_uses_markdown_table(monkeypatch):
    prompt = Prompt(
        id=PROMPT_ID,
        text="How does Acme compare?",
        category="data_warehouse",
        brand_id=BRAND_ID,
        branded=True,
        tags=["daily", "weekly"],
    )

    class FakeQueryService:
        def get_prompts(self, active_only=True, category=None, tag=None, brand_id=None):
            return [prompt]

    monkeypatch.setattr(prompts_cli, "_qs", FakeQueryService)

    result = CliRunner().invoke(prompts_cli.prompts, ["list"])

    assert result.exit_code == 0
    assert result.output == format_markdown_table([{
        "id": PROMPT_ID,
        "category": "data_warehouse",
        "branded": "yes",
        "text": "How does Acme compare?",
        "tags": "daily, weekly",
    }]) + "\n"


def test_brands_list_uses_markdown_table(monkeypatch):
    brand = Brand(id=BRAND_ID, name="Acme")

    class FakeQueryService:
        def get_brands(self, active_only=True):
            return [brand]

    monkeypatch.setattr(brands_cli, "_qs", FakeQueryService)

    result = CliRunner().invoke(brands_cli.brands, ["list"])

    assert result.exit_code == 0
    assert result.output == format_markdown_table([{
        "id": BRAND_ID,
        "name": "Acme",
        "status": "active",
    }]) + "\n"


def test_providers_list_uses_markdown_table(monkeypatch):
    provider = Provider(
        id=PROVIDER_ID,
        name="Claude API",
        provider="anthropic",
        execution_mode="api",
        model="claude-sonnet-4-6",
    )

    class FakeQueryService:
        def get_providers(self):
            return [provider]

    monkeypatch.setattr(providers_cli, "_qs", FakeQueryService)

    result = CliRunner().invoke(providers_cli.providers, ["list"])

    assert result.exit_code == 0
    assert result.output == format_markdown_table([{
        "id": PROVIDER_ID,
        "name": "Claude API",
        "provider": "anthropic",
        "mode": "api",
        "model": "claude-sonnet-4-6",
    }]) + "\n"


def test_runs_list_uses_markdown_table(monkeypatch):
    run = Run(
        id=RUN_ID,
        name="Daily prompts",
        status="completed",
        total_prompts=3,
        completed_prompts=2,
        started_at=datetime(2026, 5, 3, 12, 0, 0),
    )

    class FakeQueryService:
        def get_runs(self, limit=20):
            return [run]

    monkeypatch.setattr(runs_cli, "_qs", FakeQueryService)

    result = CliRunner().invoke(runs_cli.runs, ["list"])

    assert result.exit_code == 0
    assert result.output == format_markdown_table([{
        "id": RUN_ID,
        "status": "completed",
        "name": "Daily prompts",
        "progress": "2/3",
    }]) + "\n"
