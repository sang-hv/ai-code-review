import pytest

from argus_review.config import settings
from argus_review.services.review.gateway.review_comment_gateway import ReviewCommentGateway
from argus_review.services.review.internal.inline.schema import InlineCommentSchema, InlineCommentListSchema
from argus_review.services.review.internal.summary.schema import SummaryCommentSchema
from argus_review.services.vcs.types import ReviewCommentSchema
from argus_review.tests.fixtures.services.artifacts import FakeArtifactsService
from argus_review.tests.fixtures.services.vcs import FakeVCSClient


# === GET INLINE COMMENTS ===

@pytest.mark.asyncio
async def test_get_inline_comments_filters_only_ai_comments(
        fake_vcs_client: FakeVCSClient,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should return only inline comments containing AI inline tag."""
    fake_vcs_client.responses["get_inline_comments"] = [
        ReviewCommentSchema(id="1", body=f"{settings.review.inline_tag} AI comment"),
        ReviewCommentSchema(id="2", body="Regular inline comment"),
    ]

    result = await review_comment_gateway.get_inline_comments()

    assert len(result) == 1
    assert result[0].id == "1"

    assert any(call[0] == "get_inline_comments" for call in fake_vcs_client.calls)


@pytest.mark.asyncio
async def test_get_inline_comments_returns_empty_when_no_ai_comments(
        fake_vcs_client: FakeVCSClient,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should return empty list when no AI inline comments exist."""
    fake_vcs_client.responses["get_inline_comments"] = [
        ReviewCommentSchema(id="1", body="Just a comment"),
    ]

    result = await review_comment_gateway.get_inline_comments()

    assert result == []


# === GET SUMMARY COMMENTS ===

@pytest.mark.asyncio
async def test_get_summary_comments_filters_only_ai_comments(
        fake_vcs_client: FakeVCSClient,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should return only summary comments containing AI summary tag."""
    fake_vcs_client.responses["get_general_comments"] = [
        ReviewCommentSchema(id="10", body=f"{settings.review.summary_tag} AI summary"),
        ReviewCommentSchema(id="11", body="Regular summary"),
    ]

    result = await review_comment_gateway.get_summary_comments()

    assert len(result) == 1
    assert result[0].id == "10"

    assert any(call[0] == "get_general_comments" for call in fake_vcs_client.calls)


@pytest.mark.asyncio
async def test_get_summary_comments_returns_empty_when_no_ai_comments(
        fake_vcs_client: FakeVCSClient,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should return empty list when no AI summary comments exist."""
    fake_vcs_client.responses["get_general_comments"] = [
        ReviewCommentSchema(id="1", body="Regular comment"),
    ]

    result = await review_comment_gateway.get_summary_comments()

    assert result == []


# === INLINE COMMENT ===

@pytest.mark.asyncio
async def test_process_inline_comment_happy_path(
        fake_vcs_client: FakeVCSClient,
        fake_artifacts_service: FakeArtifactsService,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should create inline comment via VCS."""
    comment = InlineCommentSchema(file="f.py", line=1, message="AI inline comment")
    await review_comment_gateway.process_inline_comment(comment)
    assert any(call[0] == "create_inline_comment" for call in fake_vcs_client.calls)

    assert ("save_vcs_inline", {"comment": comment}) in fake_artifacts_service.calls
    assert all(call[0] != "save_vcs_summary" for call in fake_artifacts_service.calls)


@pytest.mark.asyncio
async def test_process_inline_comment_error_fallback(
        capsys: pytest.CaptureFixture,
        fake_vcs_client: FakeVCSClient,
        fake_artifacts_service: FakeArtifactsService,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should fall back to inline fallback comment when inline comment fails."""

    async def failing_create_inline_comment(file: str, line: int, message: str):
        raise RuntimeError("Failed to post inline")

    fake_vcs_client.create_inline_comment = failing_create_inline_comment

    comment = InlineCommentSchema(file="x.py", line=5, message="AI inline")
    await review_comment_gateway.process_inline_comment(comment)
    output = capsys.readouterr().out

    assert "Falling back to general comment" in output
    assert any(call[0] == "create_general_comment" for call in fake_vcs_client.calls)

    fallback_call = next(call for call in fake_vcs_client.calls if call[0] == "create_general_comment")
    posted_body = fallback_call[1][0]
    assert settings.review.inline_fallback_tag in posted_body
    assert settings.review.summary_tag not in posted_body

    assert all(call[0] != "save_vcs_inline" for call in fake_artifacts_service.calls)
    assert any(call[0] == "save_vcs_summary" for call in fake_artifacts_service.calls)


# === SUMMARY COMMENT ===

@pytest.mark.asyncio
async def test_process_summary_comment_happy_path(
        fake_vcs_client: FakeVCSClient,
        fake_artifacts_service: FakeArtifactsService,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should create general summary comment successfully."""
    comment = SummaryCommentSchema(text="AI summary")
    await review_comment_gateway.process_summary_comment(comment)
    assert any(call[0] == "create_general_comment" for call in fake_vcs_client.calls)

    assert ("save_vcs_summary", {"comment": comment}) in fake_artifacts_service.calls


@pytest.mark.asyncio
async def test_process_summary_comment_error(
        capsys: pytest.CaptureFixture,
        fake_vcs_client: FakeVCSClient,
        fake_artifacts_service: FakeArtifactsService,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should log error if summary comment creation fails."""

    async def failing_create_general_comment(body: str):
        raise RuntimeError("Backend down")

    fake_vcs_client.create_general_comment = failing_create_general_comment

    comment = SummaryCommentSchema(text="Broken")
    await review_comment_gateway.process_summary_comment(comment)
    output = capsys.readouterr().out

    assert "Failed to process summary comment" in output

    assert all(call[0] != "save_vcs_summary" for call in fake_artifacts_service.calls)


# === INLINE FALLBACK COMMENT ===

@pytest.mark.asyncio
async def test_process_inline_fallback_comment_happy_path(
        fake_vcs_client: FakeVCSClient,
        fake_artifacts_service: FakeArtifactsService,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should create general comment with inline fallback tag."""
    comment = SummaryCommentSchema(text="**x.py:42** — missing check")
    await review_comment_gateway.process_inline_fallback_comment(comment)

    assert any(call[0] == "create_general_comment" for call in fake_vcs_client.calls)

    fallback_call = next(call for call in fake_vcs_client.calls if call[0] == "create_general_comment")
    posted_body = fallback_call[1][0]
    assert settings.review.inline_fallback_tag in posted_body
    assert settings.review.summary_tag not in posted_body

    assert ("save_vcs_summary", {"comment": comment}) in fake_artifacts_service.calls


@pytest.mark.asyncio
async def test_process_inline_fallback_comment_error(
        capsys: pytest.CaptureFixture,
        fake_vcs_client: FakeVCSClient,
        fake_artifacts_service: FakeArtifactsService,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should log error if inline fallback comment creation fails."""

    async def failing_create_general_comment(body: str):
        raise RuntimeError("Backend down")

    fake_vcs_client.create_general_comment = failing_create_general_comment

    comment = SummaryCommentSchema(text="Broken fallback")
    await review_comment_gateway.process_inline_fallback_comment(comment)
    output = capsys.readouterr().out

    assert "Failed to process inline fallback comment" in output

    assert all(call[0] != "save_vcs_summary" for call in fake_artifacts_service.calls)


@pytest.mark.asyncio
async def test_process_inline_comments_calls_each(
        fake_vcs_client: FakeVCSClient,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should process all inline comments concurrently."""
    comments = InlineCommentListSchema(root=[
        InlineCommentSchema(file="a.py", line=1, message="c1"),
        InlineCommentSchema(file="b.py", line=2, message="c2"),
    ])

    await review_comment_gateway.process_inline_comments(comments)

    created = [call for call in fake_vcs_client.calls if call[0] == "create_inline_comment"]
    assert len(created) == 2


@pytest.mark.asyncio
async def test_process_inline_comment_error_no_fallback_when_disabled(
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        fake_vcs_client: FakeVCSClient,
        fake_artifacts_service: FakeArtifactsService,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should NOT fall back to summary comment when inline fallback is disabled."""
    monkeypatch.setattr(settings.review, "inline_comment_fallback", False)

    async def failing_create_inline_comment(file: str, line: int, message: str):
        raise RuntimeError("Failed to post inline")

    fake_vcs_client.create_inline_comment = failing_create_inline_comment

    comment = InlineCommentSchema(file="x.py", line=10, message="AI inline")
    await review_comment_gateway.process_inline_comment(comment)
    output = capsys.readouterr().out

    assert "Failed to process inline comment" in output
    assert "Falling back to general comment" not in output

    assert all(call[0] != "create_general_comment" for call in fake_vcs_client.calls)
    assert all(call[0] != "save_vcs_summary" for call in fake_artifacts_service.calls)
    assert all(call[0] != "save_vcs_inline" for call in fake_artifacts_service.calls)


@pytest.mark.asyncio
async def test_clear_inline_comments_deletes_all_ai_comments(
        fake_vcs_client: FakeVCSClient,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should delete all existing AI inline comments."""
    fake_vcs_client.responses["get_inline_comments"] = [
        ReviewCommentSchema(id="1", body=f"{settings.review.inline_tag} comment 1"),
        ReviewCommentSchema(id="2", body=f"{settings.review.inline_tag} comment 2"),
    ]

    await review_comment_gateway.clear_inline_comments()

    deleted = [call for call in fake_vcs_client.calls if call[0] == "delete_inline_comment"]
    assert len(deleted) == 2
    assert {call[1][0] for call in deleted} == {"1", "2"}


@pytest.mark.asyncio
async def test_clear_inline_comments_noop_when_no_comments(
        fake_vcs_client: FakeVCSClient,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should not call delete when no inline AI comments exist."""
    fake_vcs_client.responses["get_inline_comments"] = []

    await review_comment_gateway.clear_inline_comments()

    assert all(call[0] != "delete_inline_comment" for call in fake_vcs_client.calls)


@pytest.mark.asyncio
async def test_clear_summary_comments_deletes_all_ai_comments(
        fake_vcs_client: FakeVCSClient,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should delete all existing AI summary comments."""
    fake_vcs_client.responses["get_general_comments"] = [
        ReviewCommentSchema(id="10", body=f"{settings.review.summary_tag} summary 1"),
        ReviewCommentSchema(id="11", body=f"{settings.review.summary_tag} summary 2"),
    ]

    await review_comment_gateway.clear_summary_comments()

    deleted = [call for call in fake_vcs_client.calls if call[0] == "delete_general_comment"]
    assert len(deleted) == 2
    assert {call[1][0] for call in deleted} == {"10", "11"}


@pytest.mark.asyncio
async def test_clear_summary_comments_noop_when_no_comments(
        fake_vcs_client: FakeVCSClient,
        review_comment_gateway: ReviewCommentGateway,
):
    """Should not call delete when no summary AI comments exist."""
    fake_vcs_client.responses["get_general_comments"] = []

    await review_comment_gateway.clear_summary_comments()

    assert all(call[0] != "delete_general_comment" for call in fake_vcs_client.calls)


@pytest.mark.asyncio
async def test_get_summary_comments_excludes_fallback_comments(
        fake_vcs_client: FakeVCSClient,
        review_comment_gateway: ReviewCommentGateway,
):
    """Summary comments detection should not include fallback-tagged comments."""
    fake_vcs_client.responses["get_general_comments"] = [
        ReviewCommentSchema(id="10", body=f"Summary {settings.review.summary_tag}"),
        ReviewCommentSchema(id="11", body=f"Fallback {settings.review.inline_fallback_tag}"),
    ]

    result = await review_comment_gateway.get_summary_comments()

    assert len(result) == 1
    assert result[0].id == "10"
