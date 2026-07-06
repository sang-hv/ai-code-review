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
