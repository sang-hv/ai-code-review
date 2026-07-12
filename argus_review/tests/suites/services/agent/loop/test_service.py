import pytest

from argus_review.services.agent.loop.service import AgentLoopService
from argus_review.services.llm.types import ChatResultSchema
from argus_review.tests.fixtures.services.agent.tool import FakeAgentToolService
from argus_review.tests.fixtures.services.llm import FakeLLMClient
from argus_review.tests.fixtures.services.prompt import FakePromptService


def sequence_chat(outputs: list[str]):
    async def chat(prompt: str, prompt_system: str) -> ChatResultSchema:
        return ChatResultSchema(text=outputs.pop(0))

    return chat


def sequence_chat_results(outputs: list[ChatResultSchema]):
    async def chat(prompt: str, prompt_system: str) -> ChatResultSchema:
        return outputs.pop(0)

    return chat


@pytest.mark.asyncio
async def test_run_returns_final_when_llm_returns_final(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat(['{"action":"FINAL","content":"done"}']),
    )

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.final_text == "done"
    assert result.stop_reason == "final"
    assert len(result.traces) == 1
    assert fake_agent_tool_service.calls == []


@pytest.mark.asyncio
async def test_run_returns_unstructured_response_when_json_parse_fails(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat(["not-json"]),
    )

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "unstructured_response"
    assert result.final_text == "not-json"
    assert "Failed to parse structured action" in (result.traces[0].warning or "")
    assert fake_agent_tool_service.calls == []


@pytest.mark.asyncio
async def test_run_recovers_tool_call_from_unstructured_bash_output(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            "bash\ngit rev-parse HEAD",
            '{"action":"FINAL","content":"done"}',
        ]),
    )
    fake_agent_tool_service.responses["execute"] = "8e122c9d40bc81846ae98bf2f0b113a4f0a01c4f"

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "final"
    assert result.final_text == "done"
    assert fake_agent_tool_service.calls == [("execute", {"command": "git rev-parse HEAD"})]
    assert "Recovered from unstructured model output" in (result.traces[0].warning or "")


@pytest.mark.asyncio
async def test_run_recovers_diff_fallback_tool_call_from_unstructured_text(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            "I need the diff output to continue. I cannot proceed without full diff.",
            '{"action":"FINAL","content":"done"}',
        ]),
    )
    fake_agent_tool_service.responses["execute"] = "src/main.py"

    result = await agent_loop_service.run(
        "## Merge request metadata\n- Base SHA: a41c336965580592edfc5a07577da0beb82c8ae6\n"
        "- Head SHA: 8e122c9d40bc81846ae98bf2f0b113a4f0a01c4f",
        "SYSTEM",
    )

    assert result.stop_reason == "final"
    assert result.final_text == "done"
    assert fake_agent_tool_service.calls == [(
        "execute",
        {"command": "git diff --name-only a41c336965580592edfc5a07577da0beb82c8ae6..8e122c9d40bc81846ae98bf2f0b113a4f0a01c4f"},
    )]


@pytest.mark.asyncio
async def test_run_recovers_command_from_malformed_tool_call_json(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    """TOOL_CALL JSON with unescaped quotes in command must be recovered, not end the loop."""
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            '{"action":"TOOL_CALL","command":"rg "useMemo" src/ 2>/dev/null | head"}',
            '{"action":"FINAL","content":"done"}',
        ]),
    )
    fake_agent_tool_service.responses["execute"] = "match"

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "final"
    assert result.final_text == "done"
    assert fake_agent_tool_service.calls == [
        ("execute", {"command": 'rg "useMemo" src/ 2>/dev/null | head'})
    ]


@pytest.mark.asyncio
async def test_force_final_handles_empty_fallback_response(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    """An empty force-final response must not raise a schema validation error."""
    agent_loop_service.max_iterations = 1
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            '{"action":"TOOL_CALL","command":"ls"}',
            "",
        ]),
    )

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "max_requests_or_context_limit"
    assert result.final_text == ""


@pytest.mark.asyncio
async def test_run_recovers_tool_call_from_malformed_final_content(        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            '{"action":"FINAL","content":"bash\\ngit diff --name-only"}',
            '{"action":"FINAL","content":"done"}',
        ]),
    )
    fake_agent_tool_service.responses["execute"] = "src/a.py\nsrc/b.py"

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "final"
    assert result.final_text == "done"
    assert fake_agent_tool_service.calls == [("execute", {"command": "git diff --name-only"})]
    assert "Recovered TOOL_CALL from malformed FINAL content" in (result.traces[0].warning or "")


@pytest.mark.asyncio
async def test_run_executes_tool_call_then_returns_final(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            '{"action":"TOOL_CALL","command":"rg foo src"}',
            '{"action":"FINAL","content":"review-complete"}',
        ]),
    )
    fake_agent_tool_service.responses["execute"] = "match-line"

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "final"
    assert result.final_text == "review-complete"
    assert len(result.traces) == 2
    assert fake_agent_tool_service.calls == [("execute", {"command": "rg foo src"})]
    assert result.traces[0].tool_output == "match-line"


@pytest.mark.asyncio
async def test_run_prefers_structured_tool_command_from_llm_result(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat_results([
            ChatResultSchema(
                text="this is not json",
                tool_command="git diff --name-only",
            ),
            ChatResultSchema(text='{"action":"FINAL","content":"done"}'),
        ]),
    )
    fake_agent_tool_service.responses["execute"] = "src/a.py"

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "final"
    assert result.final_text == "done"
    assert fake_agent_tool_service.calls == [("execute", {"command": "git diff --name-only"})]


@pytest.mark.asyncio
async def test_run_ignores_structured_tool_command_when_disabled(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    agent_loop_service.structured_tool_calls_enabled = False
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat_results([
            ChatResultSchema(
                text="this is not json",
                tool_command="git diff --name-only",
            ),
        ]),
    )

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "unstructured_response"
    assert fake_agent_tool_service.calls == []


@pytest.mark.asyncio
async def test_run_does_not_recover_unstructured_step_when_disabled(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    agent_loop_service.unstructured_recovery_enabled = False
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat(["bash\ngit rev-parse HEAD"]),
    )

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "unstructured_response"
    assert fake_agent_tool_service.calls == []


@pytest.mark.asyncio
async def test_run_blocks_duplicate_tool_call_signature(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            '{"action":"TOOL_CALL","command":"ls"}',
            '{"action":"TOOL_CALL","command":"ls"}',
            '{"action":"FINAL","content":"done"}',
        ]),
    )

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.final_text == "done"
    assert len(fake_agent_tool_service.calls) == 1
    assert "Duplicate tool call blocked" in (result.traces[1].warning or "")


@pytest.mark.asyncio
async def test_run_forces_final_when_context_limit_reached(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_prompt_service: FakePromptService,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            '{"action":"TOOL_CALL","command":"cat big.txt"}',
            '{"action":"FINAL","content":"forced-final"}',
        ]),
    )
    fake_agent_tool_service.responses["execute"] = "0123456789"
    agent_loop_service.max_context_chars = 1
    agent_loop_service.compaction_enabled = False

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "max_requests_or_context_limit"
    assert result.final_text == "forced-final"
    assert any(
        call[0] == "build_agent_request" and call[1]["force_final"] is True
        for call in fake_prompt_service.calls
    )


@pytest.mark.asyncio
async def test_force_final_returns_raw_when_forced_response_is_not_final_json(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            '{"action":"TOOL_CALL","command":"cat big.txt"}',
            '{"action":"TOOL_CALL","command":"cat big.txt"}',
        ]),
    )
    fake_agent_tool_service.responses["execute"] = "0123456789"
    agent_loop_service.max_context_chars = 1
    agent_loop_service.compaction_enabled = False

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "max_requests_or_context_limit"
    assert result.final_text == '{"action":"TOOL_CALL","command":"cat big.txt"}'


@pytest.mark.asyncio
async def test_run_clears_token_usage_between_runs(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    agent_loop_service.max_total_tokens = 1_000

    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat_results([
            ChatResultSchema(
                text='{"action":"TOOL_CALL","command":"ls"}',
                total_tokens=1_200,
                prompt_tokens=700,
                completion_tokens=500,
            ),
            ChatResultSchema(text='{"action":"FINAL","content":"forced"}'),
        ]),
    )
    first = await agent_loop_service.run("PROMPT", "SYSTEM")
    assert first.stop_reason == "max_requests_or_context_limit"

    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat(['{"action":"FINAL","content":"clean-run"}']),
    )
    second = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert second.stop_reason == "final"
    assert second.final_text == "clean-run"
    assert agent_loop_service.tokens_used == 0


@pytest.mark.asyncio
async def test_run_clears_internal_state_between_runs(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            '{"action":"TOOL_CALL","command":"ls"}',
            '{"action":"FINAL","content":"one"}',
        ]),
    )
    await agent_loop_service.run("PROMPT", "SYSTEM")

    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            '{"action":"TOOL_CALL","command":"ls"}',
            '{"action":"FINAL","content":"two"}',
        ]),
    )
    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.final_text == "two"
    assert fake_agent_tool_service.calls.count(("execute", {"command": "ls"})) == 2


@pytest.mark.asyncio
async def test_run_forces_final_when_max_iterations_reached(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_prompt_service: FakePromptService,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            '{"action":"TOOL_CALL","command":"ls"}',
            '{"action":"TOOL_CALL","command":"cat a.py"}',
            '{"action":"FINAL","content":"forced"}',
        ]),
    )
    agent_loop_service.max_iterations = 2

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "max_requests_or_context_limit"
    assert result.final_text == "forced"
    assert any(
        call[0] == "build_agent_request" and call[1]["force_final"] is True
        for call in fake_prompt_service.calls
    )


@pytest.mark.asyncio
async def test_run_handles_coerced_list_content_as_final(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat(['{"action":"FINAL","content":[]}']),
    )

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "final"
    assert result.final_text == "[]"


@pytest.mark.asyncio
async def test_run_retries_after_empty_llm_response(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
) -> None:
    """An empty LLM response should be retried on the next iteration, not end the loop."""
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            "",
            '{"action":"FINAL","content":"done-after-empty"}',
        ]),
    )

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "final"
    assert result.final_text == "done-after-empty"


@pytest.mark.asyncio
async def test_run_forces_final_when_all_responses_empty(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
) -> None:
    """If every iteration returns empty output, the loop exhausts and force-finals."""
    agent_loop_service.max_iterations = 2
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            "",
            "",
            '{"action":"FINAL","content":"forced"}',
        ]),
    )

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "max_requests_or_context_limit"
    assert result.final_text == "forced"


@pytest.mark.asyncio
async def test_run_forces_final_when_token_budget_reached(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_prompt_service: FakePromptService,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat_results([
            ChatResultSchema(
                text='{"action":"TOOL_CALL","command":"ls"}',
                total_tokens=100,
                prompt_tokens=60,
                completion_tokens=40,
            ),
            ChatResultSchema(text='{"action":"FINAL","content":"forced-final"}'),
        ]),
    )
    agent_loop_service.max_total_tokens = 50

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "max_requests_or_context_limit"
    assert result.final_text == "forced-final"
    assert any(
        call[0] == "build_agent_request" and call[1]["force_final"] is True
        for call in fake_prompt_service.calls
    )


@pytest.mark.asyncio
async def test_run_does_not_force_final_on_tokens_when_budget_disabled(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    """max_total_tokens=0 must disable the token budget check entirely (no cap)."""
    agent_loop_service.max_total_tokens = 0

    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat_results([
            ChatResultSchema(
                text='{"action":"TOOL_CALL","command":"ls"}',
                total_tokens=1_000_000,
                prompt_tokens=900_000,
                completion_tokens=100_000,
            ),
            ChatResultSchema(text='{"action":"FINAL","content":"done"}'),
        ]),
    )

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "final"
    assert result.final_text == "done"


@pytest.mark.asyncio
async def test_run_persists_llm_tokens_in_traces(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat_results([
            ChatResultSchema(
                text='{"action":"TOOL_CALL","command":"ls"}',
                total_tokens=30,
                prompt_tokens=10,
                completion_tokens=20,
            ),
            ChatResultSchema(
                text='{"action":"FINAL","content":"done"}',
                total_tokens=15,
                prompt_tokens=5,
                completion_tokens=10,
            ),
        ]),
    )

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.final_text == "done"
    assert result.traces[0].prompt_tokens == 10
    assert result.traces[0].completion_tokens == 20
    assert result.traces[1].prompt_tokens == 5
    assert result.traces[1].completion_tokens == 10
    assert result.prompt_tokens == 15
    assert result.completion_tokens == 30
    assert result.total_tokens == 45


@pytest.mark.asyncio
async def test_compaction_triggered_when_threshold_reached(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_prompt_service: FakePromptService,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    """When context_used crosses the compaction threshold, compact and keep looping (no early break)."""
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat_results([
            # First tool call pushes context_used past the (tiny) threshold.
            ChatResultSchema(text='{"action":"TOOL_CALL","command":"cat big.txt"}'),
            # Compaction call (build_agent_compaction_request -> llm.chat).
            ChatResultSchema(text="progress: inspected big.txt"),
            # Loop continues with a fresh iteration and returns FINAL.
            ChatResultSchema(text='{"action":"FINAL","content":"done-after-compaction"}'),
        ]),
    )
    fake_agent_tool_service.responses["execute"] = "0123456789"
    agent_loop_service.max_context_chars = 1_000
    agent_loop_service.compaction_enabled = True
    agent_loop_service.compaction_threshold = 1

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "final"
    assert result.final_text == "done-after-compaction"
    assert any(call[0] == "build_agent_compaction_request" for call in fake_prompt_service.calls)
    assert any(call[0] == "build_system_agent_compaction_request" for call in fake_prompt_service.calls)
    assert agent_loop_service.compaction_summary == "progress: inspected big.txt"


@pytest.mark.asyncio
async def test_compaction_disabled_forces_final(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_prompt_service: FakePromptService,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    """With compaction disabled, reaching the context limit forces a final response (previous behavior)."""
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat([
            '{"action":"TOOL_CALL","command":"cat big.txt"}',
            '{"action":"FINAL","content":"forced-final"}',
        ]),
    )
    fake_agent_tool_service.responses["execute"] = "0123456789"
    agent_loop_service.max_context_chars = 1
    agent_loop_service.compaction_enabled = False

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "max_requests_or_context_limit"
    assert result.final_text == "forced-final"
    assert not any(call[0] == "build_agent_compaction_request" for call in fake_prompt_service.calls)


@pytest.mark.asyncio
async def test_compact_resets_context_and_sets_summary(
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
) -> None:
    """Calling compact() directly should summarize, reset context, and keep signatures intact."""
    agent_loop_service.context_used = 500
    agent_loop_service.signatures.add("ls")

    await agent_loop_service.compact()

    assert agent_loop_service.compaction_summary != ""
    assert agent_loop_service.context_used == 0
    assert agent_loop_service.traces == []
    assert "ls" in agent_loop_service.signatures


@pytest.mark.asyncio
async def test_run_forces_final_when_compaction_summary_is_empty(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_prompt_service: FakePromptService,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat_results([
            ChatResultSchema(text='{"action":"TOOL_CALL","command":"cat big.txt"}'),
            ChatResultSchema(text=""),
            ChatResultSchema(text='{"action":"FINAL","content":"forced-after-empty-compaction"}'),
        ]),
    )
    fake_agent_tool_service.responses["execute"] = "0123456789"
    agent_loop_service.max_context_chars = 1_000
    agent_loop_service.compaction_enabled = True
    agent_loop_service.compaction_threshold = 1

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "max_requests_or_context_limit"
    assert result.final_text == "forced-after-empty-compaction"
    assert any(call[0] == "build_agent_compaction_request" for call in fake_prompt_service.calls)


@pytest.mark.asyncio
async def test_run_forces_final_when_compaction_cap_reached(
        monkeypatch: pytest.MonkeyPatch,
        agent_loop_service: AgentLoopService,
        fake_llm_client: FakeLLMClient,
        fake_prompt_service: FakePromptService,
        fake_agent_tool_service: FakeAgentToolService,
) -> None:
    monkeypatch.setattr(
        fake_llm_client,
        "chat",
        sequence_chat_results([
            ChatResultSchema(text='{"action":"TOOL_CALL","command":"cat a.txt"}'),
            ChatResultSchema(text="first summary"),
            ChatResultSchema(text='{"action":"TOOL_CALL","command":"cat b.txt"}'),
            ChatResultSchema(text='{"action":"FINAL","content":"forced-after-cap"}'),
        ]),
    )
    fake_agent_tool_service.responses["execute"] = "0123456789"
    agent_loop_service.max_context_chars = 1_000
    agent_loop_service.compaction_enabled = True
    agent_loop_service.compaction_threshold = 1
    agent_loop_service.max_compactions_per_run = 1

    result = await agent_loop_service.run("PROMPT", "SYSTEM")

    assert result.stop_reason == "max_requests_or_context_limit"
    assert result.final_text == "forced-after-cap"
    compaction_calls = [call for call in fake_prompt_service.calls if call[0] == "build_agent_compaction_request"]
    assert len(compaction_calls) == 1
