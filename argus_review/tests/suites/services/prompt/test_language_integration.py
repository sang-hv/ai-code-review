import pytest

from argus_review.config import settings
from argus_review.services.diff.schema import DiffFileSchema
from argus_review.services.prompt.schema import PromptContextSchema
from argus_review.services.prompt.service import PromptService


@pytest.mark.usefixtures("fake_prompts")
def test_inline_request_injects_language_directive(
        monkeypatch: pytest.MonkeyPatch,
        fake_prompt_context: PromptContextSchema,
):
    monkeypatch.setattr(settings.review, "language", "Vietnamese")

    diff = DiffFileSchema(file="foo.py", diff="+ added")
    result = PromptService.build_inline_request(diff, fake_prompt_context)

    assert "## Response Language" in result
    assert "Vietnamese" in result
    # Language directive stays in the instruction section, before the diff.
    assert result.index("## Response Language") < result.index("## Diff")


@pytest.mark.usefixtures("fake_prompts")
def test_summary_request_injects_language_directive(
        monkeypatch: pytest.MonkeyPatch,
        fake_prompt_context: PromptContextSchema,
):
    monkeypatch.setattr(settings.review, "language", "English")

    result = PromptService.build_summary_request([], fake_prompt_context)
    assert "Write the entire review" in result
    assert "English" in result


@pytest.mark.usefixtures("fake_prompts")
def test_blank_language_skips_directive(
        monkeypatch: pytest.MonkeyPatch,
        fake_prompt_context: PromptContextSchema,
):
    monkeypatch.setattr(settings.review, "language", "   ")

    diff = DiffFileSchema(file="foo.py", diff="+ added")
    result = PromptService.build_inline_request(diff, fake_prompt_context)
    assert "## Response Language" not in result
