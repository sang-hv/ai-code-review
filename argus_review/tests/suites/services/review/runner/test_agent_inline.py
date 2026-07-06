import pytest

from argus_review.services.review.internal.inline.schema import InlineCommentSchema
from argus_review.services.review.runner.agent_inline import AgentInlineReviewRunner
from argus_review.services.vcs.types import ReviewCommentSchema, ReviewInfoSchema
from argus_review.tests.fixtures.services.policy import FakePolicyService
from argus_review.tests.fixtures.services.prompt import FakePromptService
from argus_review.tests.fixtures.services.review.gateway.review_comment_gateway import FakeReviewCommentGateway
from argus_review.tests.fixtures.services.review.gateway.review_direct_llm_gateway import FakeReviewDirectLLMGateway
from argus_review.tests.fixtures.services.vcs import FakeVCSClient


@pytest.mark.asyncio
async def test_run_happy_path(
        agent_inline_review_runner: AgentInlineReviewRunner,
        fake_vcs_client: FakeVCSClient,
        fake_prompt_service: FakePromptService,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    """One agent session across all files → single ask, inline comments posted."""
    fake_review_comment_gateway.responses["get_inline_comments"] = []

    await agent_inline_review_runner.run()

    assert any(call[0] == "get_review_info" for call in fake_vcs_client.calls)
    assert any(call[0] == "build_agent_light_inline_request" for call in fake_prompt_service.calls)
    assert any(call[0] == "build_system_agent_light_inline_request" for call in fake_prompt_service.calls)

    # Exactly one LLM call for the whole review (not one per file).
    ask_calls = [call for call in fake_review_direct_llm_gateway.calls if call[0] == "ask"]
    assert len(ask_calls) == 1
    assert any(call[0] == "process_inline_comments" for call in fake_review_comment_gateway.calls)
    # No per-file inline prompt building.
    assert not any(call[0] == "build_inline_request" for call in fake_prompt_service.calls)


@pytest.mark.asyncio
async def test_run_skips_when_existing_comments(
        agent_inline_review_runner: AgentInlineReviewRunner,
        fake_vcs_client: FakeVCSClient,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    fake_review_comment_gateway.responses["get_inline_comments"] = [
        ReviewCommentSchema(id="1", body="#ai-review-inline existing"),
    ]

    await agent_inline_review_runner.run()

    assert fake_vcs_client.calls == []
    assert not any(call[0] == "ask" for call in fake_review_direct_llm_gateway.calls)


@pytest.mark.asyncio
async def test_run_skips_when_no_changed_files(
        agent_inline_review_runner: AgentInlineReviewRunner,
        fake_policy_service: FakePolicyService,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    fake_policy_service.responses["apply_for_files"] = []
    fake_review_comment_gateway.responses["get_inline_comments"] = []

    await agent_inline_review_runner.run()

    assert not any(call[0] == "ask" for call in fake_review_direct_llm_gateway.calls)


def test_validate_line_numbers_drops_non_diff_anchors(
        agent_inline_review_runner: AgentInlineReviewRunner,
        monkeypatch: pytest.MonkeyPatch,
):
    """Comments whose (file, line) do not anchor to a real diff line are dropped."""
    review_info = ReviewInfoSchema(base_sha="A", head_sha="B")
    monkeypatch.setattr(
        agent_inline_review_runner,
        "_valid_lines_by_file",
        lambda _info: {"app/main.py": {10, 11, 12}},
    )

    comments = [
        InlineCommentSchema(file="app/main.py", line=11, message="valid"),
        InlineCommentSchema(file="app/main.py", line=99, message="bad line"),
        InlineCommentSchema(file="other.py", line=1, message="unknown file"),
    ]
    kept = agent_inline_review_runner._validate_line_numbers(comments, review_info)

    assert len(kept) == 1
    assert kept[0].line == 11
    assert kept[0].file == "app/main.py"


def test_validate_line_numbers_lenient_when_map_empty(
        agent_inline_review_runner: AgentInlineReviewRunner,
        monkeypatch: pytest.MonkeyPatch,
):
    """When the diff can't be parsed (empty map), keep all comments rather than dropping everything."""
    review_info = ReviewInfoSchema(base_sha="A", head_sha="B")
    monkeypatch.setattr(agent_inline_review_runner, "_valid_lines_by_file", lambda _info: {})

    comments = [InlineCommentSchema(file="a.py", line=5, message="x")]
    kept = agent_inline_review_runner._validate_line_numbers(comments, review_info)
    assert kept == comments
