"""Smoke tests for SQL assets."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_recommendation_columns_in_schema_assets():
    prompts_sql = (ROOT / "clickhouse" / "tables" / "003_prompts.sql").read_text()
    answers_sql = (ROOT / "clickhouse" / "tables" / "005_answers.sql").read_text()
    judgments_sql = (ROOT / "clickhouse" / "tables" / "006_recommendation_judgments.sql").read_text()

    assert "recommendation_enabled Bool DEFAULT true" in prompts_sql
    assert "recommendation_status Enum8" in answers_sql
    assert "CREATE TABLE IF NOT EXISTS recommendation_judgments" in judgments_sql
    assert "raw_output String DEFAULT ''" in judgments_sql
    assert "error_message String DEFAULT ''" in judgments_sql
    assert "ORDER BY (brand_id, toDate(created_at), answer_id)" in judgments_sql


def test_alignment_columns_in_schema_assets():
    prompts_sql = (ROOT / "clickhouse" / "tables" / "003_prompts.sql").read_text()
    answers_sql = (ROOT / "clickhouse" / "tables" / "005_answers.sql").read_text()
    positions_sql = (ROOT / "clickhouse" / "tables" / "007_canonical_positions.sql").read_text()
    judgments_sql = (ROOT / "clickhouse" / "tables" / "008_alignment_judgments.sql").read_text()

    assert "alignment_enabled Bool DEFAULT false" in prompts_sql
    assert "alignment_position_id UUID DEFAULT '00000000-0000-0000-0000-000000000000'" in prompts_sql
    assert "alignment_status Enum8" in answers_sql
    assert "alignment_rationale String DEFAULT ''" in answers_sql
    assert "CREATE TABLE IF NOT EXISTS canonical_positions" in positions_sql
    assert "ENGINE = MergeTree" in positions_sql
    assert "ORDER BY (brand_id, id)" in positions_sql
    assert "CREATE TABLE IF NOT EXISTS alignment_judgments" in judgments_sql
    assert "rationale String DEFAULT ''" in judgments_sql
    assert "ORDER BY (brand_id, toDate(created_at), alignment_position_id, answer_id)" in judgments_sql


def test_recommendation_rate_query_excludes_unjudged_denominator():
    query_sql = (ROOT / "clickhouse" / "queries" / "recommendation_rate.sql").read_text()

    assert "recommendation_status IN ('recommended', 'neutral', 'negative')" in query_sql
    assert "recommendation_status = 'judge_failed'" in query_sql
    assert "WHERE brand_id = {brand_id:UUID}" in query_sql


def test_alignment_rate_query_excludes_failures_from_denominator():
    query_sql = (ROOT / "clickhouse" / "queries" / "alignment_rate.sql").read_text()

    assert "alignment_status IN ('aligned', 'partial', 'misaligned', 'silent')" in query_sql
    assert "alignment_status = 'judge_failed'" in query_sql
    assert "a.brand_id = {brand_id:UUID}" in query_sql


def test_recommendation_judge_failures_query_exposes_debug_fields():
    query_sql = (ROOT / "clickhouse" / "queries" / "recommendation_judge_failures.sql").read_text()

    assert "j.raw_output" in query_sql
    assert "j.error_message" in query_sql
    assert "INNER JOIN answers AS a ON a.id = j.answer_id" in query_sql
    assert "j.recommendation_status = 'judge_failed'" in query_sql


def test_alignment_judge_failures_query_exposes_debug_fields():
    query_sql = (ROOT / "clickhouse" / "queries" / "alignment_judge_failures.sql").read_text()

    assert "j.raw_output" in query_sql
    assert "j.error_message" in query_sql
    assert "INNER JOIN answers AS a ON a.id = j.answer_id" in query_sql
    assert "j.alignment_status = 'judge_failed'" in query_sql
