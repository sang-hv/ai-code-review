import pytest

from argus_review.services.review.internal.agent_combined.schema import AgentCombinedResultSchema
from argus_review.services.review.internal.inline.schema import InlineCommentSchema
from argus_review.services.review.runner.agent_combined import AgentReviewRunner
from argus_review.services.vcs.types import ReviewCommentSchema
from argus_review.tests.fixtures.services.policy import FakePolicyService
from argus_review.tests.fixtures.services.review.internal.agent_combined import FakeAgentCombinedResultService
from argus_review.tests.fixtures.services.prompt import FakePromptService
from argus_review.tests.fixtures.services.review.gateway.review_comment_gateway import FakeReviewCommentGateway
from argus_review.tests.fixtures.services.review.gateway.review_direct_llm_gateway import FakeReviewDirectLLMGateway
from argus_review.tests.fixtures.services.vcs import FakeVCSClient


@pytest.mark.asyncio
async def test_run_happy_path_posts_summary_and_inline_from_single_ask(
        agent_review_runner: AgentReviewRunner,
        fake_vcs_client: FakeVCSClient,
        fake_prompt_service: FakePromptService,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    """A single agent session must produce both the summary and inline comments."""
    fake_review_comment_gateway.responses["get_inline_comments"] = []
    fake_review_comment_gateway.responses["get_summary_comments"] = []

    await agent_review_runner.run()

    assert any(call[0] == "get_review_info" for call in fake_vcs_client.calls)
    assert any(call[0] == "build_agent_light_combined_request" for call in fake_prompt_service.calls)
    assert any(call[0] == "build_system_agent_light_combined_request" for call in fake_prompt_service.calls)

    # Exactly one LLM call for the whole review (summary + inline together).
    ask_calls = [call for call in fake_review_direct_llm_gateway.calls if call[0] == "ask"]
    assert len(ask_calls) == 1

    assert any(call[0] == "process_inline_comments" for call in fake_review_comment_gateway.calls)
    assert any(call[0] == "process_summary_comment" for call in fake_review_comment_gateway.calls)

    summary_calls = [
        call for call in fake_review_comment_gateway.calls if call[0] == "process_summary_comment"
    ]
    assert summary_calls[0][1]["comment"].text == "Fake combined summary"


@pytest.mark.asyncio
async def test_run_skips_entirely_when_both_already_have_comments(
        agent_review_runner: AgentReviewRunner,
        fake_vcs_client: FakeVCSClient,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    fake_review_comment_gateway.responses["get_inline_comments"] = [
        ReviewCommentSchema(id="1", body="#ai-review-inline existing"),
    ]
    fake_review_comment_gateway.responses["get_summary_comments"] = [
        ReviewCommentSchema(id="2", body="#ai-review-summary existing"),
    ]

    await agent_review_runner.run()

    assert not any(call[0] == "get_review_info" for call in fake_vcs_client.calls)
    assert not any(call[0] == "ask" for call in fake_review_direct_llm_gateway.calls)


@pytest.mark.asyncio
async def test_run_only_posts_summary_when_inline_already_exists(
        agent_review_runner: AgentReviewRunner,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    fake_review_comment_gateway.responses["get_inline_comments"] = [
        ReviewCommentSchema(id="1", body="#ai-review-inline existing"),
    ]
    fake_review_comment_gateway.responses["get_summary_comments"] = []

    await agent_review_runner.run()

    assert any(call[0] == "ask" for call in fake_review_direct_llm_gateway.calls)
    assert not any(call[0] == "process_inline_comments" for call in fake_review_comment_gateway.calls)
    assert any(call[0] == "process_summary_comment" for call in fake_review_comment_gateway.calls)


@pytest.mark.asyncio
async def test_run_only_posts_inline_when_summary_already_exists(
        agent_review_runner: AgentReviewRunner,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    fake_review_comment_gateway.responses["get_inline_comments"] = []
    fake_review_comment_gateway.responses["get_summary_comments"] = [
        ReviewCommentSchema(id="2", body="#ai-review-summary existing"),
    ]

    await agent_review_runner.run()

    assert any(call[0] == "ask" for call in fake_review_direct_llm_gateway.calls)
    assert any(call[0] == "process_inline_comments" for call in fake_review_comment_gateway.calls)
    assert not any(call[0] == "process_summary_comment" for call in fake_review_comment_gateway.calls)


@pytest.mark.asyncio
async def test_run_skips_when_no_changed_files(
        agent_review_runner: AgentReviewRunner,
        fake_policy_service: FakePolicyService,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    fake_policy_service.responses["apply_for_files"] = []
    fake_review_comment_gateway.responses["get_inline_comments"] = []
    fake_review_comment_gateway.responses["get_summary_comments"] = []

    await agent_review_runner.run()

    assert not any(call[0] == "ask" for call in fake_review_direct_llm_gateway.calls)


@pytest.mark.asyncio
async def test_run_skips_inline_posting_when_no_valid_comments(
        agent_review_runner: AgentReviewRunner,
        fake_agent_combined_result_service: FakeAgentCombinedResultService,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    fake_review_comment_gateway.responses["get_inline_comments"] = []
    fake_review_comment_gateway.responses["get_summary_comments"] = []
    fake_agent_combined_result_service.result = AgentCombinedResultSchema(summary="Only text", comments=[])

    await agent_review_runner.run()

    assert not any(call[0] == "process_inline_comments" for call in fake_review_comment_gateway.calls)
    assert any(call[0] == "process_summary_comment" for call in fake_review_comment_gateway.calls)


@pytest.mark.asyncio
async def test_run_skips_summary_posting_when_summary_empty(
        agent_review_runner: AgentReviewRunner,
        fake_agent_combined_result_service: FakeAgentCombinedResultService,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    fake_review_comment_gateway.responses["get_inline_comments"] = []
    fake_review_comment_gateway.responses["get_summary_comments"] = []
    fake_agent_combined_result_service.result = AgentCombinedResultSchema(
        summary="",
        comments=[InlineCommentSchema(file="main.py", line=1, message="x")],
    )

    await agent_review_runner.run()

    assert any(call[0] == "process_inline_comments" for call in fake_review_comment_gateway.calls)
    assert not any(call[0] == "process_summary_comment" for call in fake_review_comment_gateway.calls)


@pytest.mark.asyncio
async def test_run_posts_fallback_summary_when_both_summary_and_inline_empty(
        agent_review_runner: AgentReviewRunner,
        fake_agent_combined_result_service: FakeAgentCombinedResultService,
        fake_review_comment_gateway: FakeReviewCommentGateway,
):
    fake_review_comment_gateway.responses["get_inline_comments"] = []
    fake_review_comment_gateway.responses["get_summary_comments"] = []
    fake_agent_combined_result_service.result = AgentCombinedResultSchema(summary="", comments=[])

    await agent_review_runner.run()

    summary_calls = [
        call for call in fake_review_comment_gateway.calls if call[0] == "process_summary_comment"
    ]
    assert len(summary_calls) == 1
    assert "model output was empty" in summary_calls[0][1]["comment"].text


# === Chunking (Phase 3) ===

def test_chunk_helper_splits_correctly():
    from argus_review.services.review.runner.chunk import _chunk

    assert _chunk(["a.py", "b.py", "c.py"], 2) == [["a.py", "b.py"], ["c.py"]]
    assert _chunk(["a.py", "b.py"], 5) == [["a.py", "b.py"]]
    assert _chunk(["a.py", "b.py"], 0) == [["a.py", "b.py"]]
    assert _chunk([], 2) == [[]]


@pytest.mark.asyncio
async def test_no_chunking_when_disabled(
        monkeypatch: pytest.MonkeyPatch,
        agent_review_runner: AgentReviewRunner,
        fake_vcs_client: FakeVCSClient,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    """max_files_per_chunk=0 (default) must keep the single-session behavior."""
    monkeypatch.setattr("argus_review.config.settings.agent.max_files_per_chunk", 0)
    fake_review_comment_gateway.responses["get_inline_comments"] = []
    fake_review_comment_gateway.responses["get_summary_comments"] = []

    await agent_review_runner.run()

    ask_calls = [call for call in fake_review_direct_llm_gateway.calls if call[0] == "ask"]
    assert len(ask_calls) == 1


@pytest.mark.asyncio
async def test_chunks_when_over_limit(
        monkeypatch: pytest.MonkeyPatch,
        agent_review_runner: AgentReviewRunner,
        fake_agent_combined_result_service: FakeAgentCombinedResultService,
        fake_vcs_client: FakeVCSClient,
        fake_review_comment_gateway: FakeReviewCommentGateway,
        fake_review_direct_llm_gateway: FakeReviewDirectLLMGateway,
):
    """With 5 files and max_files_per_chunk=2, expect 3 chunk sessions; comments/summaries are merged."""
    from argus_review.services.vcs.types import ReviewInfoSchema

    monkeypatch.setattr("argus_review.config.settings.agent.max_files_per_chunk", 2)

    fake_vcs_client.responses["get_review_info"] = ReviewInfoSchema(
        changed_files=["a.py", "b.py", "c.py", "d.py", "e.py"],
        base_sha="A",
        head_sha="B",
    )
    fake_review_comment_gateway.responses["get_inline_comments"] = []
    fake_review_comment_gateway.responses["get_summary_comments"] = []

    results = [
        AgentCombinedResultSchema(
            summary=f"summary-{i}",
            comments=[InlineCommentSchema(file=f"f{i}.py", line=1, message=f"c{i}")],
        )
        for i in range(3)
    ]

    call_count = {"n": 0}
    original_parse = fake_agent_combined_result_service.parse_model_output

    def parse_sequence(output: str) -> AgentCombinedResultSchema:
        original_parse(output)
        result = results[call_count["n"]]
        call_count["n"] += 1
        return result

    monkeypatch.setattr(fake_agent_combined_result_service, "parse_model_output", parse_sequence)

    await agent_review_runner.run()

    ask_calls = [call for call in fake_review_direct_llm_gateway.calls if call[0] == "ask"]
    assert len(ask_calls) == 3

    inline_calls = [
        call for call in fake_review_comment_gateway.calls if call[0] == "process_inline_comments"
    ]
    assert len(inline_calls) == 1
    posted_files = {comment.file for comment in inline_calls[0][1]["comments"].root}
    assert posted_files == {"f0.py", "f1.py", "f2.py"}

    summary_calls = [
        call for call in fake_review_comment_gateway.calls if call[0] == "process_summary_comment"
    ]
    assert summary_calls[0][1]["comment"].text == "summary-0\n\nsummary-1\n\nsummary-2"
