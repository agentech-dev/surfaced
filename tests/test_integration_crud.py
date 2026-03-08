"""Integration tests: CRUD operations with real ClickHouse."""

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


# --- Brands ---

class TestBrandCRUD:
    def test_insert_and_get(self, real_qs):
        brand_id = uuid4()
        brand = Brand(id=brand_id, name=f"Test_{brand_id.hex[:8]}",
                      domain="test.com", aliases=["T"], competitors=["C"])
        real_qs.insert_brand(brand)
        fetched = real_qs.get_brand(brand_id)
        assert fetched is not None
        assert fetched.name == brand.name
        assert fetched.aliases == ["T"]

    def test_get_by_name(self, real_qs):
        brand_id = uuid4()
        name = f"ByName_{brand_id.hex[:8]}"
        brand = Brand(id=brand_id, name=name)
        real_qs.insert_brand(brand)
        fetched = real_qs.get_brand_by_name(name)
        assert fetched is not None
        assert fetched.id == brand_id

    def test_update(self, real_qs):
        brand_id = uuid4()
        brand = Brand(id=brand_id, name=f"Update_{brand_id.hex[:8]}")
        real_qs.insert_brand(brand)
        brand.domain = "updated.com"
        real_qs.update_brand(brand)
        fetched = real_qs.get_brand(brand_id)
        assert fetched.domain == "updated.com"

    def test_soft_delete(self, real_qs):
        brand_id = uuid4()
        brand = Brand(id=brand_id, name=f"Delete_{brand_id.hex[:8]}")
        real_qs.insert_brand(brand)
        real_qs.delete_brand(brand_id)
        fetched = real_qs.get_brand(brand_id)
        assert fetched.is_active == 0

    def test_list_active_only(self, real_qs):
        brand_id = uuid4()
        name = f"Active_{brand_id.hex[:8]}"
        brand = Brand(id=brand_id, name=name)
        real_qs.insert_brand(brand)
        brands = real_qs.get_brands(active_only=True)
        names = [b.name for b in brands]
        assert name in names


# --- Providers ---

class TestProviderCRUD:
    def test_insert_and_get(self, real_qs):
        prov_id = uuid4()
        provider = Provider(
            id=prov_id, name=f"Prov_{prov_id.hex[:8]}",
            provider="anthropic", execution_mode="api",
            model="claude-sonnet-4-6",
        )
        real_qs.insert_provider(provider)
        fetched = real_qs.get_provider(prov_id)
        assert fetched is not None
        assert fetched.model == "claude-sonnet-4-6"

    def test_get_by_name(self, real_qs):
        prov_id = uuid4()
        name = f"ProvName_{prov_id.hex[:8]}"
        provider = Provider(
            id=prov_id, name=name, provider="openai",
            execution_mode="cli", model="codex",
        )
        real_qs.insert_provider(provider)
        fetched = real_qs.get_provider_by_name(name)
        assert fetched is not None

    def test_delete(self, real_qs):
        prov_id = uuid4()
        provider = Provider(
            id=prov_id, name=f"Del_{prov_id.hex[:8]}",
            provider="google", execution_mode="api",
            model="gemini-3.1-pro-preview",
        )
        real_qs.insert_provider(provider)
        real_qs.delete_provider(prov_id)
        fetched = real_qs.get_provider(prov_id)
        assert fetched.is_active == 0


# --- Prompts ---

class TestPromptCRUD:
    def test_insert_and_get(self, real_qs):
        brand_id = uuid4()
        brand = Brand(id=brand_id, name=f"PBrand_{brand_id.hex[:8]}")
        real_qs.insert_brand(brand)

        prompt_id = uuid4()
        prompt = Prompt(
            id=prompt_id, text="Test prompt",
            category="brand_query", brand_id=brand_id,
            tags=["daily", "weekly"],
        )
        real_qs.insert_prompt(prompt)
        fetched = real_qs.get_prompt(prompt_id)
        assert fetched is not None
        assert fetched.text == "Test prompt"
        assert fetched.tags == ["daily", "weekly"]

    def test_filter_by_category(self, real_qs):
        brand_id = uuid4()
        real_qs.insert_brand(Brand(id=brand_id, name=f"FC_{brand_id.hex[:8]}"))

        prompt = Prompt(
            id=uuid4(), text="Cat filter", category="feature_query",
            brand_id=brand_id,
        )
        real_qs.insert_prompt(prompt)
        results = real_qs.get_prompts(category="feature_query", brand_id=brand_id)
        assert any(p.text == "Cat filter" for p in results)

    def test_filter_by_tag(self, real_qs):
        brand_id = uuid4()
        real_qs.insert_brand(Brand(id=brand_id, name=f"FT_{brand_id.hex[:8]}"))

        prompt = Prompt(
            id=uuid4(), text="Tag filter", category="brand_query",
            brand_id=brand_id, tags=["monthly"],
        )
        real_qs.insert_prompt(prompt)
        results = real_qs.get_prompts(tag="monthly", brand_id=brand_id)
        assert any(p.text == "Tag filter" for p in results)

    def test_update(self, real_qs):
        brand_id = uuid4()
        real_qs.insert_brand(Brand(id=brand_id, name=f"PU_{brand_id.hex[:8]}"))

        prompt_id = uuid4()
        prompt = Prompt(
            id=prompt_id, text="Original", category="brand_query",
            brand_id=brand_id,
        )
        real_qs.insert_prompt(prompt)
        prompt.text = "Updated"
        real_qs.update_prompt(prompt)
        fetched = real_qs.get_prompt(prompt_id)
        assert fetched.text == "Updated"

    def test_delete(self, real_qs):
        brand_id = uuid4()
        real_qs.insert_brand(Brand(id=brand_id, name=f"PD_{brand_id.hex[:8]}"))

        prompt_id = uuid4()
        prompt = Prompt(
            id=prompt_id, text="To delete", category="brand_query",
            brand_id=brand_id,
        )
        real_qs.insert_prompt(prompt)
        real_qs.delete_prompt(prompt_id)
        fetched = real_qs.get_prompt(prompt_id)
        assert fetched.is_active == 0


# --- Runs ---

class TestRunCRUD:
    def test_insert_and_get(self, real_qs):
        run_id = uuid4()
        run = Run(id=run_id, name=f"Run_{run_id.hex[:8]}")
        real_qs.insert_run(run)
        fetched = real_qs.get_run(run_id)
        assert fetched is not None
        assert fetched.status == "running"

    def test_list(self, real_qs):
        run_id = uuid4()
        run = Run(id=run_id, name=f"List_{run_id.hex[:8]}")
        real_qs.insert_run(run)
        runs = real_qs.get_runs(limit=100)
        assert any(r.id == run_id for r in runs)

    def test_update(self, real_qs):
        run_id = uuid4()
        run = Run(id=run_id, name=f"UpdR_{run_id.hex[:8]}")
        real_qs.insert_run(run)
        run.status = "completed"
        run.finished_at = datetime.now()
        real_qs.update_run(run)
        fetched = real_qs.get_run(run_id)
        assert fetched.status == "completed"


# --- Answers ---

class TestAnswerCRUD:
    def test_insert_and_get(self, real_qs):
        # Setup parent records
        brand_id = uuid4()
        real_qs.insert_brand(Brand(id=brand_id, name=f"AB_{brand_id.hex[:8]}"))
        prov_id = uuid4()
        real_qs.insert_provider(Provider(
            id=prov_id, name=f"AP_{prov_id.hex[:8]}",
            provider="anthropic", execution_mode="api", model="m",
        ))
        run_id = uuid4()
        real_qs.insert_run(Run(id=run_id, name=f"AR_{run_id.hex[:8]}"))
        prompt_id = uuid4()
        real_qs.insert_prompt(Prompt(
            id=prompt_id, text="a", category="brand_query", brand_id=brand_id,
        ))

        answer_id = uuid4()
        answer = Answer(
            id=answer_id, run_id=run_id, prompt_id=prompt_id,
            provider_id=prov_id, brand_id=brand_id,
            prompt_text="a", prompt_category="brand_query",
            response_text="r", model="m", provider_name="p",
            latency_ms=100, status="success", brand_mentioned=1,
        )
        real_qs.insert_answer(answer)
        answers = real_qs.get_answers(run_id=run_id)
        assert any(a.id == answer_id for a in answers)

    def test_filter_by_brand(self, real_qs):
        brand_id = uuid4()
        real_qs.insert_brand(Brand(id=brand_id, name=f"AF_{brand_id.hex[:8]}"))
        run_id = uuid4()
        real_qs.insert_run(Run(id=run_id, name=f"AFR_{run_id.hex[:8]}"))
        prompt_id = uuid4()
        real_qs.insert_prompt(Prompt(
            id=prompt_id, text="b", category="brand_query", brand_id=brand_id,
        ))
        prov_id = uuid4()
        real_qs.insert_provider(Provider(
            id=prov_id, name=f"AFP_{prov_id.hex[:8]}",
            provider="openai", execution_mode="api", model="m",
        ))

        answer = Answer(
            id=uuid4(), run_id=run_id, prompt_id=prompt_id,
            provider_id=prov_id, brand_id=brand_id,
            prompt_text="b", prompt_category="brand_query",
            response_text="r", model="m", provider_name="p",
            latency_ms=50, status="success",
        )
        real_qs.insert_answer(answer)
        answers = real_qs.get_answers(brand_id=brand_id)
        assert len(answers) >= 1
        assert all(a.brand_id == brand_id for a in answers)
