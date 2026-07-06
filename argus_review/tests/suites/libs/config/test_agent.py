import pytest
from pydantic import ValidationError

from argus_review.libs.config.agent import AgentConfig


def test_agent_config_defaults() -> None:
    config = AgentConfig()
    assert config.enabled is False
    assert config.max_iterations == 25
    assert config.max_total_context_chars == 40_000
    assert config.command_timeout == 10
    assert config.max_command_output_chars == 40_000
    assert config.max_history_chars == 24_000
    assert len(config.allow_commands) > 0


def test_agent_config_rejects_invalid_limits() -> None:
    with pytest.raises(ValidationError):
        AgentConfig(max_iterations=0)

    with pytest.raises(ValidationError):
        AgentConfig(command_timeout=0)

    with pytest.raises(ValidationError):
        AgentConfig(max_history_chars=0)


def test_agent_config_default_allow_commands_patterns_are_stable() -> None:
    config = AgentConfig()
    patterns = [pattern.pattern for pattern in config.allow_commands]
    assert patterns == [
        r"^ls(?:\s+.*)?$",
        r"^cat(?:\s+.*)?$",
        r"^rg(?:\s+.*)?$",
        r"^grep(?:\s+.*)?$",
        r"^head(?:\s+.*)?$",
        r"^tail(?:\s+.*)?$",
        r"^wc(?:\s+.*)?$",
        r"^sed\s+-n\s+.*$",
        r"^git\s+(?:status|show|diff|log|rev-parse|ls-files)(?:\s+.*)?$",
    ]


def test_agent_config_default_allow_commands_match_expected_commands() -> None:
    config = AgentConfig()
    allowlist = config.allow_commands

    def is_allowed(command: str) -> bool:
        return any(pattern.fullmatch(command) for pattern in allowlist)

    assert is_allowed("ls")
    assert is_allowed("ls -la")
    assert is_allowed("cat README.md")
    assert is_allowed("rg TODO argus_review")
    assert is_allowed("grep -R foo .")
    assert is_allowed("head -n 40 file.py")
    assert is_allowed("tail -n 40 file.py")
    assert is_allowed("wc -l app/main.py")
    assert is_allowed("sed -n '120,180p' docs/conventions.md")
    assert is_allowed("git status")
    assert is_allowed("git diff --name-only")
    assert is_allowed("git rev-parse HEAD")

    # sed is restricted to the read-only `-n` print form (no in-place editing).
    assert not is_allowed("sed -i 's/a/b/' file.py")
    assert not is_allowed("python -c 'print(1)'")
    assert not is_allowed("git checkout main")
    assert not is_allowed("")
