"""Tests for typed query service operations."""

from uuid import uuid4

from surfaced.db.queries import QueryService
from surfaced.models.recommendation_judgment import RecommendationJudgment


class FakeDB:
    def __init__(self):
        self.inserts = []

    def insert_rows(self, table, data, column_names):
        self.inserts.append((table, data, column_names))


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
