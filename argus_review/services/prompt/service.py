from argus_review.config import settings
from argus_review.services.agent.loop.schema import AgentTraceSchema
from argus_review.services.prompt.schema import PromptContextSchema
from argus_review.services.prompt.tools import (
    format_traces,
    normalize_prompt,
)
from argus_review.services.prompt.types import PromptServiceProtocol


class PromptService(PromptServiceProtocol):
    @classmethod
    def prepare_prompt(cls, prompts: list[str], context: PromptContextSchema) -> str:
        prompt = "\n\n".join(prompts)
        prompt = context.apply_format(prompt)

        if settings.prompt.normalize_prompts:
            prompt = normalize_prompt(prompt)

        return prompt

    @classmethod
    def with_language(cls, prompt: str) -> str:
        """Instruct the model to write the review in the configured language."""
        language = settings.review.language.strip()
        if not language:
            return prompt

        directive = (
            f"## Response Language\n\n"
            f"Write the entire review — all comments, summaries and replies — in {language}. "
            f"Keep code identifiers, file paths, and code snippets unchanged."
        )
        return f"{prompt}\n\n{directive}"

    @classmethod
    def build_agent_request(
            cls,
            traces: list[AgentTraceSchema],
            force_final: bool,
            original_prompt: str,
            original_prompt_system: str,
            compaction_summary: str = "",
    ) -> str:
        mode = "Return FINAL only." if force_final else "You can either call a tool or return FINAL."
        history = format_traces(traces, max_chars=settings.agent.max_history_chars)
        agent_prompt = cls.prepare_prompt(settings.prompt.load_agent(), PromptContextSchema())

        summary_block = (
            f"## Progress summary (compacted)\n{compaction_summary}\n\n"
            if compaction_summary.strip()
            else ""
        )

        return (
            f"{agent_prompt}\n\n"
            f"## Agent mode\n{mode}\n\n"
            f"## Task output format\n{original_prompt_system}\n\n"
            f"## Task\n{original_prompt}\n\n"
            f"{summary_block}"
            f"## Agent history\n{history}\n\n"
        )

    @classmethod
    def build_agent_compaction_request(cls, traces: list[AgentTraceSchema], prior_summary: str = "") -> str:
        history = format_traces(traces, max_chars=None)
        parts = ["## Agent history\n" + history]
        if prior_summary.strip():
            parts.insert(0, f"## Prior progress summary\n{prior_summary.strip()}")

        return "\n\n".join(parts)

    @classmethod
    def build_system_agent_compaction_request(cls) -> str:
        return cls.prepare_prompt(settings.prompt.load_agent_compaction(), PromptContextSchema())

    # --- Agent-light (metadata-only) task prompts ---
    @staticmethod
    def _agent_light_metadata(context: PromptContextSchema, base_sha: str, head_sha: str) -> str:
        def join(values: list[str]) -> str:
            return ", ".join(v for v in values if v) or "-"

        return (
            "## Merge request metadata\n"
            f"- Title: {context.review_title or '-'}\n"
            f"- Description: {context.review_description or '-'}\n"
            f"- Author: {context.review_author_name or context.review_author_username or '-'}\n"
            f"- Reviewers: {join(context.review_reviewers)}\n"
            f"- Source branch: {context.source_branch or '-'}\n"
            f"- Target branch: {context.target_branch or '-'}\n"
            f"- Base SHA: {base_sha or '-'}\n"
            f"- Head SHA: {head_sha or '-'}\n"
            f"- Labels: {join(context.labels)}\n"
            f"- Changed files:\n"
            + "\n".join(f"  - {file}" for file in context.changed_files)
        )

    @classmethod
    def _agent_light_tool_guidance(cls, context: PromptContextSchema, base_sha: str, head_sha: str) -> str:
        base = base_sha or "<base>"
        head = head_sha or "<head>"
        return (
            "## How to gather context\n"
            "You start with metadata only — no diff or convention text is preloaded. "
            "Use read-only shell commands to pull in only what you need, then finalize:\n"
            f"- `git diff {base}..{head} -- path/to/file` — inspect a file's diff\n"
            "- `cat path/to/file`, `rg \"keyword\" .`, `head`, `tail`\n"
            "- `rg -n \"keyword\" path/to/conventions.md`, `sed -n '120,180p' path/to/conventions.md` "
            "to read only relevant convention sections\n\n"
            "Review ONLY the files listed under 'Changed files' above — this run may cover a subset "
            "of the merge request. Do not comment on files outside that list (another run handles them). "
            "Prefer narrow commands. Stop reading as soon as you have enough evidence and return FINAL."
        )

    @classmethod
    def build_agent_light_inline_request(
            cls,
            context: PromptContextSchema,
            base_sha: str,
            head_sha: str,
            conventions_inventory: str = "",
    ) -> str:
        instruction = cls.prepare_prompt(settings.prompt.load_agent_light_inline(), context)
        parts = [
            instruction,
            cls._agent_light_metadata(context, base_sha, head_sha),
            cls._agent_light_tool_guidance(context, base_sha, head_sha),
        ]
        if conventions_inventory.strip():
            parts.append(conventions_inventory.strip())

        prompt = "\n\n".join(parts)
        return cls.with_language(prompt)

    @classmethod
    def build_agent_light_summary_request(
            cls,
            context: PromptContextSchema,
            base_sha: str,
            head_sha: str,
            conventions_inventory: str = "",
    ) -> str:
        instruction = cls.prepare_prompt(settings.prompt.load_agent_light_summary(), context)
        parts = [
            instruction,
            cls._agent_light_metadata(context, base_sha, head_sha),
            cls._agent_light_tool_guidance(context, base_sha, head_sha),
        ]
        if conventions_inventory.strip():
            parts.append(conventions_inventory.strip())

        prompt = "\n\n".join(parts)
        return cls.with_language(prompt)

    @classmethod
    def build_agent_light_combined_request(
            cls,
            context: PromptContextSchema,
            base_sha: str,
            head_sha: str,
            conventions_inventory: str = "",
    ) -> str:
        instruction = cls.prepare_prompt(settings.prompt.load_agent_light_combined(), context)
        parts = [
            instruction,
            cls._agent_light_metadata(context, base_sha, head_sha),
            cls._agent_light_tool_guidance(context, base_sha, head_sha),
        ]
        if conventions_inventory.strip():
            parts.append(conventions_inventory.strip())

        prompt = "\n\n".join(parts)
        return cls.with_language(prompt)

    @classmethod
    def build_system_agent_light_inline_request(cls) -> str:
        return cls.prepare_prompt(settings.prompt.load_system_agent_light_inline(), PromptContextSchema())

    @classmethod
    def build_system_agent_light_summary_request(cls) -> str:
        return cls.prepare_prompt(settings.prompt.load_system_agent_light_summary(), PromptContextSchema())

    @classmethod
    def build_system_agent_light_combined_request(cls) -> str:
        return cls.prepare_prompt(settings.prompt.load_system_agent_light_combined(), PromptContextSchema())

    @classmethod
    def build_system_agent_request(cls) -> str:
        return cls.prepare_prompt(settings.prompt.load_system_agent(), PromptContextSchema())
