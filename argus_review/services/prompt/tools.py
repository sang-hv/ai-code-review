import re

from argus_review.libs.logger import get_logger
from argus_review.services.agent.loop.schema import AgentTraceSchema
from argus_review.services.diff.schema import DiffFileSchema
from argus_review.services.vcs.types import ReviewThreadSchema

logger = get_logger("PROMPT_TOOLS")


def format_file(diff: DiffFileSchema) -> str:
    return f"# File: {diff.file}\n{diff.diff}\n"


def format_files(diffs: list[DiffFileSchema]) -> str:
    return "\n\n".join(map(format_file, diffs))


def format_thread(thread: ReviewThreadSchema) -> str:
    if not thread.comments:
        return "No comments in thread."

    lines: list[str] = []
    for comment in thread.comments:
        user = (comment.author.name or comment.author.username or "User").strip()
        body = (comment.body or "").strip()
        if not body:
            continue

        lines.append(f"- {user}: {body}")

    return "\n\n".join(lines)


def normalize_prompt(text: str) -> str:
    tails_stripped = [re.sub(r"[ \t]+$", "", line) for line in text.splitlines()]
    text = "\n".join(tails_stripped)

    text = re.sub(r"\n{3,}", "\n\n", text)

    result = text.strip()
    if len(text) > len(result):
        logger.info(f"Prompt has been normalized from {len(text)} to {len(result)}")
        return result

    return text


def format_trace(trace: AgentTraceSchema) -> str:
    lines = [f"Iteration: {trace.iteration}"]

    if trace.step.command:
        lines.append(f"Command: {trace.step.command}")

    if trace.tool_output:
        lines.append(f"Tool output: {trace.tool_output}")

    if trace.step.content:
        lines.append(f"Content: {trace.step.content}")

    if trace.warning:
        lines.append(f"Warning: {trace.warning}")

    return "\n".join(lines)


def format_trace_compact(trace: AgentTraceSchema) -> str:
    """Like `format_trace` but with the (large) tool output elided."""
    lines = [f"Iteration: {trace.iteration}"]

    if trace.step.command:
        lines.append(f"Command: {trace.step.command}")

    if trace.tool_output:
        lines.append("Tool output: [elided to save context]")

    if trace.warning:
        lines.append(f"Warning: {trace.warning}")

    return "\n".join(lines)


def format_traces(traces: list[AgentTraceSchema], max_chars: int | None = None) -> str:
    if not traces:
        return "No previous steps."

    if max_chars is None:
        return "\n\n---\n\n".join(map(format_trace, traces))

    # Keep the most recent steps in full and elide older tool outputs once the
    # running budget is exceeded, so re-sent history stays bounded per iteration.
    rendered: dict[int, str] = {}
    used = 0
    for index in range(len(traces) - 1, -1, -1):
        full = format_trace(traces[index])
        if used + len(full) <= max_chars:
            rendered[index] = full
            used += len(full)
        else:
            compact = format_trace_compact(traces[index])
            rendered[index] = compact
            used += len(compact)

    return "\n\n---\n\n".join(rendered[index] for index in range(len(traces)))
