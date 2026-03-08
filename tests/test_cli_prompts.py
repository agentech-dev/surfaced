"""Tests for the prompts CLI commands."""

import json
from unittest.mock import MagicMock, patch
from uuid import UUID

from click.testing import CliRunner

from surfaced.cli.prompts import prompts
from surfaced.models.prompt import Prompt
from conftest import BRAND_ID, PROMPT_ID, NOW


def _prompt(**overrides):
    defaults = dict(
        id=PROMPT_ID, text="What are the best tools?",
        category="brand_query", brand_id=BRAND_ID,
        tags=["daily"], created_at=NOW, updated_at=NOW,
    )
    defaults.update(overrides)
    return Prompt(**defaults)


@patch("surfaced.cli.prompts._qs")
def test_add_prompt(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.insert_prompt.side_effect = lambda p: p
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(prompts, [
        "add", "--text", "Best tools?", "--category", "brand_query",
        "--brand", str(BRAND_ID),
    ])
    assert result.exit_code == 0
    assert "Best tools?" in result.output


@patch("surfaced.cli.prompts._qs")
def test_add_prompt_with_tags(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.insert_prompt.side_effect = lambda p: p
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(prompts, [
        "add", "--text", "Best tools?", "--category", "brand_query",
        "--brand", str(BRAND_ID), "--tags", "daily,weekly",
    ])
    assert result.exit_code == 0
    prompt = mock_qs.insert_prompt.call_args[0][0]
    assert prompt.tags == ["daily", "weekly"]


@patch("surfaced.cli.prompts._qs")
def test_add_prompt_template(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.insert_prompt.side_effect = lambda p: p
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(prompts, [
        "add", "--text", "Best {{product}} tools?",
        "--category", "brand_query", "--brand", str(BRAND_ID),
        "--template",
    ])
    assert result.exit_code == 0
    prompt = mock_qs.insert_prompt.call_args[0][0]
    assert prompt.is_template == 1
    assert "product" in prompt.variables


@patch("surfaced.cli.prompts._qs")
def test_list_prompts(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_prompts.return_value = [_prompt()]
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(prompts, ["list"])
    assert result.exit_code == 0
    assert "brand_query" in result.output


@patch("surfaced.cli.prompts._qs")
def test_list_prompts_with_filters(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_prompts.return_value = []
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(prompts, [
        "list", "--category", "brand_query", "--tag", "daily",
        "--brand", str(BRAND_ID),
    ])
    assert result.exit_code == 0
    mock_qs.get_prompts.assert_called_once_with(
        active_only=True, category="brand_query", tag="daily", brand_id=BRAND_ID,
    )


@patch("surfaced.cli.prompts._qs")
def test_list_prompts_empty(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_prompts.return_value = []
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(prompts, ["list"])
    assert result.exit_code == 0
    assert "No prompts found" in result.output


@patch("surfaced.cli.prompts._qs")
def test_show_prompt(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_prompt.return_value = _prompt()
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(prompts, ["show", str(PROMPT_ID)])
    assert result.exit_code == 0
    assert "What are the best tools?" in result.output


@patch("surfaced.cli.prompts._qs")
def test_show_prompt_not_found(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_prompt.return_value = None
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(prompts, ["show", str(PROMPT_ID)])
    assert result.exit_code != 0


@patch("surfaced.cli.prompts._qs")
def test_edit_prompt(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_prompt.return_value = _prompt()
    mock_qs.update_prompt.side_effect = lambda p: p
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(prompts, [
        "edit", str(PROMPT_ID), "--text", "Updated text",
    ])
    assert result.exit_code == 0
    updated = mock_qs.update_prompt.call_args[0][0]
    assert updated.text == "Updated text"


@patch("surfaced.cli.prompts._qs")
def test_edit_prompt_not_found(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs.get_prompt.return_value = None
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(prompts, ["edit", str(PROMPT_ID), "--text", "X"])
    assert result.exit_code != 0


@patch("surfaced.cli.prompts._qs")
def test_delete_prompt(mock_qs_fn):
    mock_qs = MagicMock()
    mock_qs_fn.return_value = mock_qs

    runner = CliRunner()
    result = runner.invoke(prompts, ["delete", str(PROMPT_ID)])
    assert result.exit_code == 0
    assert "deleted" in result.output


@patch("surfaced.cli.prompts._qs")
def test_import_prompts(mock_qs_fn, tmp_path):
    mock_qs = MagicMock()
    mock_qs.insert_prompt.side_effect = lambda p: p
    mock_qs_fn.return_value = mock_qs

    data = [
        {"text": "Prompt 1", "category": "brand_query", "brand_id": str(BRAND_ID), "tags": ["daily"]},
        {"text": "Prompt 2", "category": "industry_query", "brand_id": str(BRAND_ID)},
    ]
    filepath = tmp_path / "prompts.json"
    filepath.write_text(json.dumps(data))

    runner = CliRunner()
    result = runner.invoke(prompts, ["import", str(filepath)])
    assert result.exit_code == 0
    assert "Imported 2 prompts" in result.output
    assert mock_qs.insert_prompt.call_count == 2
