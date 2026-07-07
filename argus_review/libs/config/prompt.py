from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, FilePath, Field

from argus_review.libs.resources import load_resource


def resolve_prompt_files(files: list[FilePath] | None, default_file: str) -> list[Path]:
    return files or [
        load_resource(
            package="argus_review.prompts",
            filename=default_file,
            fallback=f"argus_review/prompts/{default_file}"
        )
    ]


def resolve_system_prompt_files(files: list[FilePath] | None, include: bool, default_file: str) -> list[Path]:
    global_files = [
        load_resource(
            package="argus_review.prompts",
            filename=default_file,
            fallback=f"argus_review/prompts/{default_file}"
        )
    ]

    if files is None:
        return global_files

    if include:
        return global_files + files

    return files


class PromptConfig(BaseModel):
    context: dict[str, str] = Field(default_factory=dict)
    normalize_prompts: bool = True
    context_placeholder: str = "<<{value}>>"

    # --- Prompts ---
    agent_prompt_files: list[FilePath] | None = None
    agent_light_inline_prompt_files: list[FilePath] | None = None
    agent_light_summary_prompt_files: list[FilePath] | None = None
    agent_light_combined_prompt_files: list[FilePath] | None = None
    agent_compaction_prompt_files: list[FilePath] | None = None

    # --- System Prompts ---
    system_agent_prompt_files: list[FilePath] | None = None
    system_agent_light_inline_prompt_files: list[FilePath] | None = None
    system_agent_light_summary_prompt_files: list[FilePath] | None = None
    system_agent_light_combined_prompt_files: list[FilePath] | None = None

    # --- Include System Prompts ---
    include_agent_system_prompts: bool = True

    # --- Prompts ---
    @cached_property
    def agent_prompt_files_or_default(self) -> list[Path]:
        return resolve_prompt_files(self.agent_prompt_files, "default_agent.md")

    @cached_property
    def agent_compaction_prompt_files_or_default(self) -> list[Path]:
        return resolve_prompt_files(self.agent_compaction_prompt_files, "default_agent_compaction.md")

    @cached_property
    def agent_light_inline_prompt_files_or_default(self) -> list[Path]:
        return resolve_prompt_files(self.agent_light_inline_prompt_files, "default_agent_light_inline.md")

    @cached_property
    def agent_light_summary_prompt_files_or_default(self) -> list[Path]:
        return resolve_prompt_files(self.agent_light_summary_prompt_files, "default_agent_light_summary.md")

    @cached_property
    def agent_light_combined_prompt_files_or_default(self) -> list[Path]:
        return resolve_prompt_files(self.agent_light_combined_prompt_files, "default_agent_light_combined.md")

    # --- System Prompts ---
    @cached_property
    def system_agent_prompt_files_or_default(self) -> list[Path]:
        return resolve_system_prompt_files(
            files=self.system_agent_prompt_files,
            include=self.include_agent_system_prompts,
            default_file="default_system_agent.md"
        )

    @cached_property
    def system_agent_light_inline_prompt_files_or_default(self) -> list[Path]:
        return resolve_prompt_files(
            self.system_agent_light_inline_prompt_files, "default_system_agent_light_inline.md"
        )

    @cached_property
    def system_agent_light_summary_prompt_files_or_default(self) -> list[Path]:
        return resolve_prompt_files(
            self.system_agent_light_summary_prompt_files, "default_system_agent_light_summary.md"
        )

    @cached_property
    def system_agent_light_combined_prompt_files_or_default(self) -> list[Path]:
        return resolve_prompt_files(
            self.system_agent_light_combined_prompt_files, "default_system_agent_light_combined.md"
        )

    # --- Load Prompts ---
    def load_agent(self) -> list[str]:
        return [file.read_text(encoding="utf-8") for file in self.agent_prompt_files_or_default]

    def load_agent_compaction(self) -> list[str]:
        return [file.read_text(encoding="utf-8") for file in self.agent_compaction_prompt_files_or_default]

    def load_agent_light_inline(self) -> list[str]:
        return [file.read_text(encoding="utf-8") for file in self.agent_light_inline_prompt_files_or_default]

    def load_agent_light_summary(self) -> list[str]:
        return [file.read_text(encoding="utf-8") for file in self.agent_light_summary_prompt_files_or_default]

    def load_agent_light_combined(self) -> list[str]:
        return [file.read_text(encoding="utf-8") for file in self.agent_light_combined_prompt_files_or_default]

    # --- Load System Prompts ---
    def load_system_agent(self) -> list[str]:
        return [file.read_text(encoding="utf-8") for file in self.system_agent_prompt_files_or_default]

    def load_system_agent_light_inline(self) -> list[str]:
        return [file.read_text(encoding="utf-8") for file in self.system_agent_light_inline_prompt_files_or_default]

    def load_system_agent_light_summary(self) -> list[str]:
        return [file.read_text(encoding="utf-8") for file in self.system_agent_light_summary_prompt_files_or_default]

    def load_system_agent_light_combined(self) -> list[str]:
        return [
            file.read_text(encoding="utf-8") for file in self.system_agent_light_combined_prompt_files_or_default
        ]
