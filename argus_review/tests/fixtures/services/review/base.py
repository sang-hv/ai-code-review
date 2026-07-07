import pytest

from argus_review.services.cost.types import CostServiceProtocol
from argus_review.services.review.runner.types import ReviewRunnerProtocol
from argus_review.services.review.service import ReviewService


@pytest.fixture
def review_service(
        monkeypatch: pytest.MonkeyPatch,
        fake_cost_service: CostServiceProtocol,
        fake_agent_inline_review_runner: ReviewRunnerProtocol,
        fake_agent_summary_review_runner: ReviewRunnerProtocol,
        fake_agent_review_runner: ReviewRunnerProtocol,
):
    monkeypatch.setattr("argus_review.services.review.service.CostService", lambda: fake_cost_service)

    monkeypatch.setattr(
        "argus_review.services.review.service.AgentInlineReviewRunner",
        lambda **_: fake_agent_inline_review_runner
    )
    monkeypatch.setattr(
        "argus_review.services.review.service.AgentSummaryReviewRunner",
        lambda **_: fake_agent_summary_review_runner
    )
    monkeypatch.setattr(
        "argus_review.services.review.service.AgentReviewRunner",
        lambda **_: fake_agent_review_runner
    )

    return ReviewService()
