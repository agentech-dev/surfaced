"""Tests for the provider registry and provider implementations."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from surfaced.models.provider import Provider
from surfaced.providers.registry import PROVIDER_MAP, get_provider
from surfaced.providers.anthropic_api import AnthropicAPIProvider
from surfaced.providers.openai_api import OpenAIAPIProvider
from surfaced.providers.gemini_api import GeminiAPIProvider
from surfaced.providers.claude_cli import ClaudeCLIProvider
from surfaced.providers.codex_cli import CodexCLIProvider
from surfaced.providers.gemini_cli import GeminiCLIProvider
from surfaced.providers.base import ProviderResponse


def _make_provider(vendor, mode, model="test-model"):
    return Provider(
        id=uuid4(), name=f"{vendor}_{mode}",
        provider=vendor, execution_mode=mode, model=model,
    )


# --- Registry mapping ---

@pytest.mark.parametrize("vendor,mode,expected_cls", [
    ("anthropic", "api", AnthropicAPIProvider),
    ("openai", "api", OpenAIAPIProvider),
    ("google", "api", GeminiAPIProvider),
    ("anthropic", "cli", ClaudeCLIProvider),
    ("openai", "cli", CodexCLIProvider),
    ("google", "cli", GeminiCLIProvider),
])
def test_provider_map_contains(vendor, mode, expected_cls):
    assert PROVIDER_MAP[(vendor, mode)] is expected_cls


def test_unknown_provider_raises():
    provider = _make_provider("unknown", "api")
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider(provider)


# --- API providers: init without key raises ---

def test_anthropic_api_no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicAPIProvider(model="claude-sonnet-4-6")


def test_openai_api_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIAPIProvider(model="gpt-5.2")


def test_gemini_api_no_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        GeminiAPIProvider(model="gemini-3.1-pro-preview")


# --- API providers: execute with mocked SDK ---

def test_anthropic_api_execute(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("surfaced.providers.anthropic_api.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Acme is great."

        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.model = "claude-sonnet-4-6"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_client.messages.create.return_value = mock_response

        provider = AnthropicAPIProvider(model="claude-sonnet-4-6")
        result = provider.execute("test prompt")

        assert isinstance(result, ProviderResponse)
        assert result.text == "Acme is great."
        assert result.model == "claude-sonnet-4-6"
        assert result.input_tokens == 10


def test_openai_api_execute(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with patch("surfaced.providers.openai_api.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "GPT response"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-5.2"
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 25
        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAIAPIProvider(model="gpt-5.2")
        result = provider.execute("test prompt")

        assert result.text == "GPT response"
        assert result.input_tokens == 15


# --- CLI providers: execute with mocked subprocess ---

def test_claude_cli_execute():
    import json
    mock_output = json.dumps({
        "result": "Claude CLI output",
        "model": "claude-sonnet-4-6",
        "input_tokens": 5,
        "output_tokens": 10,
    })
    with patch("surfaced.providers.claude_cli.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout=mock_output, stderr=""
        )
        provider = ClaudeCLIProvider(model="claude-sonnet-4-6")
        result = provider.execute("hello")

        assert result.text == "Claude CLI output"
        assert result.model == "claude-sonnet-4-6"
        cmd = mock_run.call_args[0][0]
        assert "claude" in cmd
        assert "-p" in cmd


def test_claude_cli_no_history():
    import json
    mock_output = json.dumps({"result": "ok", "model": "m"})
    with patch("surfaced.providers.claude_cli.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr="")
        provider = ClaudeCLIProvider(model="m")
        provider.execute("hello", no_history=True)
        cmd = mock_run.call_args[0][0]
        assert "--no-session-persistence" in cmd


def test_claude_cli_error():
    with patch("surfaced.providers.claude_cli.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="fail")
        provider = ClaudeCLIProvider()
        with pytest.raises(RuntimeError, match="Claude CLI error"):
            provider.execute("hello")


def test_codex_cli_execute():
    import json
    lines = [
        json.dumps({
            "type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": "Codex output"}],
            "model": "codex", "usage": {"input_tokens": 3, "output_tokens": 7},
        })
    ]
    with patch("surfaced.providers.codex_cli.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="\n".join(lines), stderr=""
        )
        provider = CodexCLIProvider(model="codex")
        result = provider.execute("hello")
        assert result.text == "Codex output"


def test_gemini_cli_execute():
    import json
    mock_output = json.dumps({
        "response": "Gemini output",
        "model": "gemini-3.1-pro-preview",
        "usage": {"inputTokens": 4, "outputTokens": 8},
    })
    with patch("surfaced.providers.gemini_cli.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout=mock_output, stderr=""
        )
        provider = GeminiCLIProvider(model="gemini-3.1-pro-preview")
        result = provider.execute("hello")
        assert result.text == "Gemini output"
        assert result.input_tokens == 4


def test_gemini_cli_non_json_fallback():
    with patch("surfaced.providers.gemini_cli.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="plain text response", stderr=""
        )
        provider = GeminiCLIProvider()
        result = provider.execute("hello")
        assert result.text == "plain text response"


# --- Gemini API provider: execute with mocked SDK ---

def test_gemini_api_execute(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch("surfaced.providers.gemini_api.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 12
        mock_usage.candidates_token_count = 30

        mock_response = MagicMock()
        mock_response.text = "Gemini API response"
        mock_response.usage_metadata = mock_usage
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiAPIProvider(model="gemini-3.1-pro-preview")
        result = provider.execute("test prompt")

        assert isinstance(result, ProviderResponse)
        assert result.text == "Gemini API response"
        assert result.model == "gemini-3.1-pro-preview"
        assert result.input_tokens == 12
        assert result.output_tokens == 30
        mock_client.models.generate_content.assert_called_once()


def test_gemini_api_execute_no_usage_metadata(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch("surfaced.providers.gemini_api.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "response"
        mock_response.usage_metadata = None
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiAPIProvider(model="gemini-3.1-pro-preview")
        result = provider.execute("test")

        assert result.input_tokens == 0
        assert result.output_tokens == 0


# --- CLI providers: no-model cmd building ---

def test_claude_cli_no_model():
    import json
    mock_output = json.dumps({"result": "ok", "model": "default"})
    with patch("surfaced.providers.claude_cli.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr="")
        provider = ClaudeCLIProvider(model=None)
        provider.execute("hello")
        cmd = mock_run.call_args[0][0]
        assert "--model" not in cmd


def test_codex_cli_no_model():
    import json
    lines = [json.dumps({
        "type": "message", "role": "assistant",
        "content": [{"type": "output_text", "text": "ok"}],
        "model": "default", "usage": {"input_tokens": 1, "output_tokens": 1},
    })]
    with patch("surfaced.providers.codex_cli.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="\n".join(lines), stderr="")
        provider = CodexCLIProvider(model=None)
        provider.execute("hello")
        cmd = mock_run.call_args[0][0]
        assert "-m" not in cmd


def test_gemini_cli_no_model():
    import json
    mock_output = json.dumps({"response": "ok", "model": "default"})
    with patch("surfaced.providers.gemini_cli.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr="")
        provider = GeminiCLIProvider(model=None)
        provider.execute("hello")
        cmd = mock_run.call_args[0][0]
        assert "-m" not in cmd
