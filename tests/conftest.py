"""Pytest configuration and fixtures."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from click.testing import CliRunner

from surfaced.db.client import DBClient
from surfaced.db.queries import QueryService
from surfaced.models.answer import Answer
from surfaced.models.brand import Brand
from surfaced.models.prompt import Prompt
from surfaced.models.provider import Provider
from surfaced.models.run import Run


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires running ClickHouse server")


# --- Deterministic IDs ---

BRAND_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
PROVIDER_ID = UUID("550e8400-e29b-41d4-a716-446655440001")
PROMPT_ID = UUID("550e8400-e29b-41d4-a716-446655440002")
RUN_ID = UUID("550e8400-e29b-41d4-a716-446655440003")
ANSWER_ID = UUID("550e8400-e29b-41d4-a716-446655440004")

NOW = datetime(2024, 6, 15, 12, 0, 0)


# --- Sample model fixtures ---

@pytest.fixture
def sample_brand():
    return Brand(
        id=BRAND_ID,
        name="Acme",
        domain="acme.com",
        description="Test brand",
        aliases=["ACME", "Acme Corp"],
        competitors=["Globex", "Initech"],
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def sample_provider():
    return Provider(
        id=PROVIDER_ID,
        name="Claude API",
        provider="anthropic",
        execution_mode="api",
        model="claude-sonnet-4-6",
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def sample_prompt():
    return Prompt(
        id=PROMPT_ID,
        text="What are the best tools for project management?",
        category="brand_query",
        brand_id=BRAND_ID,
        tags=["daily"],
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def sample_run():
    return Run(
        id=RUN_ID,
        name="Test Run",
        status="completed",
        total_prompts=5,
        completed_prompts=5,
        started_at=NOW,
        finished_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def sample_answer():
    return Answer(
        id=ANSWER_ID,
        run_id=RUN_ID,
        prompt_id=PROMPT_ID,
        provider_id=PROVIDER_ID,
        brand_id=BRAND_ID,
        prompt_text="What are the best tools?",
        prompt_category="brand_query",
        response_text="Acme is a great tool.",
        model="claude-sonnet-4-6",
        provider_name="Claude API",
        latency_ms=500,
        input_tokens=100,
        output_tokens=200,
        status="success",
        brand_mentioned=1,
        competitors_mentioned=["Globex"],
        created_at=NOW,
    )


# --- Mock fixtures ---

@pytest.fixture
def mock_db():
    return MagicMock(spec=DBClient)


@pytest.fixture
def mock_qs(mock_db):
    return QueryService(db=mock_db)


@pytest.fixture
def cli_runner():
    return CliRunner()


# --- Integration helpers ---

def _clickhouse_available():
    """Check if ClickHouse is reachable on localhost:8123."""
    import socket
    try:
        s = socket.create_connection(("localhost", 8123), timeout=1)
        s.close()
        return True
    except OSError:
        return False


requires_clickhouse = pytest.mark.skipif(
    not _clickhouse_available(),
    reason="ClickHouse not available on localhost:8123",
)


@pytest.fixture
def real_db():
    """Real DBClient for integration tests."""
    return DBClient(host="localhost", port=8123)


@pytest.fixture
def real_qs(real_db):
    """Real QueryService for integration tests."""
    return QueryService(db=real_db)
