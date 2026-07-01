import os
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from argus_review.cli.main import app
from argus_review.services.review.service import ReviewService

runner = CliRunner()


def test_cli_module_import_does_not_require_config_file(tmp_path):
    """
    Importing the CLI module should not eagerly load runtime settings.
    """
    excluded_keys = {
        "AI_REVIEW_CONFIG_FILE_ENV",
        "AI_REVIEW_CONFIG_FILE_YAML",
        "AI_REVIEW_CONFIG_FILE_JSON",
    }
    excluded_prefixes = (
        "LLM__",
        "VCS__",
        "CORE__",
        "AGENT__",
        "PROMPT__",
        "REVIEW__",
        "LOGGER__",
        "ARTIFACTS__",
    )
    preserved_keys = {
        "PATH",
        "PYTHONPATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",
        "__PYVENV_LAUNCHER__",
    }
    env = {
        key: value
        for key, value in os.environ.items()
        if (
            key in preserved_keys
            and key not in excluded_keys
            and not key.startswith(excluded_prefixes)
        )
    }
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    python_path_parts = [repo_root]
    if env.get("PYTHONPATH"):
        python_path_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_path_parts)

    result = subprocess.run(
        [sys.executable, "-c", "import argus_review.cli.main"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.fixture(autouse=True)
def dummy_review_service(monkeypatch: pytest.MonkeyPatch, review_service: ReviewService):
    monkeypatch.setattr("argus_review.cli.commands.run_review.ReviewService", lambda: review_service)
    monkeypatch.setattr("argus_review.cli.commands.run_inline_review.ReviewService", lambda: review_service)
    monkeypatch.setattr("argus_review.cli.commands.run_context_review.ReviewService", lambda: review_service)
    monkeypatch.setattr("argus_review.cli.commands.run_summary_review.ReviewService", lambda: review_service)
    monkeypatch.setattr("argus_review.cli.commands.run_inline_reply_review.ReviewService", lambda: review_service)
    monkeypatch.setattr("argus_review.cli.commands.run_summary_reply_review.ReviewService", lambda: review_service)


@pytest.mark.parametrize(
    "args, expected_output",
    [
        (["run"], "Starting full AI review..."),
        (["run-inline"], "Starting inline AI review..."),
        (["run-context"], "Starting context AI review..."),
        (["run-summary"], "Starting summary AI review..."),
        (["run-inline-reply"], "Starting inline reply AI review..."),
        (["run-summary-reply"], "Starting summary reply AI review..."),
    ],
)
def test_cli_commands_invoke_review_service_successfully(args: list[str], expected_output: str):
    """
    Ensure CLI commands correctly call the ReviewService with fake dependencies.
    """
    result = runner.invoke(app, args)

    assert result.exit_code == 0
    assert expected_output in result.output
    assert "AI review completed successfully!" in result.output


def test_show_config_outputs_json(monkeypatch: pytest.MonkeyPatch):
    """
    Validate that the 'show-config' command prints settings as JSON.
    """
    monkeypatch.setattr(
        "argus_review.config.settings.model_dump_json",
        lambda **_: '{"debug": true}'
    )

    result = runner.invoke(app, ["show-config"])
    assert result.exit_code == 0
    assert "Loaded ArgusReview configuration" in result.output
    assert '{"debug": true}' in result.output
