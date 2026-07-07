import pytest

from argus_review.services.review.internal.summary.schema import SummaryCommentSchema
from argus_review.services.review.runner.agent_summary import AgentSummaryReviewRunner
from argus_review.services.vcs.types import ReviewCommentSchema
from argus_review.tests.fixtures.services.policy import FakePolicyService
from argus_review.tests.fixtures.services.prompt import FakePromptService
from argus_review.tests.fixtures.services.review.gateway.review_comment_gateway import FakeReviewCommentGateway
from argus_review.tests.fixtures.services.review.gateway.review_direct_llm_gateway import FakeReviewDirectLLMGateway
from argus_review.tests.fixtures.services.review.internal.summary import FakeSummaryCommentService
from argus_review.tests.fixtures.services.vcs import FakeVCSClient


@pytest.mark.asyncio
async def test_run_happy_path(
        agent_summary_review_runner: AgentSummaryReviewRunner,
        fake_vcs_client: FakeVCSClient,
        fake_prompt_service: FakePromptService,
        fake_policy_service: FakePolicyService,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    """One agent session: light prompt built, agent gateway asked once, summary posted."""
    fake_review_comment_gateway.responses["get_summary_comments"] = []

    await agent_summary_review_runner.run()

    assert any(call[0] == "get_review_info" for call in fake_vcs_client.calls)
    assert any(call[0] == "build_agent_light_summary_request" for call in fake_prompt_service.calls)
    assert any(call[0] == "build_system_agent_light_summary_request" for call in fake_prompt_service.calls)
    assert any(call[0] == "ask" for call in fake_review_direct_llm_gateway.calls)
    assert any(call[0] == "process_summary_comment" for call in fake_review_comment_gateway.calls)
    # No per-file diff rendering / no full-diff summary prompt.
    assert not any(call[0] == "build_summary_request" for call in fake_prompt_service.calls)


@pytest.mark.asyncio
async def test_run_skips_when_existing_summary_comments(
        agent_summary_review_runner: AgentSummaryReviewRunner,
        fake_vcs_client: FakeVCSClient,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    fake_review_comment_gateway.responses["get_summary_comments"] = [
        ReviewCommentSchema(id="1", body="#ai-review-summary existing"),
    ]

    await agent_summary_review_runner.run()

    assert fake_vcs_client.calls == []
    assert not any(call[0] == "ask" for call in fake_review_direct_llm_gateway.calls)


@pytest.mark.asyncio
async def test_run_skips_when_no_changed_files(
        agent_summary_review_runner: AgentSummaryReviewRunner,
        fake_policy_service: FakePolicyService,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    fake_policy_service.responses["apply_for_files"] = []
    fake_review_comment_gateway.responses["get_summary_comments"] = []

    await agent_summary_review_runner.run()

    assert not any(call[0] == "ask" for call in fake_review_direct_llm_gateway.calls)


@pytest.mark.asyncio
async def test_run_skips_when_empty_summary(
        agent_summary_review_runner: AgentSummaryReviewRunner,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_summary_comment_service: FakeSummaryCommentService,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    fake_review_comment_gateway.responses["get_summary_comments"] = []
    fake_summary_comment_service.responses["parse_model_output"] = SummaryCommentSchema(text="")

    await agent_summary_review_runner.run()

    assert any(call[0] == "ask" for call in fake_review_direct_llm_gateway.calls)
    assert not any(call[0] == "process_summary_comment" for call in fake_review_comment_gateway.calls)


@pytest.mark.asyncio
async def test_run_chunks_and_concatenates_summaries(
        monkeypatch: pytest.MonkeyPatch,
        agent_summary_review_runner: AgentSummaryReviewRunner,
        fake_vcs_client: FakeVCSClient,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
        fake_summary_comment_service: FakeSummaryCommentService,
):
    """With 5 files and max_files_per_chunk=2, expect 3 chunk sessions with concatenated summaries."""
    from argus_review.services.vcs.types import ReviewInfoSchema

    monkeypatch.setattr("argus_review.config.settings.agent.max_files_per_chunk", 2)

    fake_vcs_client.responses["get_review_info"] = ReviewInfoSchema(
        changed_files=["a.py", "b.py", "c.py", "d.py", "e.py"],
        base_sha="A",
        head_sha="B",
    )
    fake_review_comment_gateway.responses["get_summary_comments"] = []

    outputs = [SummaryCommentSchema(text=f"summary-{i}") for i in range(3)]
    call_count = {"n": 0}

    def parse_sequence(output: str):
        result = outputs[call_count["n"]]
        call_count["n"] += 1
        return result

    monkeypatch.setattr(fake_summary_comment_service, "parse_model_output", parse_sequence)

    await agent_summary_review_runner.run()

    ask_calls = [call for call in fake_review_direct_llm_gateway.calls if call[0] == "ask"]
    assert len(ask_calls) == 3

    summary_calls = [
        call for call in fake_review_comment_gateway.calls if call[0] == "process_summary_comment"
    ]
    assert len(summary_calls) == 1
    assert summary_calls[0][1]["comment"].text == "summary-0\n\nsummary-1\n\nsummary-2"
