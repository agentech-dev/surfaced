"""Tests for data models."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from surfaced.models.brand import Brand
from surfaced.models.prompt import Prompt
from surfaced.models.answer import Answer
from surfaced.models.provider import Provider
from surfaced.models.run import Run


# --- Brand ---

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


def test_brand_from_dict_with_datetime_objects():
    now = datetime.now()
    data = {
        "id": uuid4(),
        "name": "Test",
        "domain": "",
        "created_at": now,
        "updated_at": now,
    }
    brand = Brand.from_dict(data)
    assert brand.created_at is now


def test_brand_defaults():
    brand = Brand(name="Minimal")
    assert brand.domain == ""
    assert brand.description == ""
    assert brand.aliases == []
    assert brand.competitors == []
    assert brand.is_active == 1
    assert isinstance(brand.id, UUID)
    assert isinstance(brand.created_at, datetime)


def test_brand_from_dict_missing_optional_fields():
    data = {
        "id": uuid4(),
        "name": "Sparse",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    brand = Brand.from_dict(data)
    assert brand.domain == ""
    assert brand.aliases == []
    assert brand.competitors == []


# --- Provider ---

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


def test_provider_defaults():
    provider = Provider(name="P", provider="anthropic", execution_mode="api", model="m")
    assert provider.config == "{}"
    assert provider.rate_limit_rpm == 60
    assert provider.is_active == 1


def test_provider_from_dict_string_dates():
    data = {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "Test",
        "provider": "openai",
        "execution_mode": "cli",
        "model": "codex",
        "created_at": "2024-06-01T10:00:00",
        "updated_at": "2024-06-01T10:00:00",
    }
    provider = Provider.from_dict(data)
    assert provider.created_at == datetime(2024, 6, 1, 10, 0, 0)


# --- Prompt ---

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


def test_prompt_extract_no_variables():
    assert Prompt.extract_variables("No placeholders here") == []


def test_prompt_render_partial_variables():
    prompt = Prompt(
        text="Use {{tool}} in {{domain}}",
        category="brand_query",
        brand_id=uuid4(),
        is_template=1,
        variables=["tool", "domain"],
    )
    rendered = prompt.render({"tool": "Acme"})
    assert rendered == "Use Acme in {{domain}}"


def test_prompt_render_with_none_variables():
    prompt = Prompt(
        text="Hello {{name}}",
        category="brand_query",
        brand_id=uuid4(),
        is_template=1,
        variables=["name"],
    )
    assert prompt.render(None) == "Hello {{name}}"


def test_prompt_from_dict_string_dates():
    data = {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "text": "test",
        "category": "brand_query",
        "brand_id": "550e8400-e29b-41d4-a716-446655440000",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }
    prompt = Prompt.from_dict(data)
    assert isinstance(prompt.created_at, datetime)
    assert isinstance(prompt.brand_id, UUID)


# --- Run ---

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
    assert run.finished_at is None


def test_run_defaults():
    run = Run(name="R")
    assert run.status == "running"
    assert run.filters == "{}"
    assert run.total_prompts == 0
    assert run.completed_prompts == 0
    assert run.finished_at is None


def test_run_from_dict_string_finished_at():
    data = {
        "id": uuid4(),
        "name": "Done",
        "status": "completed",
        "started_at": datetime.now(),
        "finished_at": "2024-06-15T12:00:00",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    run = Run.from_dict(data)
    assert run.finished_at == datetime(2024, 6, 15, 12, 0, 0)


# --- Answer ---

def test_answer_from_dict():
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
    answer = Answer.from_dict(data)
    assert answer.status == "success"
    assert answer.brand_mentioned == 1


def test_answer_defaults():
    uid = uuid4()
    answer = Answer(
        run_id=uid, prompt_id=uid, provider_id=uid, brand_id=uid,
        prompt_text="t", prompt_category="brand_query", response_text="r",
        model="m", provider_name="p", latency_ms=0, status="success",
    )
    assert answer.input_tokens == 0
    assert answer.output_tokens == 0
    assert answer.error_message == ""
    assert answer.brand_mentioned == 0
    assert answer.competitors_mentioned == []


def test_answer_from_dict_missing_optional():
    uid = uuid4()
    data = {
        "id": uid, "run_id": uid, "prompt_id": uid, "provider_id": uid,
        "brand_id": uid, "prompt_text": "t", "prompt_category": "c",
        "model": "m", "provider_name": "p", "status": "error",
        "created_at": datetime.now(),
    }
    answer = Answer.from_dict(data)
    assert answer.response_text == ""
    assert answer.latency_ms == 0
    assert answer.error_message == ""
