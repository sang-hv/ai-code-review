import pytest

from argus_review.services.agent.loop.schema import AgentAction, AgentStepSchema, AgentTraceSchema
from argus_review.services.agent.loop.schema import AgentLoopResultSchema
from argus_review.services.review.gateway.review_agent_llm_gateway import ReviewAgentLLMGateway
from argus_review.tests.fixtures.services.artifacts import FakeArtifactsService
from argus_review.tests.fixtures.services.cost import FakeCostService
from argus_review.tests.fixtures.services.review.gateway.review_agent_llm_gateway import FakeAgentLoopService
from argus_review.tests.fixtures.services.review.gateway.review_agent_llm_gateway import FakeFallbackReviewLLMGateway


@pytest.mark.asyncio
async def test_agent_gateway_returns_agent_result(
        review_agent_llm_gateway: ReviewAgentLLMGateway,
        fake_cost_service: FakeCostService,
        fake_artifacts_service: FakeArtifactsService,
        fake_agent_loop_service: FakeAgentLoopService,
        fake_fallback_review_llm_gateway: FakeFallbackReviewLLMGateway,
):
    fake_agent_loop_service.responses["run"] = AgentLoopResultSchema(
        final_text="AGENT_RESPONSE",
        stop_reason="final",
        traces=[
            AgentTraceSchema(
                step=AgentStepSchema(action=AgentAction.FINAL, content="step-one"),
                iteration=1,
                raw_output="raw-step-one",
                prompt_tokens=11,
                completion_tokens=7,
                total_tokens=18,
            ),
            AgentTraceSchema(
                step=AgentStepSchema(action=AgentAction.FINAL, content="step-two"),
                iteration=2,
                raw_output="raw-step-two",
                prompt_tokens=5,
                completion_tokens=3,
                total_tokens=8,
            ),
        ],
    )

    result = await review_agent_llm_gateway.ask("PROMPT", "SYSTEM_PROMPT")
    assert result == "AGENT_RESPONSE"
    assert any(call[0] == "run" for call in fake_agent_loop_service.calls)
    calculate_calls = [call for call in fake_cost_service.calls if call[0] == "calculate"]
    assert len(calculate_calls) == 1
    assert calculate_calls[0][1]["result"].prompt_tokens == 16
    assert calculate_calls[0][1]["result"].completion_tokens == 10
    assert any(call[0] == "save_llm" for call in fake_artifacts_service.calls)
    save_call = next(call for call in fake_artifacts_service.calls if call[0] == "save_llm")
    assert save_call[1]["cost_report"] is not None
    assert fake_fallback_review_llm_gateway.calls == []


@pytest.mark.asyncio
async def test_agent_gateway_falls_back_to_default_gateway_on_error(
        review_agent_llm_gateway: ReviewAgentLLMGateway,
        fake_agent_loop_service: FakeAgentLoopService,
        fake_fallback_review_llm_gateway: FakeFallbackReviewLLMGateway,
):
    fake_agent_loop_service.responses["raise"] = True
    fake_fallback_review_llm_gateway.responses["ask"] = "ONE_SHOT_RESPONSE"

    result = await review_agent_llm_gateway.ask("PROMPT", "SYSTEM_PROMPT")
    assert result == "ONE_SHOT_RESPONSE"
    assert any(call[0] == "ask" for call in fake_fallback_review_llm_gateway.calls)


@pytest.mark.asyncio
async def test_agent_gateway_calculates_zero_cost_for_missing_trace_tokens(
        review_agent_llm_gateway: ReviewAgentLLMGateway,
        fake_cost_service: FakeCostService,
        fake_agent_loop_service: FakeAgentLoopService,
):
    fake_agent_loop_service.responses["run"] = AgentLoopResultSchema(
        final_text="AGENT_RESPONSE",
        stop_reason="final",
        traces=[
            AgentTraceSchema(
                step=AgentStepSchema(action=AgentAction.FINAL, content="done"),
                iteration=1,
                raw_output="raw",
            ),
        ],
    )

    result = await review_agent_llm_gateway.ask("PROMPT", "SYSTEM_PROMPT")

    assert result == "AGENT_RESPONSE"
    calculate_calls = [call for call in fake_cost_service.calls if call[0] == "calculate"]
    assert len(calculate_calls) == 1
    assert calculate_calls[0][1]["result"].prompt_tokens == 0
    assert calculate_calls[0][1]["result"].completion_tokens == 0


@pytest.mark.asyncio
async def test_agent_gateway_falls_back_when_final_output_is_empty(
        review_agent_llm_gateway: ReviewAgentLLMGateway,
        fake_agent_loop_service: FakeAgentLoopService,
        fake_fallback_review_llm_gateway: FakeFallbackReviewLLMGateway,
        fake_cost_service: FakeCostService,
):
    fake_agent_loop_service.responses["run"] = AgentLoopResultSchema(
        final_text="",
        stop_reason="max_requests_or_context_limit",
        traces=[
            AgentTraceSchema(
                step=AgentStepSchema(action=AgentAction.FINAL, content="Empty model response"),
                iteration=1,
                raw_output="",
            ),
        ],
    )
    fake_fallback_review_llm_gateway.responses["ask"] = "ONE_SHOT_RESPONSE"

    result = await review_agent_llm_gateway.ask("PROMPT", "SYSTEM_PROMPT")

    assert result == "ONE_SHOT_RESPONSE"
    assert any(call[0] == "ask" for call in fake_fallback_review_llm_gateway.calls)
    assert not any(call[0] == "calculate" for call in fake_cost_service.calls)


@pytest.mark.asyncio
async def test_agent_gateway_synthesizes_when_direct_fallback_returns_empty(
        review_agent_llm_gateway: ReviewAgentLLMGateway,
        fake_agent_loop_service: FakeAgentLoopService,
        fake_fallback_review_llm_gateway: FakeFallbackReviewLLMGateway,
):
    fake_agent_loop_service.responses["run"] = AgentLoopResultSchema(
        final_text="",
        stop_reason="max_requests_or_context_limit",
        traces=[
            AgentTraceSchema(
                step=AgentStepSchema(action=AgentAction.FINAL, content="Empty model response"),
                iteration=1,
                raw_output="",
            ),
        ],
    )
    fake_fallback_review_llm_gateway.responses["ask"] = ""

    result = await review_agent_llm_gateway.ask(
        "PROMPT",
        "Return a single JSON object with summary and comments.",
    )

    assert '"summary"' in result
    assert '"comments":[]' in result


@pytest.mark.asyncio
async def test_agent_gateway_synthesizes_when_direct_fallback_errors(
        review_agent_llm_gateway: ReviewAgentLLMGateway,
        fake_agent_loop_service: FakeAgentLoopService,
        fake_fallback_review_llm_gateway: FakeFallbackReviewLLMGateway,
):
    fake_agent_loop_service.responses["run"] = AgentLoopResultSchema(
        final_text="",
        stop_reason="max_requests_or_context_limit",
        traces=[
            AgentTraceSchema(
                step=AgentStepSchema(action=AgentAction.FINAL, content="Empty model response"),
                iteration=1,
                raw_output="",
            ),
        ],
    )

    async def raise_error(prompt: str, prompt_system: str) -> str:
        fake_fallback_review_llm_gateway.calls.append(
            ("ask", {"prompt": prompt, "prompt_system": prompt_system})
        )
        raise RuntimeError("boom")

    fake_fallback_review_llm_gateway.ask = raise_error

    result = await review_agent_llm_gateway.ask(
        "PROMPT",
        "Return summary review as plain markdown text.",
    )

    assert result


@pytest.mark.asyncio
async def test_agent_gateway_falls_back_when_final_output_is_bash_command(
        review_agent_llm_gateway: ReviewAgentLLMGateway,
        fake_agent_loop_service: FakeAgentLoopService,
        fake_fallback_review_llm_gateway: FakeFallbackReviewLLMGateway,
):
    fake_agent_loop_service.responses["run"] = AgentLoopResultSchema(
        final_text="<bash>\ngit diff a2ba70e..HEAD -- src/main.ts\n</bash>",
        stop_reason="max_requests_or_context_limit",
        traces=[
            AgentTraceSchema(
                step=AgentStepSchema(action=AgentAction.FINAL, content="<bash>...</bash>"),
                iteration=1,
                raw_output="<bash>...</bash>",
            ),
        ],
    )
    fake_fallback_review_llm_gateway.responses["ask"] = (
        '{"summary":"Fallback summary","comments":[]}'
    )

    result = await review_agent_llm_gateway.ask(
        "PROMPT",
        "The FINAL content MUST be a single JSON object and include summary plus comments.",
    )

    assert '"summary"' in result
    assert '"comments":[]' in result
