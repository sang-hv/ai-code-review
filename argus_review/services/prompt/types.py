from typing import Protocol

from argus_review.services.agent.loop.schema import AgentTraceSchema
from argus_review.services.prompt.schema import PromptContextSchema


class PromptServiceProtocol(Protocol):
    def prepare_prompt(self, prompts: list[str], context: PromptContextSchema) -> str:
        ...

    def build_agent_request(
            self,
            traces: list[AgentTraceSchema],
            force_final: bool,
            original_prompt: str,
            original_prompt_system: str,
            compaction_summary: str = "",
    ) -> str:
        ...

    def build_agent_compaction_request(self, traces: list[AgentTraceSchema], prior_summary: str = "") -> str:
        ...

    def build_system_agent_compaction_request(self) -> str:
        ...

    def build_agent_light_inline_request(
            self,
            context: PromptContextSchema,
            base_sha: str,
            head_sha: str,
            conventions_inventory: str = "",
    ) -> str:
        ...

    def build_agent_light_summary_request(
            self,
            context: PromptContextSchema,
            base_sha: str,
            head_sha: str,
            conventions_inventory: str = "",
    ) -> str:
        ...

    def build_agent_light_combined_request(
            self,
            context: PromptContextSchema,
            base_sha: str,
            head_sha: str,
            conventions_inventory: str = "",
    ) -> str:
        ...

    def build_system_agent_light_inline_request(self) -> str:
        ...

    def build_system_agent_light_summary_request(self) -> str:
        ...

    def build_system_agent_light_combined_request(self) -> str:
        ...

    def build_system_agent_request(self) -> str:
        ...
