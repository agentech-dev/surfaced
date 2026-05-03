"""Tests for data models."""

from datetime import datetime
from uuid import UUID, uuid4

from surfaced.models.brand import Brand
from surfaced.models.prompt import Prompt
from surfaced.models.answer import Answer
from surfaced.models.provider import Provider
from surfaced.models.run import Run
from surfaced.cli.prompts import _format_prompt


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
        category="crm",
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
        category="crm",
        brand_id=uuid4(),
    )
    assert prompt.render({"something": "else"}) == "What are the best CRM tools?"


def test_prompt_branded_defaults_false():
    prompt = Prompt(
        text="What are the best CRM tools?",
        category="crm",
        brand_id=uuid4(),
    )
    assert prompt.branded is False


def test_prompt_recommendation_enabled_defaults_true():
    prompt = Prompt(
        text="What are the best CRM tools?",
        category="crm",
        brand_id=uuid4(),
    )
    assert prompt.recommendation_enabled is True


def test_prompt_from_dict_branded():
    now = datetime.now()
    prompt = Prompt.from_dict({
        "id": uuid4(),
        "text": "How does Acme compare to Globex?",
        "category": "crm",
        "brand_id": uuid4(),
        "branded": True,
        "recommendation_enabled": False,
        "created_at": now,
        "updated_at": now,
    })
    assert prompt.branded is True
    assert prompt.recommendation_enabled is False


def test_prompt_format_includes_branded():
    prompt = Prompt(
        text="How does Acme compare to Globex?",
        category="crm",
        brand_id=uuid4(),
        branded=True,
    )
    assert '"branded": true' in _format_prompt(prompt, "json")
    assert '"recommendation_enabled": true' in _format_prompt(prompt, "json")
    assert "Branded:   yes" in _format_prompt(prompt, "text")
    assert "Recs:      enabled" in _format_prompt(prompt, "text")


def test_provider_from_dict():
    data = {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "Claude API",
        "provider": "anthropic",
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


def test_answer_from_dict():
    now = datetime.now()
    data = {
        "id": uuid4(),
        "run_id": uuid4(),
        "prompt_id": uuid4(),
        "provider_id": uuid4(),
        "brand_id": uuid4(),
        "prompt_text": "Test prompt",
        "prompt_category": "crm",
        "prompt_branded": 1,
        "response_text": "Test response",
        "model": "claude-sonnet-4-6",
        "provider_name": "test",
        "latency_ms": 500,
        "input_tokens": 100,
        "output_tokens": 200,
        "status": "success",
        "error_message": "",
        "brand_mentioned": 1,
        "recommendation_status": "recommended",
        "competitors_mentioned": ["Globex"],
        "created_at": now,
    }
    answer = Answer.from_dict(data)
    assert answer.status == "success"
    assert answer.brand_mentioned == 1
    assert answer.recommendation_status == "recommended"
    assert answer.prompt_branded is True


def test_answer_recommendation_status_defaults_not_mentioned():
    answer = Answer(
        run_id=uuid4(),
        prompt_id=uuid4(),
        provider_id=uuid4(),
        brand_id=uuid4(),
        prompt_text="Test prompt",
        prompt_category="crm",
        response_text="Test response",
        model="claude-sonnet-4-6",
        provider_name="test",
        latency_ms=500,
        status="success",
    )

    assert answer.recommendation_status == "not_mentioned"
