"""Smoke tests for SQL assets."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_recommendation_columns_in_schema_assets():
    prompts_sql = (ROOT / "clickhouse" / "tables" / "003_prompts.sql").read_text()
    answers_sql = (ROOT / "clickhouse" / "tables" / "005_answers.sql").read_text()

    assert "recommendation_enabled Bool DEFAULT true" in prompts_sql
    assert "recommendation_status Enum8" in answers_sql


def test_recommendation_rate_query_excludes_unjudged_denominator():
    query_sql = (ROOT / "clickhouse" / "queries" / "recommendation_rate.sql").read_text()

    assert "recommendation_status IN ('recommended', 'neutral', 'negative')" in query_sql
    assert "recommendation_status = 'judge_failed'" in query_sql
    assert "WHERE brand_id = {brand_id:UUID}" in query_sql
