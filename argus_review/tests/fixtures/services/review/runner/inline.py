import pytest

from argus_review.services.cost.types import CostServiceProtocol
from argus_review.services.diff.types import DiffServiceProtocol
from argus_review.services.git.types import GitServiceProtocol
from argus_review.services.policy.types import PolicyServiceProtocol
from argus_review.services.prompt.types import PromptServiceProtocol
from argus_review.services.review.gateway.types import ReviewLLMGatewayProtocol, ReviewCommentGatewayProtocol
from argus_review.services.review.internal.inline.types import InlineCommentServiceProtocol
from argus_review.services.review.runner.inline import InlineReviewRunner
from argus_review.services.review.runner.types import ReviewRunnerProtocol
from argus_review.services.vcs.types import VCSClientProtocol


class FakeInlineReviewRunner(ReviewRunnerProtocol):
    def __init__(self):
        self.calls = []

    async def run(self) -> None:
        self.calls.append(("run", {}))


@pytest.fixture
def fake_inline_review_runner() -> FakeInlineReviewRunner:
    return FakeInlineReviewRunner()


@pytest.fixture
def inline_review_runner(
        fake_vcs_client: VCSClientProtocol,
        fake_git_service: GitServiceProtocol,
        fake_diff_service: DiffServiceProtocol,
        fake_cost_service: CostServiceProtocol,
        fake_prompt_service: PromptServiceProtocol,
        fake_policy_service: PolicyServiceProtocol,
        fake_review_llm_gateway: ReviewLLMGatewayProtocol,
        fake_review_comment_gateway: ReviewCommentGatewayProtocol,
        fake_inline_comment_service: InlineCommentServiceProtocol,
) -> InlineReviewRunner:
    return InlineReviewRunner(
        vcs=fake_vcs_client,
        git=fake_git_service,
        diff=fake_diff_service,
        cost=fake_cost_service,
        prompt=fake_prompt_service,
        policy=fake_policy_service,
        inline_comment=fake_inline_comment_service,
        review_llm_gateway=fake_review_llm_gateway,
        review_comment_gateway=fake_review_comment_gateway,
    )
