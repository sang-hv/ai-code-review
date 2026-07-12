import pytest

from argus_review.services.llm.types import ChatResultSchema
from argus_review.services.review.gateway.review_direct_llm_gateway import ReviewDirectLLMGateway
from argus_review.tests.fixtures.services.artifacts import FakeArtifactsService
from argus_review.tests.fixtures.services.cost import FakeCostService
from argus_review.tests.fixtures.services.llm import FakeLLMClient


@pytest.mark.asyncio
async def test_ask_happy_path(
        review_direct_llm_gateway: ReviewDirectLLMGateway,
        fake_llm_client: FakeLLMClient,
        fake_cost_service: FakeCostService,
        fake_artifacts_service: FakeArtifactsService,
):
    """Should call LLM, calculate cost, save artifacts, and return text."""
    fake_llm_client.responses["chat"] = ChatResultSchema(text="FAKE_RESPONSE")

    result = await review_direct_llm_gateway.ask("PROMPT", "SYSTEM_PROMPT")

    assert result == "FAKE_RESPONSE"
    assert any(call[0] == "chat" for call in fake_llm_client.calls)
    calculate_calls = [call for call in fake_cost_service.calls if call[0] == "calculate"]
    assert len(calculate_calls) == 1
    assert calculate_calls[0][1]["result"].prompt_tokens is None
    assert calculate_calls[0][1]["result"].completion_tokens is None
    assert any(call[0] == "save_llm" for call in fake_artifacts_service.calls)


@pytest.mark.asyncio
async def test_ask_warns_on_empty_response(
        capsys: pytest.CaptureFixture,
        review_direct_llm_gateway: ReviewDirectLLMGateway,
        fake_llm_client: FakeLLMClient,
        fake_cost_service: FakeCostService,
        fake_artifacts_service: FakeArtifactsService,
):
    """Should retry once and still return empty if both responses are empty."""

    async def always_empty_chat(prompt: str, prompt_system: str) -> ChatResultSchema:
        fake_llm_client.calls.append(("chat", {"prompt": prompt, "prompt_system": prompt_system}))
        return ChatResultSchema(text="")

    fake_llm_client.chat = always_empty_chat

    result = await review_direct_llm_gateway.ask("PROMPT", "SYSTEM_PROMPT")
    output = capsys.readouterr().out

    assert result == ""
    assert "LLM returned an empty response" in output
    assert "retry also returned empty response" in output

    assert len([call for call in fake_llm_client.calls if call[0] == "chat"]) == 2
    assert any(call[0] == "calculate" for call in fake_cost_service.calls)
    assert any(call[0] == "save_llm" for call in fake_artifacts_service.calls)


@pytest.mark.asyncio
async def test_ask_retries_once_and_returns_non_empty_retry(
        review_direct_llm_gateway: ReviewDirectLLMGateway,
        fake_llm_client: FakeLLMClient,
):
    responses = iter([
        ChatResultSchema(text="", prompt_tokens=10, completion_tokens=5),
        ChatResultSchema(text="RECOVERED", prompt_tokens=20, completion_tokens=10),
    ])

    async def sequence_chat(prompt: str, prompt_system: str) -> ChatResultSchema:
        fake_llm_client.calls.append(("chat", {"prompt": prompt, "prompt_system": prompt_system}))
        return next(responses)

    fake_llm_client.chat = sequence_chat

    result = await review_direct_llm_gateway.ask("PROMPT", "SYSTEM_PROMPT")

    assert result == "RECOVERED"
    assert len([call for call in fake_llm_client.calls if call[0] == "chat"]) == 2


@pytest.mark.asyncio
async def test_ask_synthesizes_combined_fallback_without_retry(
        review_direct_llm_gateway: ReviewDirectLLMGateway,
        fake_llm_client: FakeLLMClient,
):
    async def always_empty_chat(prompt: str, prompt_system: str) -> ChatResultSchema:
        fake_llm_client.calls.append(("chat", {"prompt": prompt, "prompt_system": prompt_system}))
        return ChatResultSchema(text="", prompt_tokens=10, completion_tokens=5)

    fake_llm_client.chat = always_empty_chat

    result = await review_direct_llm_gateway.ask(
        "PROMPT",
        '{"summary":"<markdown>","comments":[{"file":"x.py","line":1,"message":"m"}]}'
    )

    assert '"summary"' in result
    assert '"comments":[]' in result
    assert len([call for call in fake_llm_client.calls if call[0] == "chat"]) == 1


@pytest.mark.asyncio
async def test_ask_synthesizes_combined_fallback_for_generic_json_object_contract(
        review_direct_llm_gateway: ReviewDirectLLMGateway,
        fake_llm_client: FakeLLMClient,
):
    async def always_empty_chat(prompt: str, prompt_system: str) -> ChatResultSchema:
        fake_llm_client.calls.append(("chat", {"prompt": prompt, "prompt_system": prompt_system}))
        return ChatResultSchema(text="", prompt_tokens=10, completion_tokens=5)

    fake_llm_client.chat = always_empty_chat

    result = await review_direct_llm_gateway.ask(
        "PROMPT",
        "The FINAL content MUST be a single JSON object and include summary plus comments.",
    )

    assert '"summary"' in result
    assert '"comments":[]' in result
    assert len([call for call in fake_llm_client.calls if call[0] == "chat"]) == 1


@pytest.mark.asyncio
async def test_ask_synthesizes_when_control_protocol_output_is_returned(
        review_direct_llm_gateway: ReviewDirectLLMGateway,
        fake_llm_client: FakeLLMClient,
):
    async def tool_calls_chat(prompt: str, prompt_system: str) -> ChatResultSchema:
        fake_llm_client.calls.append(("chat", {"prompt": prompt, "prompt_system": prompt_system}))
        return ChatResultSchema(
            text="<tool_calls>\n<tool_call>...</tool_call>\n</tool_calls>",
            prompt_tokens=10,
            completion_tokens=5,
        )

    fake_llm_client.chat = tool_calls_chat

    result = await review_direct_llm_gateway.ask(
        "PROMPT",
        "The FINAL content MUST be a single JSON object and include summary plus comments.",
    )

    assert '"summary"' in result
    assert '"comments":[]' in result
    assert len([call for call in fake_llm_client.calls if call[0] == "chat"]) == 1


@pytest.mark.asyncio
async def test_ask_passes_llm_tokens_to_calculate(
        review_direct_llm_gateway: ReviewDirectLLMGateway,
        fake_llm_client: FakeLLMClient,
        fake_cost_service: FakeCostService,
):
    fake_llm_client.responses["chat"] = ChatResultSchema(
        text="FAKE_RESPONSE",
        prompt_tokens=123,
        completion_tokens=77,
    )

    result = await review_direct_llm_gateway.ask("PROMPT", "SYSTEM_PROMPT")

    assert result == "FAKE_RESPONSE"
    calculate_call = next(call for call in fake_cost_service.calls if call[0] == "calculate")
    assert calculate_call[1]["result"].prompt_tokens == 123
    assert calculate_call[1]["result"].completion_tokens == 77


@pytest.mark.asyncio
async def test_ask_handles_llm_error(
        capsys: pytest.CaptureFixture,
        fake_llm_client: FakeLLMClient,
        review_direct_llm_gateway: ReviewDirectLLMGateway,
):
    """Should handle exceptions gracefully and log error."""

    async def failing_chat(prompt: str, prompt_system: str):
        raise RuntimeError("LLM connection failed")

    fake_llm_client.chat = failing_chat

    result = await review_direct_llm_gateway.ask("PROMPT", "SYSTEM_PROMPT")
    output = capsys.readouterr().out

    assert result is None
    assert "LLM request failed" in output
    assert "RuntimeError" in output
