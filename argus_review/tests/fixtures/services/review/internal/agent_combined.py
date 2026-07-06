import pytest

from argus_review.services.review.internal.agent_combined.schema import AgentCombinedResultSchema
from argus_review.services.review.internal.agent_combined.service import AgentCombinedResultService
from argus_review.services.review.internal.agent_combined.types import AgentCombinedResultServiceProtocol
from argus_review.services.review.internal.inline.schema import InlineCommentSchema


class FakeAgentCombinedResultService(AgentCombinedResultServiceProtocol):
    def __init__(self, result: AgentCombinedResultSchema | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.result = result or AgentCombinedResultSchema(
            summary="Fake combined summary",
            comments=[InlineCommentSchema(file="main.py", line=1, message="Test comment")],
        )

    def parse_model_output(self, output: str) -> AgentCombinedResultSchema:
        self.calls.append(("parse_model_output", {"output": output}))
        return self.result


@pytest.fixture
def fake_agent_combined_result_service() -> FakeAgentCombinedResultService:
    return FakeAgentCombinedResultService()


@pytest.fixture
def agent_combined_result_service() -> AgentCombinedResultService:
    return AgentCombinedResultService()
