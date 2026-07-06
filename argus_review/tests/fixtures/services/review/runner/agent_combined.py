import pytest

from argus_review.services.cost.types import CostServiceProtocol
from argus_review.services.diff.types import DiffServiceProtocol
from argus_review.services.git.types import GitServiceProtocol
from argus_review.services.policy.types import PolicyServiceProtocol
from argus_review.services.prompt.types import PromptServiceProtocol
from argus_review.services.review.gateway.types import ReviewCommentGatewayProtocol, ReviewLLMGatewayProtocol
from argus_review.services.review.internal.agent_combined.types import AgentCombinedResultServiceProtocol
from argus_review.services.review.runner.agent_combined import AgentReviewRunner
from argus_review.services.review.runner.types import ReviewRunnerProtocol
from argus_review.services.vcs.types import VCSClientProtocol


class FakeAgentReviewRunner(ReviewRunnerProtocol):
    def __init__(self):
        self.calls = []

    async def run(self) -> None:
        self.calls.append(("run", {}))


@pytest.fixture
def fake_agent_review_runner() -> FakeAgentReviewRunner:
    return FakeAgentReviewRunner()


@pytest.fixture
def agent_review_runner(
        fake_vcs_client: VCSClientProtocol,
        fake_git_service: GitServiceProtocol,
        fake_diff_service: DiffServiceProtocol,
        fake_cost_service: CostServiceProtocol,
        fake_prompt_service: PromptServiceProtocol,
        fake_policy_service: PolicyServiceProtocol,
        fake_agent_combined_result_service: AgentCombinedResultServiceProtocol,
        fake_review_direct_llm_gateway: ReviewLLMGatewayProtocol,
        fake_review_comment_gateway: ReviewCommentGatewayProtocol,
) -> AgentReviewRunner:
    return AgentReviewRunner(
        vcs=fake_vcs_client,
        git=fake_git_service,
        diff=fake_diff_service,
        cost=fake_cost_service,
        prompt=fake_prompt_service,
        policy=fake_policy_service,
        agent_combined_result=fake_agent_combined_result_service,
        review_agent_llm_gateway=fake_review_direct_llm_gateway,
        review_comment_gateway=fake_review_comment_gateway,
    )
