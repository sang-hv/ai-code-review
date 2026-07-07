import pytest

from argus_review.config import settings
from argus_review.services.agent.loop.schema import AgentAction, AgentStepSchema, AgentTraceSchema
from argus_review.services.prompt.schema import PromptContextSchema
from argus_review.services.prompt.service import PromptService


@pytest.mark.usefixtures("fake_prompts")
def test_prepare_prompt_basic_substitution(fake_prompt_context: PromptContextSchema) -> None:
    prompts = ["Hello", "MR title: <<review_title>>"]
    result = PromptService.prepare_prompt(prompts, fake_prompt_context)

    assert "Hello" in result
    assert "MR title: Fix login bug" in result


@pytest.mark.usefixtures("fake_prompts")
def test_prepare_prompt_applies_normalization(
        monkeypatch: pytest.MonkeyPatch,
        fake_prompt_context: PromptContextSchema
) -> None:
    monkeypatch.setattr(settings.prompt, "normalize_prompts", True)
    prompts = ["Line with space   ", "", "", "Next line"]
    result = PromptService.prepare_prompt(prompts, fake_prompt_context)

    assert "Line with space" in result
    assert "Next line" in result
    assert "\n\n\n" not in result


@pytest.mark.usefixtures("fake_prompts")
def test_prepare_prompt_skips_normalization(
        monkeypatch: pytest.MonkeyPatch,
        fake_prompt_context: PromptContextSchema
) -> None:
    monkeypatch.setattr(settings.prompt, "normalize_prompts", False)
    prompts = ["Line with space   ", "", "", "Next line"]
    result = PromptService.prepare_prompt(prompts, fake_prompt_context)

    assert "Line with space   " in result
    assert "\n\n\n" in result


@pytest.mark.usefixtures("fake_prompts")
def test_build_agent_request_contains_history() -> None:
    traces = [
        AgentTraceSchema(
            step=AgentStepSchema(
                action=AgentAction.TOOL_CALL,
                command="rg foo src",
            ),
            iteration=1,
            raw_output='{"action":"TOOL_CALL"}',
            tool_output="foo.py:1: foo",
        )
    ]
    result = PromptService.build_agent_request(
        traces=traces,
        force_final=False,
        original_prompt="ORIGINAL_PROMPT",
        original_prompt_system="ORIGINAL_SYSTEM",
    )
    assert "GLOBAL_AGENT" in result
    assert "AGENT_PROMPT" in result
    assert "## Agent mode" in result
    assert "## Task output format" in result
    assert "ORIGINAL_SYSTEM" in result
    assert "## Task" in result
    assert "ORIGINAL_PROMPT" in result
    assert "## Agent history" in result
    assert "Command: rg foo src" in result


@pytest.mark.usefixtures("fake_prompts")
def test_build_system_agent_request_returns_only_agent_instructions() -> None:
    result = PromptService.build_system_agent_request()
    assert "SYS_AGENT_A" in result
    assert "SYS_AGENT_B" in result


@pytest.mark.usefixtures("fake_prompts")
def test_build_agent_request_force_final_mode() -> None:
    result = PromptService.build_agent_request(
        traces=[],
        force_final=True,
        original_prompt="TASK",
        original_prompt_system="FORMAT",
    )
    assert "## Agent mode" in result
    assert "Return FINAL only." in result
    assert "No previous steps." in result
