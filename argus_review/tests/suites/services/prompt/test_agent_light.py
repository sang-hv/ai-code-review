import pytest

from argus_review.config import settings
from argus_review.libs.config.prompt import PromptConfig
from argus_review.services.prompt.schema import PromptContextSchema
from argus_review.services.prompt.service import PromptService


@pytest.fixture
def context() -> PromptContextSchema:
    return PromptContextSchema(
        review_title="Add feature",
        review_description="Adds a new endpoint",
        review_author_name="Alice",
        review_reviewers=["Bob"],
        source_branch="feat/x",
        target_branch="main",
        labels=["enhancement"],
        changed_files=["app/main.py", "app/utils.py"],
    )


def test_agent_light_inline_request_contains_metadata_and_files(context: PromptContextSchema):
    prompt = PromptService.build_agent_light_inline_request(
        context=context, base_sha="BASE", head_sha="HEAD",
    )

    assert "Add feature" in prompt
    assert "app/main.py" in prompt
    assert "app/utils.py" in prompt
    assert "BASE" in prompt
    assert "HEAD" in prompt
    # Tool guidance present, but no preloaded diff/convention body.
    assert "git diff" in prompt


def test_agent_light_inline_request_includes_inventory_when_present(context: PromptContextSchema):
    inventory = "## Project Coding Conventions\n\n- .argus-review/cache/conventions/py.md (docs/py.md), 42 lines"
    prompt = PromptService.build_agent_light_inline_request(
        context=context, base_sha="B", head_sha="H", conventions_inventory=inventory,
    )
    assert "42 lines" in prompt
    assert "conventions" in prompt.lower()


def test_agent_light_inline_request_omits_inventory_when_empty(context: PromptContextSchema):
    prompt = PromptService.build_agent_light_inline_request(
        context=context, base_sha="B", head_sha="H", conventions_inventory="",
    )
    assert "cache/conventions" not in prompt


def test_agent_light_summary_request_contains_metadata(context: PromptContextSchema):
    prompt = PromptService.build_agent_light_summary_request(
        context=context, base_sha="B", head_sha="H",
    )
    assert "Add feature" in prompt
    assert "summary" in prompt.lower()


def test_agent_light_inline_system_contract_requires_json_array():
    contract = PromptService.build_system_agent_light_inline_request()
    assert "JSON array" in contract
    assert "line" in contract


def test_agent_light_summary_system_contract_is_plain_text():
    contract = PromptService.build_system_agent_light_summary_request()
    assert "plain markdown" in contract.lower()


def test_agent_light_request_applies_language(context: PromptContextSchema, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings.review, "language", "Vietnamese")
    prompt = PromptService.build_agent_light_summary_request(
        context=context, base_sha="B", head_sha="H",
    )
    assert "Vietnamese" in prompt


def test_agent_light_inline_instruction_is_overridable(context: PromptContextSchema, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(PromptConfig, "load_agent_light_inline", lambda self: ["CUSTOM INLINE INSTRUCTION"])
    prompt = PromptService.build_agent_light_inline_request(
        context=context, base_sha="B", head_sha="H",
    )
    assert "CUSTOM INLINE INSTRUCTION" in prompt
    # Dynamic metadata/tool-guidance is still injected alongside the custom instruction.
    assert "app/main.py" in prompt
    assert "git diff" in prompt


def test_agent_light_system_contract_is_overridable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(PromptConfig, "load_system_agent_light_summary", lambda self: ["CUSTOM CONTRACT"])
    assert PromptService.build_system_agent_light_summary_request() == "CUSTOM CONTRACT"
