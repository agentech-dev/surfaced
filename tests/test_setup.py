"""Tests for setup wizard prompt examples."""

import json
from pathlib import Path
from uuid import uuid4

import surfaced.cli.setup as setup_cli
from surfaced.models.brand import Brand


ROOT = Path(__file__).resolve().parents[1]


class FakeQueryService:
    def __init__(self):
        self.positions = []
        self.prompts = []

    def get_canonical_position(self, position_id, active_only=True):
        return next((p for p in self.positions if p.id == position_id), None)

    def insert_canonical_position(self, position):
        self.positions.append(position)

    def insert_prompt(self, prompt):
        self.prompts.append(prompt)


def test_prompt_choice_lists_example_prompts_last(monkeypatch):
    captured = {}

    class FakeSelect:
        def ask(self):
            return "skip"

    def fake_select(message, choices):
        captured["choices"] = choices
        return FakeSelect()

    monkeypatch.setattr(setup_cli.questionary, "select", fake_select)

    setup_cli._step_prompts(Brand(id=uuid4(), name="ClickHouse"))

    titles = [choice.title for choice in captured["choices"]]
    values = [choice.value for choice in captured["choices"]]
    assert titles == [
        "Import from JSON file",
        "Import example prompts",
        "Skip",
    ]
    assert values == ["file", "example", "skip"]


def test_example_prompts_include_alignment_positions():
    data = json.loads((ROOT / "example_prompts.json").read_text())

    positions = data["canonical_positions"]
    prompts = data["prompts"]
    position_ids = {position["id"] for position in positions}
    alignment_prompts = [
        prompt for prompt in prompts
        if prompt.get("alignment_enabled")
    ]

    assert len(positions) >= 2
    assert len(alignment_prompts) >= 2
    assert all(
        prompt["alignment_position_id"] in position_ids
        for prompt in alignment_prompts
    )


def test_import_prompt_bundle_loads_positions_and_links_prompts(tmp_path):
    brand = Brand(id=uuid4(), name="ClickHouse")
    position_id = uuid4()
    path = tmp_path / "example_prompts.json"
    path.write_text(json.dumps({
        "canonical_positions": [{
            "id": str(position_id),
            "topic": "joins",
            "statement": "ClickHouse supports joins.",
        }],
        "prompts": [{
            "text": "Is ClickHouse good at joins?",
            "category": "data_warehousing",
            "branded": True,
            "alignment_enabled": True,
            "alignment_position_id": str(position_id),
            "tags": ["alignment"],
        }],
    }))
    qs = FakeQueryService()

    setup_cli._import_prompts_file(qs, str(path), brand)

    assert len(qs.positions) == 1
    assert qs.positions[0].brand_id == brand.id
    assert len(qs.prompts) == 1
    assert qs.prompts[0].brand_id == brand.id
    assert qs.prompts[0].alignment_enabled is True
    assert qs.prompts[0].alignment_position_id == position_id
