from typing import Protocol

from argus_review.services.agent.loop.schema import AgentLoopResultSchema
from argus_review.services.llm.types import LLMClientProtocol
from argus_review.services.prompt.types import PromptServiceProtocol


class AgentLoopServiceProtocol(Protocol):
    llm: LLMClientProtocol
    prompt: PromptServiceProtocol

    async def run(self, prompt: str, prompt_system: str) -> AgentLoopResultSchema:
        ...
