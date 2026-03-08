"""Tests for data models."""

from datetime import datetime
from uuid import UUID, uuid4

from surfaced.models.brand import Brand
from surfaced.models.prompt import Prompt
from surfaced.models.prompt_run import PromptRun
from surfaced.models.provider import Provider
from surfaced.models.run import Run


def test_brand_from_dict():
    data = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Acme",
        "domain": "acme.com",
        "description": "Test brand",
        "aliases": ["ACME", "Acme Corp"],
        "competitors": ["Globex"],
        "is_active": 1,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }
    brand = Brand.from_dict(data)
    assert brand.name == "Acme"
    assert brand.domain == "acme.com"
    assert brand.aliases == ["ACME", "Acme Corp"]
    assert isinstance(brand.id, UUID)


def test_prompt_template_rendering():
    prompt = Prompt(
        text="What are the best {{product_type}} tools for {{industry}}?",
        category="brand_query",
        brand_id=uuid4(),
        is_template=1,
        variables=["product_type", "industry"],
    )
    rendered = prompt.render({"product_type": "CRM", "industry": "healthcare"})
    assert rendered == "What are the best CRM tools for healthcare?"


def test_prompt_extract_variables():
    text = "Tell me about {{brand}} in the {{market}} market"
    variables = Prompt.extract_variables(text)
    assert variables == ["brand", "market"]


def test_prompt_non_template_render():
    prompt = Prompt(
        text="What are the best CRM tools?",
        category="brand_query",
        brand_id=uuid4(),
    )
    assert prompt.render({"something": "else"}) == "What are the best CRM tools?"


def test_provider_from_dict():
    data = {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "Claude API",
        "provider_type": "anthropic_api",
        "execution_mode": "api",
        "model": "claude-sonnet-4-6",
        "config": "{}",
        "rate_limit_rpm": 60,
        "is_active": 1,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    provider = Provider.from_dict(data)
    assert provider.name == "Claude API"
    assert provider.execution_mode == "api"


def test_run_from_dict():
    now = datetime.now()
    data = {
        "id": uuid4(),
        "name": "Test Run",
        "status": "running",
        "filters": "{}",
        "total_prompts": 10,
        "completed_prompts": 5,
        "started_at": now,
        "finished_at": None,
        "created_at": now,
        "updated_at": now,
    }
    run = Run.from_dict(data)
    assert run.name == "Test Run"
    assert run.total_prompts == 10


def test_prompt_run_from_dict():
    now = datetime.now()
    data = {
        "id": uuid4(),
        "run_id": uuid4(),
        "prompt_id": uuid4(),
        "provider_id": uuid4(),
        "brand_id": uuid4(),
        "prompt_text": "Test prompt",
        "prompt_category": "brand_query",
        "response_text": "Test response",
        "model": "claude-sonnet-4-6",
        "provider_name": "test",
        "latency_ms": 500,
        "input_tokens": 100,
        "output_tokens": 200,
        "status": "success",
        "error_message": "",
        "brand_mentioned": 1,
        "competitors_mentioned": ["Globex"],
        "created_at": now,
    }
    run = PromptRun.from_dict(data)
    assert run.status == "success"
    assert run.brand_mentioned == 1
