import pytest

from argus_review.services.diff.schema import DiffFileSchema
from argus_review.services.prompt.schema import PromptContextSchema
from argus_review.services.prompt.service import PromptService


class _FakeConventions:
    """Renders a marker block only for the inline mode."""

    def render(self, mode: str) -> str:
        if mode == "inline":
            return "## Project Coding Conventions\n\nUSE_SNAKE_CASE"
        return ""


@pytest.fixture
def fake_conventions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "argus_review.services.prompt.service.get_conventions_service",
        lambda: _FakeConventions(),
    )


@pytest.mark.usefixtures("fake_prompts", "fake_conventions")
def test_inline_request_injects_conventions_before_diff(fake_prompt_context: PromptContextSchema):
    diff = DiffFileSchema(file="foo.py", diff="+ added")
    result = PromptService.build_inline_request(diff, fake_prompt_context)

    assert "INLINE_PROMPT" in result
    assert "## Project Coding Conventions" in result
    assert "USE_SNAKE_CASE" in result
    # Conventions must come before the diff section.
    assert result.index("## Project Coding Conventions") < result.index("## Diff")


@pytest.mark.usefixtures("fake_prompts", "fake_conventions")
def test_summary_request_omits_conventions_when_mode_returns_empty(fake_prompt_context: PromptContextSchema):
    diffs = [DiffFileSchema(file="a.py", diff="+ foo")]
    result = PromptService.build_summary_request(diffs, fake_prompt_context)

    assert "SUMMARY_PROMPT" in result
    assert "Project Coding Conventions" not in result
