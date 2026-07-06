from argus_review.services.agent.loop.schema import AgentAction, AgentStepSchema, AgentTraceSchema
from argus_review.services.prompt.tools import format_traces


def _tool_trace(iteration: int, command: str, output: str) -> AgentTraceSchema:
    return AgentTraceSchema(
        step=AgentStepSchema(action=AgentAction.TOOL_CALL, command=command),
        iteration=iteration,
        raw_output="raw",
        tool_output=output,
    )


def test_format_traces_without_budget_keeps_all_output():
    traces = [_tool_trace(1, "cat a", "X" * 500), _tool_trace(2, "cat b", "Y" * 500)]
    rendered = format_traces(traces)
    assert "X" * 500 in rendered
    assert "Y" * 500 in rendered


def test_format_traces_elides_old_output_over_budget():
    old = _tool_trace(1, "cat old", "O" * 5000)
    recent = _tool_trace(2, "cat recent", "R" * 200)

    rendered = format_traces([old, recent], max_chars=1000)

    # Recent step stays in full; the older large output is elided.
    assert "R" * 200 in rendered
    assert "O" * 5000 not in rendered
    assert "[elided to save context]" in rendered


def test_format_traces_preserves_chronological_order():
    old = _tool_trace(1, "cat old", "O" * 5000)
    recent = _tool_trace(2, "cat recent", "R" * 200)

    rendered = format_traces([old, recent], max_chars=1000)
    assert rendered.index("Iteration: 1") < rendered.index("Iteration: 2")


def test_format_traces_empty_with_budget():
    assert format_traces([], max_chars=1000) == "No previous steps."
