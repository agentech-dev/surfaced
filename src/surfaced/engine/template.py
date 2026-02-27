"""Template rendering for prompts."""

from __future__ import annotations

from surfaced.models.prompt import Prompt


def render_prompt(prompt: Prompt, variables: dict[str, str] | None = None) -> str:
    """Render a prompt, substituting template variables if applicable."""
    return prompt.render(variables)
