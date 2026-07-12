import subprocess
from pathlib import Path

import pytest

from argus_review.config import settings
from argus_review.services.agent.tool.service import AgentToolService
from argus_review.tests.fixtures.services.policy import FakePolicyService


@pytest.mark.asyncio
async def test_execute_runs_allowed_command(
        tmp_path: Path,
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
) -> None:
    (tmp_path / "sample.txt").write_text("hello", encoding="utf-8")
    fake_policy_service.responses["should_agent_run_command"] = True

    result = await agent_tool_service.execute("cat sample.txt")

    assert "exit_code: 0" in result
    assert "hello" in result
    assert any(call[0] == "should_agent_run_command" for call in fake_policy_service.calls)


@pytest.mark.asyncio
async def test_execute_blocks_disallowed_command(
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
) -> None:
    fake_policy_service.responses["should_agent_run_command"] = False

    result = await agent_tool_service.execute("cat sample.txt")

    assert "blocked by policy" in result.lower()


@pytest.mark.asyncio
async def test_execute_runs_in_repo_directory(
        tmp_path: Path,
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
) -> None:
    (tmp_path / "visible.txt").write_text("ok", encoding="utf-8")
    fake_policy_service.responses["should_agent_run_command"] = True

    result = await agent_tool_service.execute("ls")

    assert "visible.txt" in result


@pytest.mark.asyncio
async def test_execute_truncates_large_output(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
) -> None:
    huge = "x" * 5_000
    (tmp_path / "big.txt").write_text(huge, encoding="utf-8")
    fake_policy_service.responses["should_agent_run_command"] = True
    monkeypatch.setattr(settings.agent, "max_command_output_chars", 1_000)
    agent_tool_service.max_command_output_chars = 1_000

    result = await agent_tool_service.execute("cat big.txt")

    assert "output truncated" in result


@pytest.mark.asyncio
async def test_execute_rejects_empty_command(agent_tool_service: AgentToolService) -> None:
    result = await agent_tool_service.execute("   ")
    assert "empty command" in result.lower()


@pytest.mark.asyncio
async def test_execute_rejects_none_command(agent_tool_service: AgentToolService) -> None:
    result = await agent_tool_service.execute(None)  # noqa
    assert "empty command" in result.lower()


@pytest.mark.asyncio
async def test_execute_returns_parse_error_for_invalid_shell_syntax(
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
) -> None:
    fake_policy_service.responses["should_agent_run_command"] = True

    result = await agent_tool_service.execute('"unterminated')

    assert "parse error" in result.lower()


@pytest.mark.asyncio
async def test_execute_returns_timeout_error(
        monkeypatch: pytest.MonkeyPatch,
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
) -> None:
    fake_policy_service.responses["should_agent_run_command"] = True

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["ls"], timeout=0.01)

    monkeypatch.setattr(subprocess, "run", _raise_timeout)
    result = await agent_tool_service.execute("ls")

    assert "timeout" in result.lower()


@pytest.mark.asyncio
async def test_execute_returns_runtime_error(
        monkeypatch: pytest.MonkeyPatch,
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
) -> None:
    fake_policy_service.responses["should_agent_run_command"] = True

    def _raise_runtime_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(subprocess, "run", _raise_runtime_error)
    result = await agent_tool_service.execute("ls")

    assert "failed" in result.lower()


@pytest.mark.asyncio
async def test_execute_captures_non_zero_exit_code(
        tmp_path: Path,
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
) -> None:
    fake_policy_service.responses["should_agent_run_command"] = True

    result = await agent_tool_service.execute("cat nonexistent_file.txt")

    assert "exit_code: 1" in result or "exit_code: 2" in result
    assert "no such file" in result.lower() or "not found" in result.lower()


@pytest.mark.asyncio
async def test_execute_captures_stderr(
        tmp_path: Path,
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
) -> None:
    fake_policy_service.responses["should_agent_run_command"] = True

    result = await agent_tool_service.execute("ls nonexistent_dir")

    assert "stderr:" in result
    assert "no such file" in result.lower() or "not found" in result.lower()


@pytest.mark.asyncio
async def test_execute_recovers_allowed_subcommand_from_compound_command(
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    def selective_policy(command: str) -> bool:
        command = (command or "").strip()
        return command in {"ls -la", "git status 2>&1"}

    monkeypatch.setattr(fake_policy_service, "should_agent_run_command", selective_policy)

    result = await agent_tool_service.execute("pwd; ls -la; git status 2>&1 | head -20")

    assert "original_command:" in result
    assert "command: ls -la" in result
    assert "exit_code: 0" in result


@pytest.mark.asyncio
async def test_execute_recovery_skips_bare_stdin_filters(
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bare filter like 'head -50' (no file operand) must not be recovered — it would hang on stdin."""
    def selective_policy(command: str) -> bool:
        command = (command or "").strip()
        # Policy would allow 'head -50', but recovery must skip it (needs stdin).
        return command in {"head -50", "ls -la"}

    monkeypatch.setattr(fake_policy_service, "should_agent_run_command", selective_policy)

    result = await agent_tool_service.execute("find . -name '*.ts' | head -50")

    assert "blocked by policy" in result.lower()


@pytest.mark.asyncio
async def test_execute_recovery_allows_filter_with_file_operand(
        tmp_path: Path,
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "a.txt").write_text("line1\nline2\n", encoding="utf-8")

    def selective_policy(command: str) -> bool:
        return (command or "").strip() == "head -1 a.txt"

    monkeypatch.setattr(fake_policy_service, "should_agent_run_command", selective_policy)

    result = await agent_tool_service.execute("pwd; head -1 a.txt")

    assert "command: head -1 a.txt" in result
    assert "line1" in result


@pytest.mark.asyncio
async def test_execute_falls_back_to_grep_when_rg_missing(
        monkeypatch: pytest.MonkeyPatch,
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
) -> None:
    fake_policy_service.responses["should_agent_run_command"] = True

    original_run = subprocess.run

    def fake_run(*args, **kwargs):
        argv = args[0]
        if argv[0] == "rg":
            raise FileNotFoundError("[Errno 2] No such file or directory: 'rg'")
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = await agent_tool_service.execute("rg -n foo .")

    assert "command: grep -R -n -- foo ." in result


@pytest.mark.asyncio
async def test_execute_falls_back_to_grep_when_rg_missing_with_compact_flags(
        monkeypatch: pytest.MonkeyPatch,
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
) -> None:
    fake_policy_service.responses["should_agent_run_command"] = True

    original_run = subprocess.run

    def fake_run(*args, **kwargs):
        argv = args[0]
        if argv[0] == "rg":
            raise FileNotFoundError("[Errno 2] No such file or directory: 'rg'")
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = await agent_tool_service.execute("rg -rn foo . --no-heading")

    assert "command: grep -R -n -- foo ." in result


@pytest.mark.asyncio
async def test_execute_falls_back_to_grep_when_rg_missing_with_list_flag(
        monkeypatch: pytest.MonkeyPatch,
        agent_tool_service: AgentToolService,
        fake_policy_service: FakePolicyService,
) -> None:
    fake_policy_service.responses["should_agent_run_command"] = True

    original_run = subprocess.run

    def fake_run(*args, **kwargs):
        argv = args[0]
        if argv[0] == "rg":
            raise FileNotFoundError("[Errno 2] No such file or directory: 'rg'")
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = await agent_tool_service.execute("rg -n foo . --no-heading -l")

    assert "command: grep -R -n -l -- foo ." in result
