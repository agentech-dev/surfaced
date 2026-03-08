"""Integration tests: analytics queries with real ClickHouse."""

import os
from datetime import datetime
from uuid import uuid4

import pytest

from surfaced.db.queries import QueryService
from surfaced.models.answer import Answer
from surfaced.models.brand import Brand
from surfaced.models.prompt import Prompt
from surfaced.models.provider import Provider
from surfaced.models.run import Run
from conftest import requires_clickhouse

pytestmark = [pytest.mark.integration, requires_clickhouse]


def _find_queries_dir():
    """Find clickhouse/queries/ relative to repo root."""
    current = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(current, "clickhouse", "queries")
    if os.path.isdir(candidate):
        return candidate
    return None


@pytest.fixture
def seeded_brand(real_qs):
    """Insert a brand with answers and return (brand_id, run_id)."""
    brand_id = uuid4()
    brand = Brand(
        id=brand_id, name=f"Analytics_{brand_id.hex[:8]}",
        aliases=["AnalyticsAlias"], competitors=["CompetitorX"],
    )
    real_qs.insert_brand(brand)

    prov_id = uuid4()
    real_qs.insert_provider(Provider(
        id=prov_id, name=f"AnalyticsProv_{prov_id.hex[:8]}",
        provider="anthropic", execution_mode="api", model="claude-sonnet-4-6",
    ))

    run_id = uuid4()
    run = Run(id=run_id, name=f"AnalyticsRun_{run_id.hex[:8]}",
              status="completed", total_prompts=2, completed_prompts=2,
              finished_at=datetime.now())
    real_qs.insert_run(run)

    prompt_id = uuid4()
    real_qs.insert_prompt(Prompt(
        id=prompt_id, text="Analytics prompt",
        category="brand_query", brand_id=brand_id,
    ))

    # Insert 2 answers: one with brand mentioned, one without
    for mentioned in [1, 0]:
        real_qs.insert_answer(Answer(
            id=uuid4(), run_id=run_id, prompt_id=prompt_id,
            provider_id=prov_id, brand_id=brand_id,
            prompt_text="Analytics prompt",
            prompt_category="brand_query",
            response_text="Acme" if mentioned else "other",
            model="claude-sonnet-4-6",
            provider_name=f"AnalyticsProv_{prov_id.hex[:8]}",
            latency_ms=500, status="success",
            brand_mentioned=mentioned,
            competitors_mentioned=["CompetitorX"] if mentioned else [],
        ))

    return brand_id, run_id


@pytest.fixture
def queries_dir():
    d = _find_queries_dir()
    if d is None:
        pytest.skip("clickhouse/queries/ directory not found")
    return d


def _run_query(real_qs, queries_dir, query_name, brand_id, days=30):
    """Helper to load and execute a query SQL file."""
    sql_path = os.path.join(queries_dir, f"{query_name}.sql")
    with open(sql_path) as f:
        sql = f.read()
    # Strip comment lines
    sql_lines = [line for line in sql.strip().split("\n") if not line.strip().startswith("--")]
    sql_clean = "\n".join(sql_lines)
    return real_qs.db.execute(sql_clean, parameters={"brand_id": str(brand_id), "days": days})


def test_summary_query(real_qs, seeded_brand, queries_dir):
    brand_id, _ = seeded_brand
    rows = _run_query(real_qs, queries_dir, "summary", brand_id)
    assert len(rows) == 1
    row = rows[0]
    expected_columns = {
        "total_runs", "total_mentions", "overall_mention_rate_pct",
        "unique_prompts", "providers_used", "avg_latency_ms",
        "earliest_run", "latest_run", "unique_competitors_mentioned",
    }
    assert expected_columns == set(row.keys())
    assert row["total_runs"] == 2  # 2 answers seeded
    assert row["total_mentions"] == 1  # 1 with brand_mentioned=1


def test_mention_frequency_query(real_qs, seeded_brand, queries_dir):
    brand_id, _ = seeded_brand
    rows = _run_query(real_qs, queries_dir, "mention_frequency", brand_id)
    assert len(rows) >= 1
    expected_columns = {"day", "total_runs", "mentions", "mention_rate_pct"}
    assert expected_columns == set(rows[0].keys())
    # Our seeded data is from today, so one row
    assert rows[0]["total_runs"] == 2
    assert rows[0]["mentions"] == 1


def test_share_of_voice_query(real_qs, seeded_brand, queries_dir):
    brand_id, _ = seeded_brand
    rows = _run_query(real_qs, queries_dir, "share_of_voice", brand_id)
    assert len(rows) >= 1
    expected_columns = {
        "prompt_category", "total_runs", "brand_mentions",
        "brand_mention_pct", "competitor_mentions",
    }
    assert expected_columns == set(rows[0].keys())
    assert rows[0]["prompt_category"] == "brand_query"


def test_provider_comparison_query(real_qs, seeded_brand, queries_dir):
    brand_id, _ = seeded_brand
    rows = _run_query(real_qs, queries_dir, "provider_comparison", brand_id)
    assert len(rows) >= 1
    expected_columns = {
        "provider_name", "model", "total_runs", "mentions",
        "mention_rate_pct", "avg_latency_ms", "avg_tokens",
    }
    assert expected_columns == set(rows[0].keys())
    assert rows[0]["model"] == "claude-sonnet-4-6"


def test_consistency_query(real_qs, seeded_brand, queries_dir):
    brand_id, _ = seeded_brand
    rows = _run_query(real_qs, queries_dir, "consistency", brand_id)
    assert len(rows) >= 1
    expected_columns = {
        "prompt_id", "prompt_text_sample", "runs", "mentions",
        "mention_rate_pct", "first_run", "last_run",
    }
    assert expected_columns == set(rows[0].keys())
    assert rows[0]["runs"] == 2
