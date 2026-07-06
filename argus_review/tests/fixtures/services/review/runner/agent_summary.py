import pytest

from argus_review.services.cost.types import CostServiceProtocol
from argus_review.services.git.types import GitServiceProtocol
from argus_review.services.policy.types import PolicyServiceProtocol
from argus_review.services.prompt.types import PromptServiceProtocol
from argus_review.services.review.gateway.types import ReviewCommentGatewayProtocol, ReviewLLMGatewayProtocol
from argus_review.services.review.internal.summary.types import SummaryCommentServiceProtocol
from argus_review.services.review.runner.agent_summary import AgentSummaryReviewRunner
from argus_review.services.review.runner.types import ReviewRunnerProtocol
from argus_review.services.vcs.types import VCSClientProtocol


class FakeAgentSummaryReviewRunner(ReviewRunnerProtocol):
    def __init__(self):
        self.calls = []

    async def run(self) -> None:
        self.calls.append(("run", {}))


@pytest.fixture
def fake_agent_summary_review_runner() -> FakeAgentSummaryReviewRunner:
    return FakeAgentSummaryReviewRunner()


@pytest.fixture
def agent_summary_review_runner(
        fake_vcs_client: VCSClientProtocol,
        fake_git_service: GitServiceProtocol,
        fake_cost_service: CostServiceProtocol,
        fake_prompt_service: PromptServiceProtocol,
        fake_policy_service: PolicyServiceProtocol,
        fake_summary_comment_service: SummaryCommentServiceProtocol,
        fake_review_direct_llm_gateway: ReviewLLMGatewayProtocol,
        fake_review_comment_gateway: ReviewCommentGatewayProtocol,
) -> AgentSummaryReviewRunner:
    return AgentSummaryReviewRunner(
        vcs=fake_vcs_client,
        git=fake_git_service,
        cost=fake_cost_service,
        prompt=fake_prompt_service,
        policy=fake_policy_service,
        summary_comment=fake_summary_comment_service,
        review_agent_llm_gateway=fake_review_direct_llm_gateway,
        review_comment_gateway=fake_review_comment_gateway,
    )
