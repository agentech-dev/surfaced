"""Tests for the execution engine runner."""

from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import UUID, uuid4

import pytest

from surfaced.db.client import DBClient
from surfaced.db.queries import QueryService
from surfaced.engine.runner import execute_run, MAX_RETRIES
from surfaced.models.brand import Brand
from surfaced.models.prompt import Prompt
from surfaced.models.provider import Provider
from surfaced.models.run import Run
from surfaced.providers.base import ProviderResponse

BRAND_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
PROVIDER_ID = UUID("550e8400-e29b-41d4-a716-446655440001")
PROMPT_ID = UUID("550e8400-e29b-41d4-a716-446655440002")
NOW = datetime(2024, 6, 15, 12, 0, 0)


def _make_prompt(prompt_id=None, brand_id=None):
    return Prompt(
        id=prompt_id or PROMPT_ID,
        text="What are the best tools?",
        category="brand_query",
        brand_id=brand_id or BRAND_ID,
        created_at=NOW, updated_at=NOW,
    )


def _make_provider_record(provider_id=None):
    return Provider(
        id=provider_id or PROVIDER_ID,
        name="Claude API", provider="anthropic",
        execution_mode="api", model="claude-sonnet-4-6",
        rate_limit_rpm=0,  # No rate limiting in tests
        created_at=NOW, updated_at=NOW,
    )


def _make_brand(brand_id=None):
    return Brand(
        id=brand_id or BRAND_ID, name="Acme",
        aliases=["ACME"], competitors=["Globex"],
        created_at=NOW, updated_at=NOW,
    )


def _make_response(text="Acme is great."):
    return ProviderResponse(
        text=text, model="claude-sonnet-4-6",
        input_tokens=10, output_tokens=20, latency_ms=500,
    )


@pytest.fixture
def mock_qs():
    db = MagicMock(spec=DBClient)
    qs = QueryService(db=db)
    return qs


def test_no_prompts_returns_none(mock_qs):
    mock_qs.get_prompts = MagicMock(return_value=[])
    result = execute_run(mock_qs)
    assert result is None


def test_no_providers_returns_none(mock_qs):
    mock_qs.get_prompts = MagicMock(return_value=[_make_prompt()])
    mock_qs.get_providers = MagicMock(return_value=[])
    result = execute_run(mock_qs)
    assert result is None


@patch("surfaced.engine.runner.get_provider")
@patch("surfaced.engine.runner.time.sleep")
def test_dry_run_no_answers(mock_sleep, mock_get_provider, mock_qs):
    mock_qs.get_prompts = MagicMock(return_value=[_make_prompt()])
    mock_qs.get_providers = MagicMock(return_value=[_make_provider_record()])
    result = execute_run(mock_qs, dry_run=True)
    assert result is None
    mock_get_provider.assert_not_called()
    mock_qs.db.insert_rows.assert_not_called()


@patch("surfaced.engine.runner.get_provider")
@patch("surfaced.engine.runner.time.sleep")
def test_success_run(mock_sleep, mock_get_provider, mock_qs):
    prompt = _make_prompt()
    prov_record = _make_provider_record()
    brand = _make_brand()

    mock_qs.get_prompts = MagicMock(return_value=[prompt])
    mock_qs.get_providers = MagicMock(return_value=[prov_record])
    mock_qs.get_brand = MagicMock(return_value=brand)
    mock_qs.insert_run = MagicMock(side_effect=lambda r: r)
    mock_qs.insert_answer = MagicMock(side_effect=lambda a: a)
    mock_qs.update_run = MagicMock(side_effect=lambda r: r)

    mock_ai = MagicMock()
    mock_ai.execute.return_value = _make_response("Acme is great.")
    mock_get_provider.return_value = mock_ai

    result = execute_run(mock_qs)

    assert result is not None
    assert result.status == "completed"
    assert result.completed_prompts == 1
    mock_qs.insert_answer.assert_called_once()
    answer = mock_qs.insert_answer.call_args[0][0]
    assert answer.status == "success"
    assert answer.brand_mentioned == 1


@patch("surfaced.engine.runner.get_provider")
@patch("surfaced.engine.runner.time.sleep")
def test_brand_not_mentioned(mock_sleep, mock_get_provider, mock_qs):
    prompt = _make_prompt()
    prov_record = _make_provider_record()
    brand = _make_brand()

    mock_qs.get_prompts = MagicMock(return_value=[prompt])
    mock_qs.get_providers = MagicMock(return_value=[prov_record])
    mock_qs.get_brand = MagicMock(return_value=brand)
    mock_qs.insert_run = MagicMock(side_effect=lambda r: r)
    mock_qs.insert_answer = MagicMock(side_effect=lambda a: a)
    mock_qs.update_run = MagicMock(side_effect=lambda r: r)

    mock_ai = MagicMock()
    mock_ai.execute.return_value = _make_response("Some other tool is best.")
    mock_get_provider.return_value = mock_ai

    result = execute_run(mock_qs)

    answer = mock_qs.insert_answer.call_args[0][0]
    assert answer.brand_mentioned == 0
    assert answer.competitors_mentioned == []


@patch("surfaced.engine.runner.get_provider")
@patch("surfaced.engine.runner.time.sleep")
def test_competitor_detection(mock_sleep, mock_get_provider, mock_qs):
    prompt = _make_prompt()
    prov_record = _make_provider_record()
    brand = _make_brand()

    mock_qs.get_prompts = MagicMock(return_value=[prompt])
    mock_qs.get_providers = MagicMock(return_value=[prov_record])
    mock_qs.get_brand = MagicMock(return_value=brand)
    mock_qs.insert_run = MagicMock(side_effect=lambda r: r)
    mock_qs.insert_answer = MagicMock(side_effect=lambda a: a)
    mock_qs.update_run = MagicMock(side_effect=lambda r: r)

    mock_ai = MagicMock()
    mock_ai.execute.return_value = _make_response("Globex is a strong competitor.")
    mock_get_provider.return_value = mock_ai

    execute_run(mock_qs)
    answer = mock_qs.insert_answer.call_args[0][0]
    assert "Globex" in answer.competitors_mentioned


@patch("surfaced.engine.runner.get_provider")
@patch("surfaced.engine.runner.time.sleep")
def test_retry_then_succeed(mock_sleep, mock_get_provider, mock_qs):
    prompt = _make_prompt()
    prov_record = _make_provider_record()

    mock_qs.get_prompts = MagicMock(return_value=[prompt])
    mock_qs.get_providers = MagicMock(return_value=[prov_record])
    mock_qs.get_brand = MagicMock(return_value=_make_brand())
    mock_qs.insert_run = MagicMock(side_effect=lambda r: r)
    mock_qs.insert_answer = MagicMock(side_effect=lambda a: a)
    mock_qs.update_run = MagicMock(side_effect=lambda r: r)

    mock_ai = MagicMock()
    mock_ai.execute.side_effect = [
        RuntimeError("temporary error"),
        _make_response("OK"),
    ]
    mock_get_provider.return_value = mock_ai

    result = execute_run(mock_qs)
    assert result.status == "completed"
    assert result.completed_prompts == 1
    answer = mock_qs.insert_answer.call_args[0][0]
    assert answer.status == "success"


@patch("surfaced.engine.runner.get_provider")
@patch("surfaced.engine.runner.time.sleep")
def test_retry_exhausted(mock_sleep, mock_get_provider, mock_qs):
    prompt = _make_prompt()
    prov_record = _make_provider_record()

    mock_qs.get_prompts = MagicMock(return_value=[prompt])
    mock_qs.get_providers = MagicMock(return_value=[prov_record])
    mock_qs.get_brand = MagicMock(return_value=_make_brand())
    mock_qs.insert_run = MagicMock(side_effect=lambda r: r)
    mock_qs.insert_answer = MagicMock(side_effect=lambda a: a)
    mock_qs.update_run = MagicMock(side_effect=lambda r: r)

    mock_ai = MagicMock()
    mock_ai.execute.side_effect = RuntimeError("persistent error")
    mock_get_provider.return_value = mock_ai

    result = execute_run(mock_qs)
    assert result.status == "failed"
    answer = mock_qs.insert_answer.call_args[0][0]
    assert answer.status == "error"
    assert "persistent error" in answer.error_message


@patch("surfaced.engine.runner.get_provider")
@patch("surfaced.engine.runner.time.sleep")
def test_multiple_prompts_and_providers(mock_sleep, mock_get_provider, mock_qs):
    prompts = [_make_prompt(prompt_id=uuid4()) for _ in range(2)]
    providers = [_make_provider_record(provider_id=uuid4()) for _ in range(2)]

    mock_qs.get_prompts = MagicMock(return_value=prompts)
    mock_qs.get_providers = MagicMock(return_value=providers)
    mock_qs.get_brand = MagicMock(return_value=_make_brand())
    mock_qs.insert_run = MagicMock(side_effect=lambda r: r)
    mock_qs.insert_answer = MagicMock(side_effect=lambda a: a)
    mock_qs.update_run = MagicMock(side_effect=lambda r: r)

    mock_ai = MagicMock()
    mock_ai.execute.return_value = _make_response()
    mock_get_provider.return_value = mock_ai

    result = execute_run(mock_qs)
    assert result.completed_prompts == 4  # 2 prompts x 2 providers
    assert mock_qs.insert_answer.call_count == 4


@patch("surfaced.engine.runner.get_provider")
def test_provider_init_failure_exits(mock_get_provider, mock_qs):
    mock_qs.get_prompts = MagicMock(return_value=[_make_prompt()])
    mock_qs.get_providers = MagicMock(return_value=[_make_provider_record()])

    mock_get_provider.side_effect = RuntimeError("Missing API key")

    with pytest.raises(SystemExit):
        execute_run(mock_qs)


@patch("surfaced.engine.runner.get_provider")
@patch("surfaced.engine.runner.time.sleep")
def test_no_history_flag_passed(mock_sleep, mock_get_provider, mock_qs):
    prompt = _make_prompt()
    prov_record = _make_provider_record()

    mock_qs.get_prompts = MagicMock(return_value=[prompt])
    mock_qs.get_providers = MagicMock(return_value=[prov_record])
    mock_qs.get_brand = MagicMock(return_value=_make_brand())
    mock_qs.insert_run = MagicMock(side_effect=lambda r: r)
    mock_qs.insert_answer = MagicMock(side_effect=lambda a: a)
    mock_qs.update_run = MagicMock(side_effect=lambda r: r)

    mock_ai = MagicMock()
    mock_ai.execute.return_value = _make_response()
    mock_get_provider.return_value = mock_ai

    execute_run(mock_qs, no_history=True)
    mock_ai.execute.assert_called_once()
    _, kwargs = mock_ai.execute.call_args
    assert kwargs.get("no_history") is True


@patch("surfaced.engine.runner.get_provider")
@patch("surfaced.engine.runner.time.sleep")
def test_no_brand_found_still_succeeds(mock_sleep, mock_get_provider, mock_qs):
    """When brand lookup returns None, brand_mentioned should be 0."""
    prompt = _make_prompt()
    prov_record = _make_provider_record()

    mock_qs.get_prompts = MagicMock(return_value=[prompt])
    mock_qs.get_providers = MagicMock(return_value=[prov_record])
    mock_qs.get_brand = MagicMock(return_value=None)
    mock_qs.insert_run = MagicMock(side_effect=lambda r: r)
    mock_qs.insert_answer = MagicMock(side_effect=lambda a: a)
    mock_qs.update_run = MagicMock(side_effect=lambda r: r)

    mock_ai = MagicMock()
    mock_ai.execute.return_value = _make_response("Acme is great")
    mock_get_provider.return_value = mock_ai

    result = execute_run(mock_qs)
    assert result.status == "completed"
    answer = mock_qs.insert_answer.call_args[0][0]
    assert answer.brand_mentioned == 0
