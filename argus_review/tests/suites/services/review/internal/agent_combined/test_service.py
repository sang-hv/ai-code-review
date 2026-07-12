import pytest

from argus_review.services.review.internal.agent_combined.schema import AgentCombinedResultSchema
from argus_review.services.review.internal.agent_combined.service import AgentCombinedResultService


def test_parse_model_output_empty_returns_empty_result(agent_combined_result_service: AgentCombinedResultService):
    result = agent_combined_result_service.parse_model_output("")
    assert isinstance(result, AgentCombinedResultSchema)
    assert result.summary == ""
    assert result.comments == []


def test_parse_model_output_valid_json(agent_combined_result_service: AgentCombinedResultService):
    output = '{"summary":"Nice review","comments":[{"file":"a.py","line":1,"message":"m"}]}'

    result = agent_combined_result_service.parse_model_output(output)

    assert result.summary == "Nice review"
    assert len(result.comments) == 1
    assert result.comments[0].file == "a.py"


def test_parse_model_output_falls_back_to_summary_text_when_json_invalid(
        agent_combined_result_service: AgentCombinedResultService,
):
    output = "Overall this MR looks fine. Keep an eye on edge cases in checkout flow."

    result = agent_combined_result_service.parse_model_output(output)

    assert result.summary == output
    assert result.comments == []


def test_parse_model_output_recovers_inline_comments_from_plain_text(
        agent_combined_result_service: AgentCombinedResultService,
):
    output = (
        "General summary for this MR\n"
        "- src/app/main.py:42 - Handle null before rendering\n"
        "- src/lib/util.ts:10: Remove dead branch\n"
    )

    result = agent_combined_result_service.parse_model_output(output)

    assert result.summary == "General summary for this MR"
    assert len(result.comments) == 2
    assert result.comments[0].file == "src/app/main.py"
    assert result.comments[0].line == 42
    assert result.comments[1].file == "src/lib/util.ts"
    assert result.comments[1].line == 10
