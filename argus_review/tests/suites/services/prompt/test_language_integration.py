import pytest

from argus_review.config import settings
from argus_review.services.prompt.schema import PromptContextSchema
from argus_review.services.prompt.service import PromptService


@pytest.fixture
def context() -> PromptContextSchema:
    return PromptContextSchema(
        review_title="Fix login bug",
        changed_files=["foo.py"],
    )


@pytest.mark.usefixtures("fake_prompts")
def test_agent_light_inline_request_injects_language_directive(
        monkeypatch: pytest.MonkeyPatch,
        context: PromptContextSchema,
):
    monkeypatch.setattr(settings.review, "language", "Vietnamese")

    result = PromptService.build_agent_light_inline_request(context=context, base_sha="B", head_sha="H")

    assert "## Response Language" in result
    assert "Vietnamese" in result


@pytest.mark.usefixtures("fake_prompts")
def test_agent_light_summary_request_injects_language_directive(
        monkeypatch: pytest.MonkeyPatch,
        context: PromptContextSchema,
):
    monkeypatch.setattr(settings.review, "language", "English")

    result = PromptService.build_agent_light_summary_request(context=context, base_sha="B", head_sha="H")
    assert "Write the entire review" in result
    assert "English" in result


@pytest.mark.usefixtures("fake_prompts")
def test_blank_language_skips_directive(
        monkeypatch: pytest.MonkeyPatch,
        context: PromptContextSchema,
):
    monkeypatch.setattr(settings.review, "language", "   ")

    result = PromptService.build_agent_light_inline_request(context=context, base_sha="B", head_sha="H")
    assert "## Response Language" not in result
