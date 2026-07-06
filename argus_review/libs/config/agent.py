import re

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    enabled: bool = False
    max_iterations: int = Field(default=25, ge=1, le=100)
    allow_commands: list[re.Pattern[str]] = Field(
        default_factory=lambda: [
            re.compile(r"^ls(?:\s+.*)?$"),
            re.compile(r"^cat(?:\s+.*)?$"),
            re.compile(r"^rg(?:\s+.*)?$"),
            re.compile(r"^grep(?:\s+.*)?$"),
            re.compile(r"^head(?:\s+.*)?$"),
            re.compile(r"^tail(?:\s+.*)?$"),
            re.compile(r"^wc(?:\s+.*)?$"),
            # Restricted to the read-only `-n ...p` print form so the agent can
            # inspect specific line ranges (e.g. convention sections) without the
            # in-place `-i` edit flag.
            re.compile(r"^sed\s+-n\s+.*$"),
            re.compile(r"^git\s+(?:status|show|diff|log|rev-parse|ls-files)(?:\s+.*)?$"),
        ]
    )
    command_timeout: int = Field(default=10, ge=1, le=120)
    max_total_context_chars: int = Field(default=40_000, ge=1_000, le=500_000)
    max_command_output_chars: int = Field(default=40_000, ge=1_000, le=500_000)
    # Caps how much agent-loop history (previous tool outputs) is re-sent into
    # each iteration's prompt. Older tool outputs are elided once the budget is
    # exceeded, keeping per-iteration token cost bounded.
    max_history_chars: int = Field(default=24_000, ge=1_000, le=500_000)
    # Hard budget on *actual* LLM token usage (prompt+completion) across the whole
    # agent loop. Unlike max_total_context_chars (which only tracks tool-output
    # chars), this bounds real provider-billed tokens directly — the metric the
    # quota guardrails are actually meant to protect. Default is a safety net
    # that rarely triggers on a well-behaved loop; lower it for tighter quotas.
    # 0 disables the check entirely (relies on max_iterations /
    # max_total_context_chars instead), since not every provider reports usage.
    max_total_tokens: int = Field(default=100_000, ge=0, le=10_000_000)
