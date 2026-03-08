"""Tests for QueryService (mock DBClient)."""

from datetime import datetime
from unittest.mock import MagicMock, call
from uuid import UUID, uuid4

import pytest

from surfaced.db.client import DBClient
from surfaced.db.queries import QueryService
from surfaced.models.answer import Answer
from surfaced.models.brand import Brand
from surfaced.models.prompt import Prompt
from surfaced.models.provider import Provider
from surfaced.models.run import Run

BRAND_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
PROVIDER_ID = UUID("550e8400-e29b-41d4-a716-446655440001")
PROMPT_ID = UUID("550e8400-e29b-41d4-a716-446655440002")
RUN_ID = UUID("550e8400-e29b-41d4-a716-446655440003")
NOW = datetime(2024, 6, 15, 12, 0, 0)


@pytest.fixture
def db():
    return MagicMock(spec=DBClient)


@pytest.fixture
def qs(db):
    return QueryService(db=db)


# --- Brands ---

class TestBrands:
    def test_insert_brand(self, qs, db):
        brand = Brand(id=BRAND_ID, name="Acme", domain="acme.com",
                      created_at=NOW, updated_at=NOW)
        result = qs.insert_brand(brand)
        assert result is brand
        db.insert_rows.assert_called_once()
        args = db.insert_rows.call_args
        assert args[0][0] == "brands"
        assert "id" in args[1]["column_names"]

    def test_get_brands_active(self, qs, db):
        db.execute.return_value = [{
            "id": BRAND_ID, "name": "Acme", "domain": "", "description": "",
            "aliases": [], "competitors": [], "is_active": 1,
            "created_at": NOW, "updated_at": NOW,
        }]
        brands = qs.get_brands(active_only=True)
        assert len(brands) == 1
        assert "is_active = 1" in db.execute.call_args[0][0]

    def test_get_brands_all(self, qs, db):
        db.execute.return_value = []
        qs.get_brands(active_only=False)
        sql = db.execute.call_args[0][0]
        assert "is_active" not in sql

    def test_get_brand_by_id(self, qs, db):
        db.execute.return_value = [{
            "id": BRAND_ID, "name": "Acme", "domain": "", "description": "",
            "aliases": [], "competitors": [], "is_active": 1,
            "created_at": NOW, "updated_at": NOW,
        }]
        brand = qs.get_brand(BRAND_ID)
        assert brand.name == "Acme"
        assert db.execute.call_args[1]["parameters"]["id"] == str(BRAND_ID)

    def test_get_brand_not_found(self, qs, db):
        db.execute.return_value = []
        assert qs.get_brand(BRAND_ID) is None

    def test_get_brand_by_name(self, qs, db):
        db.execute.return_value = [{
            "id": BRAND_ID, "name": "Acme", "domain": "", "description": "",
            "aliases": [], "competitors": [], "is_active": 1,
            "created_at": NOW, "updated_at": NOW,
        }]
        brand = qs.get_brand_by_name("Acme")
        assert brand.name == "Acme"

    def test_update_brand(self, qs, db):
        brand = Brand(id=BRAND_ID, name="Acme", created_at=NOW, updated_at=NOW)
        old_updated = brand.updated_at
        qs.update_brand(brand)
        assert brand.updated_at >= old_updated
        db.insert_rows.assert_called_once()

    def test_delete_brand(self, qs, db):
        db.execute.return_value = [{
            "id": BRAND_ID, "name": "Acme", "domain": "", "description": "",
            "aliases": [], "competitors": [], "is_active": 1,
            "created_at": NOW, "updated_at": NOW,
        }]
        qs.delete_brand(BRAND_ID)
        # Should have called insert_rows to re-insert with is_active=0
        db.insert_rows.assert_called_once()

    def test_delete_brand_not_found(self, qs, db):
        db.execute.return_value = []
        qs.delete_brand(BRAND_ID)
        db.insert_rows.assert_not_called()


# --- Providers ---

class TestProviders:
    def test_insert_provider(self, qs, db):
        provider = Provider(id=PROVIDER_ID, name="Claude API", provider="anthropic",
                            execution_mode="api", model="claude-sonnet-4-6",
                            created_at=NOW, updated_at=NOW)
        result = qs.insert_provider(provider)
        assert result is provider
        db.insert_rows.assert_called_once()
        assert db.insert_rows.call_args[0][0] == "providers"

    def test_get_providers(self, qs, db):
        db.execute.return_value = [{
            "id": PROVIDER_ID, "name": "Claude API", "provider": "anthropic",
            "execution_mode": "api", "model": "claude-sonnet-4-6",
            "config": "{}", "rate_limit_rpm": 60, "is_active": 1,
            "created_at": NOW, "updated_at": NOW,
        }]
        providers = qs.get_providers()
        assert len(providers) == 1
        assert "is_active = 1" in db.execute.call_args[0][0]

    def test_get_provider_by_id(self, qs, db):
        db.execute.return_value = [{
            "id": PROVIDER_ID, "name": "Claude API", "provider": "anthropic",
            "execution_mode": "api", "model": "claude-sonnet-4-6",
            "config": "{}", "rate_limit_rpm": 60, "is_active": 1,
            "created_at": NOW, "updated_at": NOW,
        }]
        provider = qs.get_provider(PROVIDER_ID)
        assert provider.name == "Claude API"

    def test_get_provider_by_name(self, qs, db):
        db.execute.return_value = [{
            "id": PROVIDER_ID, "name": "Claude API", "provider": "anthropic",
            "execution_mode": "api", "model": "claude-sonnet-4-6",
            "config": "{}", "rate_limit_rpm": 60, "is_active": 1,
            "created_at": NOW, "updated_at": NOW,
        }]
        provider = qs.get_provider_by_name("Claude API")
        assert provider.name == "Claude API"

    def test_get_provider_not_found(self, qs, db):
        db.execute.return_value = []
        assert qs.get_provider(PROVIDER_ID) is None

    def test_delete_provider(self, qs, db):
        db.execute.return_value = [{
            "id": PROVIDER_ID, "name": "Claude API", "provider": "anthropic",
            "execution_mode": "api", "model": "claude-sonnet-4-6",
            "config": "{}", "rate_limit_rpm": 60, "is_active": 1,
            "created_at": NOW, "updated_at": NOW,
        }]
        qs.delete_provider(PROVIDER_ID)
        db.insert_rows.assert_called_once()


# --- Prompts ---

class TestPrompts:
    def test_insert_prompt(self, qs, db):
        prompt = Prompt(id=PROMPT_ID, text="test", category="brand_query",
                        brand_id=BRAND_ID, created_at=NOW, updated_at=NOW)
        result = qs.insert_prompt(prompt)
        assert result is prompt
        db.insert_rows.assert_called_once()
        assert db.insert_rows.call_args[0][0] == "prompts"

    def test_get_prompts_no_filters(self, qs, db):
        db.execute.return_value = [{
            "id": PROMPT_ID, "text": "test", "category": "brand_query",
            "brand_id": BRAND_ID, "tags": [], "is_template": 0,
            "variables": [], "is_active": 1,
            "created_at": NOW, "updated_at": NOW,
        }]
        prompts = qs.get_prompts()
        assert len(prompts) == 1
        sql = db.execute.call_args[0][0]
        assert "is_active = 1" in sql

    def test_get_prompts_category_filter(self, qs, db):
        db.execute.return_value = []
        qs.get_prompts(category="brand_query")
        sql = db.execute.call_args[0][0]
        assert "category = {category:String}" in sql

    def test_get_prompts_tag_filter(self, qs, db):
        db.execute.return_value = []
        qs.get_prompts(tag="daily")
        sql = db.execute.call_args[0][0]
        assert "has(tags, {tag:String})" in sql

    def test_get_prompts_brand_filter(self, qs, db):
        db.execute.return_value = []
        qs.get_prompts(brand_id=BRAND_ID)
        sql = db.execute.call_args[0][0]
        assert "brand_id = {brand_id:UUID}" in sql

    def test_get_prompts_combined_filters(self, qs, db):
        db.execute.return_value = []
        qs.get_prompts(category="brand_query", tag="daily", brand_id=BRAND_ID)
        sql = db.execute.call_args[0][0]
        assert "category" in sql
        assert "has(tags" in sql
        assert "brand_id" in sql

    def test_get_prompt_by_id(self, qs, db):
        db.execute.return_value = [{
            "id": PROMPT_ID, "text": "test", "category": "brand_query",
            "brand_id": BRAND_ID, "tags": [], "is_template": 0,
            "variables": [], "is_active": 1,
            "created_at": NOW, "updated_at": NOW,
        }]
        prompt = qs.get_prompt(PROMPT_ID)
        assert prompt.text == "test"

    def test_get_prompt_not_found(self, qs, db):
        db.execute.return_value = []
        assert qs.get_prompt(PROMPT_ID) is None

    def test_update_prompt(self, qs, db):
        prompt = Prompt(id=PROMPT_ID, text="test", category="brand_query",
                        brand_id=BRAND_ID, created_at=NOW, updated_at=NOW)
        qs.update_prompt(prompt)
        assert prompt.updated_at >= NOW
        db.insert_rows.assert_called_once()

    def test_delete_prompt(self, qs, db):
        db.execute.return_value = [{
            "id": PROMPT_ID, "text": "test", "category": "brand_query",
            "brand_id": BRAND_ID, "tags": [], "is_template": 0,
            "variables": [], "is_active": 1,
            "created_at": NOW, "updated_at": NOW,
        }]
        qs.delete_prompt(PROMPT_ID)
        db.insert_rows.assert_called_once()


# --- Runs ---

class TestRuns:
    def test_insert_run(self, qs, db):
        run = Run(id=RUN_ID, name="Test", created_at=NOW, updated_at=NOW)
        result = qs.insert_run(run)
        assert result is run
        db.insert_rows.assert_called_once()
        assert db.insert_rows.call_args[0][0] == "runs"

    def test_insert_run_none_finished_at(self, qs, db):
        run = Run(id=RUN_ID, name="Test", finished_at=None,
                  created_at=NOW, updated_at=NOW)
        qs.insert_run(run)
        data = db.insert_rows.call_args[0][1][0]
        # finished_at should be epoch when None
        assert data[7] == datetime(1970, 1, 1)

    def test_get_runs(self, qs, db):
        db.execute.return_value = [{
            "id": RUN_ID, "name": "Test", "status": "running",
            "filters": "{}", "total_prompts": 0, "completed_prompts": 0,
            "started_at": NOW, "finished_at": None,
            "created_at": NOW, "updated_at": NOW,
        }]
        runs = qs.get_runs(limit=10)
        assert len(runs) == 1
        assert "LIMIT 10" in db.execute.call_args[0][0]

    def test_get_run_by_id(self, qs, db):
        db.execute.return_value = [{
            "id": RUN_ID, "name": "Test", "status": "running",
            "filters": "{}", "total_prompts": 0, "completed_prompts": 0,
            "started_at": NOW, "finished_at": None,
            "created_at": NOW, "updated_at": NOW,
        }]
        run = qs.get_run(RUN_ID)
        assert run.name == "Test"

    def test_get_run_not_found(self, qs, db):
        db.execute.return_value = []
        assert qs.get_run(RUN_ID) is None

    def test_update_run(self, qs, db):
        run = Run(id=RUN_ID, name="Test", created_at=NOW, updated_at=NOW)
        qs.update_run(run)
        assert run.updated_at >= NOW
        db.insert_rows.assert_called_once()


# --- Answers ---

class TestAnswers:
    def test_insert_answer(self, qs, db):
        answer = Answer(
            id=UUID("550e8400-e29b-41d4-a716-446655440004"),
            run_id=RUN_ID, prompt_id=PROMPT_ID, provider_id=PROVIDER_ID,
            brand_id=BRAND_ID, prompt_text="t", prompt_category="brand_query",
            response_text="r", model="m", provider_name="p",
            latency_ms=100, status="success", created_at=NOW,
        )
        result = qs.insert_answer(answer)
        assert result is answer
        db.insert_rows.assert_called_once()
        assert db.insert_rows.call_args[0][0] == "answers"

    def test_get_answers_no_filters(self, qs, db):
        db.execute.return_value = []
        qs.get_answers()
        sql = db.execute.call_args[0][0]
        assert "WHERE" not in sql

    def test_get_answers_by_run(self, qs, db):
        db.execute.return_value = []
        qs.get_answers(run_id=RUN_ID)
        sql = db.execute.call_args[0][0]
        assert "run_id = {run_id:UUID}" in sql

    def test_get_answers_by_brand(self, qs, db):
        db.execute.return_value = []
        qs.get_answers(brand_id=BRAND_ID)
        sql = db.execute.call_args[0][0]
        assert "brand_id = {brand_id:UUID}" in sql

    def test_get_answers_combined(self, qs, db):
        db.execute.return_value = []
        qs.get_answers(run_id=RUN_ID, brand_id=BRAND_ID)
        sql = db.execute.call_args[0][0]
        assert "run_id" in sql
        assert "brand_id" in sql
