import pytest

from argus_review.libs.config.prompt import PromptConfig
from argus_review.services.agent.loop.schema import AgentTraceSchema
from argus_review.services.prompt.schema import PromptContextSchema
from argus_review.services.prompt.types import PromptServiceProtocol


class FakePromptService(PromptServiceProtocol):
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def prepare_prompt(self, prompts: list[str], context: PromptContextSchema) -> str:
        self.calls.append(("prepare_prompt", {"prompts": prompts, "context": context}))
        return "FAKE_PROMPT"

    def build_agent_request(
            self,
            traces: list[AgentTraceSchema],
            force_final: bool,
            original_prompt: str,
            original_prompt_system: str,
            compaction_summary: str = "",
    ) -> str:
        self.calls.append((
            "build_agent_request",
            {
                "traces": traces,
                "force_final": force_final,
                "original_prompt": original_prompt,
                "original_prompt_system": original_prompt_system,
                "compaction_summary": compaction_summary,
            }
        ))
        return "AGENT_LOOP_PROMPT"

    def build_agent_compaction_request(self, traces: list[AgentTraceSchema], prior_summary: str = "") -> str:
        self.calls.append((
            "build_agent_compaction_request",
            {"traces": traces, "prior_summary": prior_summary}
        ))
        return "AGENT_COMPACTION_PROMPT"

    def build_system_agent_compaction_request(self) -> str:
        self.calls.append(("build_system_agent_compaction_request", {}))
        return "SYSTEM_AGENT_COMPACTION_PROMPT"

    def build_agent_light_inline_request(
            self,
            context: PromptContextSchema,
            base_sha: str,
            head_sha: str,
            conventions_inventory: str = "",
    ) -> str:
        self.calls.append((
            "build_agent_light_inline_request",
            {
                "context": context,
                "base_sha": base_sha,
                "head_sha": head_sha,
                "conventions_inventory": conventions_inventory,
            }
        ))
        return "AGENT_LIGHT_INLINE_PROMPT"

    def build_agent_light_summary_request(
            self,
            context: PromptContextSchema,
            base_sha: str,
            head_sha: str,
            conventions_inventory: str = "",
    ) -> str:
        self.calls.append((
            "build_agent_light_summary_request",
            {
                "context": context,
                "base_sha": base_sha,
                "head_sha": head_sha,
                "conventions_inventory": conventions_inventory,
            }
        ))
        return "AGENT_LIGHT_SUMMARY_PROMPT"

    def build_agent_light_combined_request(
            self,
            context: PromptContextSchema,
            base_sha: str,
            head_sha: str,
            conventions_inventory: str = "",
    ) -> str:
        self.calls.append((
            "build_agent_light_combined_request",
            {
                "context": context,
                "base_sha": base_sha,
                "head_sha": head_sha,
                "conventions_inventory": conventions_inventory,
            }
        ))
        return "AGENT_LIGHT_COMBINED_PROMPT"

    def build_system_agent_light_inline_request(self) -> str:
        self.calls.append(("build_system_agent_light_inline_request", {}))
        return "SYSTEM_AGENT_LIGHT_INLINE_PROMPT"

    def build_system_agent_light_summary_request(self) -> str:
        self.calls.append(("build_system_agent_light_summary_request", {}))
        return "SYSTEM_AGENT_LIGHT_SUMMARY_PROMPT"

    def build_system_agent_light_combined_request(self) -> str:
        self.calls.append(("build_system_agent_light_combined_request", {}))
        return "SYSTEM_AGENT_LIGHT_COMBINED_PROMPT"

    def build_system_agent_request(self) -> str:
        self.calls.append(("build_system_agent_request", {}))
        return "SYSTEM_AGENT_PROMPT"


@pytest.fixture
def fake_prompt_service() -> FakePromptService:
    return FakePromptService()


@pytest.fixture
def fake_prompts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch methods of settings.prompt to return dummy values."""
    monkeypatch.setattr(PromptConfig, "load_agent", lambda self: ["GLOBAL_AGENT", "AGENT_PROMPT"])
    monkeypatch.setattr(PromptConfig, "load_system_agent", lambda self: ["SYS_AGENT_A", "SYS_AGENT_B"])


@pytest.fixture
def fake_prompt_context() -> PromptContextSchema:
    """Builds a context object that reflects the new unified review schema."""
    return PromptContextSchema(
        review_title="Fix login bug",
        review_description="Some description",
        review_author_name="Nikita",
        review_author_username="nikita.filonov",
        review_reviewers=["Alice", "Bob"],
        review_reviewers_usernames=["alice", "bob"],
        review_assignees=["Charlie"],
        review_assignees_usernames=["charlie"],
        source_branch="feature/login-fix",
        target_branch="main",
        labels=["bug", "critical"],
        changed_files=["foo.py", "bar.py"],
    )
