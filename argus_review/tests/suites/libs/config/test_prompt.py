from pathlib import Path

import pytest

from argus_review.libs.config.prompt import PromptConfig, resolve_prompt_files, resolve_system_prompt_files


# ---------- resolve_prompt_files ----------

def test_resolve_prompt_files_returns_given_list(tmp_path: Path):
    dummy_file = tmp_path / "file.md"
    result = resolve_prompt_files([dummy_file], "default_inline.md")
    assert result == [dummy_file]


def test_resolve_prompt_files_loads_default_when_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dummy_file = tmp_path / "inline_default.md"
    dummy_file.write_text("INLINE_DEFAULT")
    monkeypatch.setattr("argus_review.libs.config.prompt.load_resource", lambda **_: dummy_file)

    result = resolve_prompt_files(None, "default_inline.md")
    assert result == [dummy_file]


# ---------- resolve_system_prompt_files ----------

def test_resolve_system_prompt_files_none_returns_global(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    dummy_file = tmp_path / "sys.md"
    dummy_file.write_text("SYS")
    monkeypatch.setattr("argus_review.libs.config.prompt.load_resource", lambda **_: dummy_file)

    result = resolve_system_prompt_files(None, include=True, default_file="default_system_inline.md")
    assert result == [dummy_file]


def test_resolve_system_prompt_files_include_true(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    global_file = tmp_path / "global.md"
    global_file.write_text("GLOBAL")
    custom_file = tmp_path / "custom.md"
    monkeypatch.setattr("argus_review.libs.config.prompt.load_resource", lambda **_: global_file)

    result = resolve_system_prompt_files([custom_file], include=True, default_file="default_system_inline.md")
    assert result == [global_file, custom_file]


def test_resolve_system_prompt_files_include_false(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    global_file = tmp_path / "global.md"
    global_file.write_text("GLOBAL")
    custom_file = tmp_path / "custom.md"
    monkeypatch.setattr("argus_review.libs.config.prompt.load_resource", lambda **_: global_file)

    result = resolve_system_prompt_files([custom_file], include=False, default_file="default_system_inline.md")
    assert result == [custom_file]


# ---------- Agent Prompts ----------

def test_load_agent_prompts_from_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    dummy_file = tmp_path / "agent.md"
    dummy_file.write_text("AGENT")
    monkeypatch.setattr("argus_review.libs.config.prompt.load_resource", lambda **_: dummy_file)

    config = PromptConfig()
    assert config.agent_prompt_files_or_default == [dummy_file]
    assert config.load_agent() == ["AGENT"]


def test_load_agent_prompts_from_custom_files(tmp_path: Path):
    custom_file = tmp_path / "custom_agent.md"
    custom_file.write_text("CUSTOM_AGENT")

    config = PromptConfig(agent_prompt_files=[custom_file])
    assert config.agent_prompt_files_or_default == [custom_file]
    assert config.load_agent() == ["CUSTOM_AGENT"]


# ---------- System Prompts ----------

def test_load_system_agent_prompts_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    global_file = tmp_path / "global_sys_agent.md"
    global_file.write_text("GLOBAL_SYS_AGENT")
    monkeypatch.setattr("argus_review.libs.config.prompt.load_resource", lambda **_: global_file)

    config = PromptConfig()
    assert config.system_agent_prompt_files_or_default == [global_file]
    assert config.load_system_agent() == ["GLOBAL_SYS_AGENT"]


def test_load_system_agent_prompts_include_true(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    global_file = tmp_path / "global_sys_agent.md"
    global_file.write_text("GLOBAL_SYS_AGENT")
    custom_file = tmp_path / "custom_sys_agent.md"
    custom_file.write_text("CUSTOM_SYS_AGENT")
    monkeypatch.setattr("argus_review.libs.config.prompt.load_resource", lambda **_: global_file)

    config = PromptConfig(system_agent_prompt_files=[custom_file], include_agent_system_prompts=True)
    assert config.system_agent_prompt_files_or_default == [global_file, custom_file]
    assert config.load_system_agent() == ["GLOBAL_SYS_AGENT", "CUSTOM_SYS_AGENT"]


def test_load_system_agent_prompts_include_false(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    global_file = tmp_path / "global_sys_agent.md"
    global_file.write_text("GLOBAL_SYS_AGENT")
    custom_file = tmp_path / "custom_sys_agent.md"
    custom_file.write_text("CUSTOM_SYS_AGENT")
    monkeypatch.setattr("argus_review.libs.config.prompt.load_resource", lambda **_: global_file)

    config = PromptConfig(system_agent_prompt_files=[custom_file], include_agent_system_prompts=False)
    assert config.system_agent_prompt_files_or_default == [custom_file]
    assert config.load_system_agent() == ["CUSTOM_SYS_AGENT"]


# ---------- Agent-light Prompts ----------

def test_load_agent_light_inline_prompts_from_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    dummy_file = tmp_path / "agent_light_inline.md"
    dummy_file.write_text("AGENT_LIGHT_INLINE")
    monkeypatch.setattr("argus_review.libs.config.prompt.load_resource", lambda **_: dummy_file)

    config = PromptConfig()
    assert config.agent_light_inline_prompt_files_or_default == [dummy_file]
    assert config.load_agent_light_inline() == ["AGENT_LIGHT_INLINE"]


def test_load_agent_light_inline_prompts_from_custom_files(tmp_path: Path):
    custom_file = tmp_path / "custom_agent_light_inline.md"
    custom_file.write_text("CUSTOM_AGENT_LIGHT_INLINE")

    config = PromptConfig(agent_light_inline_prompt_files=[custom_file])
    assert config.agent_light_inline_prompt_files_or_default == [custom_file]
    assert config.load_agent_light_inline() == ["CUSTOM_AGENT_LIGHT_INLINE"]


def test_load_agent_light_summary_prompts_from_custom_files(tmp_path: Path):
    custom_file = tmp_path / "custom_agent_light_summary.md"
    custom_file.write_text("CUSTOM_AGENT_LIGHT_SUMMARY")

    config = PromptConfig(agent_light_summary_prompt_files=[custom_file])
    assert config.agent_light_summary_prompt_files_or_default == [custom_file]
    assert config.load_agent_light_summary() == ["CUSTOM_AGENT_LIGHT_SUMMARY"]


def test_load_system_agent_light_prompts_from_custom_files(tmp_path: Path):
    inline_file = tmp_path / "sys_agent_light_inline.md"
    inline_file.write_text("SYS_AGENT_LIGHT_INLINE")
    summary_file = tmp_path / "sys_agent_light_summary.md"
    summary_file.write_text("SYS_AGENT_LIGHT_SUMMARY")

    config = PromptConfig(
        system_agent_light_inline_prompt_files=[inline_file],
        system_agent_light_summary_prompt_files=[summary_file],
    )
    assert config.load_system_agent_light_inline() == ["SYS_AGENT_LIGHT_INLINE"]
    assert config.load_system_agent_light_summary() == ["SYS_AGENT_LIGHT_SUMMARY"]


def test_load_system_agent_light_prompts_from_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    dummy_file = tmp_path / "sys_agent_light.md"
    dummy_file.write_text("SYS_AGENT_LIGHT_DEFAULT")
    monkeypatch.setattr("argus_review.libs.config.prompt.load_resource", lambda **_: dummy_file)

    config = PromptConfig()
    assert config.load_system_agent_light_inline() == ["SYS_AGENT_LIGHT_DEFAULT"]
