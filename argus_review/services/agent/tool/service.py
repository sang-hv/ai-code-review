import shlex
import subprocess
import re
from pathlib import Path

from argus_review.config import settings
from argus_review.libs.logger import get_logger
from argus_review.libs.text import truncate_text
from argus_review.services.agent.tool.types import AgentToolServiceProtocol
from argus_review.services.policy.types import PolicyServiceProtocol

logger = get_logger("AGENT_TOOL_SERVICE")

_COMMAND_SPLIT_RE = re.compile(r"\s*(?:;|&&|\|\||\|)\s*")

# Filters that read from stdin when given no file argument — running them
# standalone (recovered from a pipeline) would block until timeout.
_STDIN_FILTERS = {"head", "tail", "wc", "grep", "sed", "sort", "uniq", "cut", "awk", "xargs", "tr"}


def _needs_stdin(candidate: str) -> bool:
    """True when the candidate is a bare filter (e.g. 'head -50') that would hang without stdin."""
    try:
        argv = shlex.split(candidate)
    except ValueError:
        return False
    if not argv or argv[0] not in _STDIN_FILTERS:
        return False

    # Any non-flag argument after the program name is treated as a file operand.
    return not any(not arg.startswith("-") for arg in argv[1:])


def _rewrite_rg_to_grep(argv: list[str]) -> list[str] | None:
    """
    Best-effort fallback when `rg` is not installed.
    Maps common `rg` forms to portable `grep -R -n` equivalents.
    """
    if not argv or argv[0] != "rg":
        return None

    pattern: str | None = None
    paths: list[str] = []
    grep_flags: list[str] = ["-R", "-n"]

    index = 1
    while index < len(argv):
        token = argv[index]

        if token in {"-n", "--line-number", "--no-heading", "--hidden"}:
            index += 1
            continue

        if token in {"-l", "--files-with-matches"}:
            grep_flags.append("-l")
            index += 1
            continue

        if token in {"-i", "--ignore-case"}:
            grep_flags.append("-i")
            index += 1
            continue

        if token in {"-F", "--fixed-strings"}:
            grep_flags.append("-F")
            index += 1
            continue

        if token == "--type":
            # Skip type value (grep fallback does not enforce file-type filter).
            index += 2
            continue

        if token.startswith("-"):
            # Handle compact short-flags such as -rn or -ni.
            if token.startswith("--"):
                return None

            supported_letters = {"n", "r", "H", "h"}
            for letter in token[1:]:
                if letter == "i":
                    grep_flags.append("-i")
                elif letter == "F":
                    grep_flags.append("-F")
                elif letter == "l":
                    grep_flags.append("-l")
                elif letter in supported_letters:
                    # Keep as no-op for grep fallback (`-n` already defaulted,
                    # `-r` equivalent covered by `-R`).
                    pass
                else:
                    return None

            index += 1
            continue

        if pattern is None:
            pattern = token
        else:
            paths.append(token)

        index += 1

    if not pattern:
        return None

    if not paths:
        paths = ["."]

    return ["grep", *grep_flags, "--", pattern, *paths]


class AgentToolService(AgentToolServiceProtocol):
    def __init__(
            self,
            policy: PolicyServiceProtocol,
            repo_dir: Path = Path(".")
    ):
        self.policy = policy
        self.repo_root = repo_dir.resolve()

        self.command_timeout = settings.agent.command_timeout
        self.max_command_output_chars = settings.agent.max_command_output_chars

    def _recover_allowed_subcommand(self, command: str) -> str | None:
        """
        Try to recover a single read-only command when the model emits a
        compound shell command (e.g. "pwd; ls -la; git status | head -20").
        """
        parts = [part.strip() for part in _COMMAND_SPLIT_RE.split(command) if part.strip()]
        if len(parts) <= 1:
            return None

        for candidate in parts:
            if _needs_stdin(candidate):
                logger.debug(f"Skipping recovered candidate that needs stdin: {candidate}")
                continue
            if self.policy.should_agent_run_command(candidate):
                return candidate

        return None

    async def execute(self, command: str) -> str:
        command = (command or "").strip()
        original_command = command

        if not command:
            logger.warning("Agent command rejected: empty command")
            return "Agent command rejected: empty command"

        if not self.policy.should_agent_run_command(command):
            recovered = self._recover_allowed_subcommand(command)
            if recovered is None:
                logger.warning(f"Agent command blocked by policy: {command}")
                return f"Agent command blocked by policy: {command}"

            logger.warning(
                f"Agent command blocked by policy, recovered subcommand: "
                f"original='{command}' -> recovered='{recovered}'"
            )
            command = recovered

        command_preview = f"{self.repo_root}#{command}"

        try:
            argv = shlex.split(command)
        except ValueError as error:
            logger.warning(f"Agent command parse error: {command} | {error}")
            return f"Agent command parse error: {command} | {error}"
        if not argv:
            logger.warning(f"Agent command rejected after parsing: {command}")
            return f"Agent command rejected after parsing: {command}"

        logger.debug(f"Running agent command: {command_preview}, timeout={self.command_timeout}s")
        try:
            result = subprocess.run(
                argv,
                cwd=self.repo_root,
                check=False,
                errors="replace",
                timeout=self.command_timeout,
                encoding="utf-8",
                capture_output=True,
            )
        except FileNotFoundError as error:
            if argv and argv[0] == "rg":
                fallback_argv = _rewrite_rg_to_grep(argv)
                if fallback_argv is not None:
                    fallback_command = " ".join(shlex.quote(token) for token in fallback_argv)
                    logger.warning(
                        f"Agent command fallback: 'rg' not found, retrying with grep: {fallback_command}"
                    )
                    command = fallback_command
                    command_preview = f"{self.repo_root}#{command}"
                    result = subprocess.run(
                        fallback_argv,
                        cwd=self.repo_root,
                        check=False,
                        errors="replace",
                        timeout=self.command_timeout,
                        encoding="utf-8",
                        capture_output=True,
                    )
                else:
                    logger.warning(f"Agent command failed: {command_preview}:{error}")
                    return f"Agent command failed: {command_preview}:{error}"
            else:
                logger.warning(f"Agent command failed: {command_preview}:{error}")
                return f"Agent command failed: {command_preview}:{error}"
        except subprocess.TimeoutExpired:
            logger.warning(f"Agent command timeout: {command_preview}, timeout={self.command_timeout}s")
            return f"Agent command timeout: {command_preview}, timeout={self.command_timeout}s"
        except Exception as error:
            logger.exception(f"Agent command failed: {command_preview}:{error}")
            return f"Agent command failed: {command_preview}:{error}"

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        logger.debug(
            f"Agent command finished: {command_preview}, exit_code={result.returncode}, "
            f"stdout_chars={len(stdout)}, stderr_chars={len(stderr)}"
        )

        output = (
            f"command: {command}\n"
            f"exit_code: {result.returncode}\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}"
        )
        if original_command != command:
            output = f"original_command: {original_command}\n{output}"

        truncated = len(output) > self.max_command_output_chars
        if truncated:
            logger.debug(
                "Agent command output truncated: "
                f"{command}, payload_chars={len(output)}, limit={self.max_command_output_chars}"
            )

        return truncate_text(text=output, limit=self.max_command_output_chars)
