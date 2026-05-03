"""Tests for typed query service operations."""

from uuid import uuid4

from surfaced.db.queries import QueryService
from surfaced.models.alignment_judgment import AlignmentJudgment
from surfaced.models.canonical_position import CanonicalPosition
from surfaced.models.recommendation_judgment import RecommendationJudgment


class FakeDB:
    def __init__(self):
        self.inserts = []
        self.commands = []

    def insert_rows(self, table, data, column_names):
        self.inserts.append((table, data, column_names))

    def execute_no_result(self, query, parameters=None):
        self.commands.append((query, parameters))


def test_insert_recommendation_judgment_writes_audit_columns():
    db = FakeDB()
    qs = QueryService(db=db)
    judgment = RecommendationJudgment(
        answer_id=uuid4(),
        run_id=uuid4(),
        prompt_id=uuid4(),
        provider_id=uuid4(),
        brand_id=uuid4(),
        judge_model="claude-haiku-4-5",
        recommendation_status="judge_failed",
        raw_output="probably",
        error_message="Judge returned an invalid recommendation label",
        latency_ms=123,
    )

    qs.insert_recommendation_judgment(judgment)

    table, data, columns = db.inserts[0]
    assert table == "recommendation_judgments"
    assert columns == [
        "id", "answer_id", "run_id", "prompt_id", "provider_id",
        "brand_id", "judge_model", "recommendation_status",
        "raw_output", "error_message", "latency_ms", "created_at",
    ]
    assert data[0][7] == "judge_failed"
    assert data[0][8] == "probably"


def test_insert_canonical_position_writes_columns():
    db = FakeDB()
    qs = QueryService(db=db)
    position = CanonicalPosition(
        brand_id=uuid4(),
        topic="joins",
        statement="ClickHouse supports high-performance joins.",
    )

    qs.insert_canonical_position(position)

    table, data, columns = db.inserts[0]
    assert table == "canonical_positions"
    assert columns == [
        "id", "brand_id", "topic", "statement", "is_active",
        "created_at", "updated_at",
    ]
    assert data[0][2] == "joins"
    assert data[0][3] == "ClickHouse supports high-performance joins."


def test_update_canonical_position_uses_standard_update():
    db = FakeDB()
    qs = QueryService(db=db)
    position = CanonicalPosition(
        brand_id=uuid4(),
        topic="joins",
        statement="Updated statement.",
    )

    qs.update_canonical_position(position)

    query, params = db.commands[0]
    assert "UPDATE canonical_positions" in query
    assert "SET" in query
    assert "WHERE id = {id:UUID}" in query
    assert params["topic"] == "joins"
    assert params["statement"] == "Updated statement."


def test_insert_alignment_judgment_writes_audit_columns():
    db = FakeDB()
    qs = QueryService(db=db)
    judgment = AlignmentJudgment(
        answer_id=uuid4(),
        run_id=uuid4(),
        prompt_id=uuid4(),
        provider_id=uuid4(),
        brand_id=uuid4(),
        alignment_position_id=uuid4(),
        judge_model="claude-haiku-4-5",
        alignment_status="judge_failed",
        rationale="",
        raw_output="probably",
        error_message="Judge returned an invalid alignment label",
        latency_ms=123,
    )

    qs.insert_alignment_judgment(judgment)

    table, data, columns = db.inserts[0]
    assert table == "alignment_judgments"
    assert columns == [
        "id", "answer_id", "run_id", "prompt_id", "provider_id",
        "brand_id", "alignment_position_id", "judge_model",
        "alignment_status", "rationale", "raw_output",
        "error_message", "latency_ms", "created_at",
    ]
    assert data[0][8] == "judge_failed"
    assert data[0][10] == "probably"
