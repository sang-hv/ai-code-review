from typing import Protocol

from argus_review.services.review.internal.agent_combined.schema import AgentCombinedResultSchema


class AgentCombinedResultServiceProtocol(Protocol):
    def parse_model_output(self, output: str) -> AgentCombinedResultSchema:
        ...
