import pytest

from argus_review.config import settings
from argus_review.services.review.gateway.review_dry_run_comment_gateway import ReviewDryRunCommentGateway
from argus_review.services.review.internal.inline.schema import InlineCommentSchema, InlineCommentListSchema
from argus_review.services.review.internal.summary.schema import SummaryCommentSchema
from argus_review.services.vcs.types import ReviewCommentSchema
from argus_review.tests.fixtures.services.artifacts import FakeArtifactsService
from argus_review.tests.fixtures.services.vcs import FakeVCSClient


@pytest.mark.asyncio
async def test_process_inline_comment_dry_run_logs_and_no_vcs_calls(
        capsys: pytest.CaptureFixture,
        fake_vcs_client: FakeVCSClient,
        fake_artifacts_service: FakeArtifactsService,
        review_dry_run_comment_gateway: ReviewDryRunCommentGateway
):
    """Dry-run: should log inline comment without creating one."""
    comment = InlineCommentSchema(file="a.py", line=10, message="Test comment")
    await review_dry_run_comment_gateway.process_inline_comment(comment)
    output = capsys.readouterr().out

    assert "[dry-run]" in output
    assert "Would create inline comment" in output
    assert "a.py" in output
    assert not any(call[0].startswith("create_") for call in fake_vcs_client.calls)

    assert ("save_vcs_inline", {"comment": comment}) in fake_artifacts_service.calls


@pytest.mark.asyncio
async def test_process_summary_comment_dry_run_logs_and_no_vcs_calls(
        capsys: pytest.CaptureFixture,
        fake_vcs_client: FakeVCSClient,
        fake_artifacts_service: FakeArtifactsService,
        review_dry_run_comment_gateway: ReviewDryRunCommentGateway
):
    """Dry-run: should log summary comment but not send it."""
    comment = SummaryCommentSchema(text="Dry-run summary comment")
    await review_dry_run_comment_gateway.process_summary_comment(comment)
    output = capsys.readouterr().out

    assert "[dry-run]" in output
    assert "Would create summary comment" in output
    assert not any(call[0].startswith("create_") for call in fake_vcs_client.calls)

    assert ("save_vcs_summary", {"comment": comment}) in fake_artifacts_service.calls


@pytest.mark.asyncio
async def test_process_inline_comments_iterates_all(
        capsys: pytest.CaptureFixture,
        fake_vcs_client: FakeVCSClient,
        fake_artifacts_service: FakeArtifactsService,
        review_dry_run_comment_gateway: ReviewDryRunCommentGateway
):
    """Dry-run: should iterate through all inline comments and log each."""
    comments = InlineCommentListSchema(root=[
        InlineCommentSchema(file="a.py", line=1, message="C1"),
        InlineCommentSchema(file="b.py", line=2, message="C2"),
    ])
    await review_dry_run_comment_gateway.process_inline_comments(comments)
    output = capsys.readouterr().out

    assert "[dry-run]" in output
    assert "a.py" in output
    assert "b.py" in output
    assert not any(call[0].startswith("create_") for call in fake_vcs_client.calls)

    assert ("save_vcs_inline", {"comment": comments.root[0]}) in fake_artifacts_service.calls
    assert ("save_vcs_inline", {"comment": comments.root[1]}) in fake_artifacts_service.calls


@pytest.mark.asyncio
async def test_clear_inline_comments_dry_run_no_comments(
        capsys: pytest.CaptureFixture,
        fake_vcs_client: FakeVCSClient,
        review_dry_run_comment_gateway: ReviewDryRunCommentGateway,
):
    """Dry-run: should log and do nothing when no inline comments exist."""
    fake_vcs_client.responses["get_inline_comments"] = []

    await review_dry_run_comment_gateway.clear_inline_comments()
    output = capsys.readouterr().out

    assert "[dry-run] No AI inline comments to clear" in output
    assert not any(call[0].startswith("delete_") for call in fake_vcs_client.calls)


@pytest.mark.asyncio
async def test_clear_inline_comments_dry_run_logs_each_comment(
        capsys: pytest.CaptureFixture,
        fake_vcs_client: FakeVCSClient,
        review_dry_run_comment_gateway: ReviewDryRunCommentGateway,
):
    """Dry-run: should log deletion of each inline comment without calling VCS."""
    fake_vcs_client.responses["get_inline_comments"] = [
        ReviewCommentSchema(id="1", body=f"{settings.review.inline_tag} AI inline"),
        ReviewCommentSchema(id="2", body=f"{settings.review.inline_tag} AI inline"),
    ]

    await review_dry_run_comment_gateway.clear_inline_comments()
    output = capsys.readouterr().out

    assert "[dry-run] Would clear 2 AI inline comments" in output
    assert "[dry-run] Would delete inline comment 1" in output
    assert "[dry-run] Would delete inline comment 2" in output

    assert not any(call[0].startswith("delete_") for call in fake_vcs_client.calls)


@pytest.mark.asyncio
async def test_clear_summary_comments_dry_run_no_comments(
        capsys: pytest.CaptureFixture,
        fake_vcs_client: FakeVCSClient,
        review_dry_run_comment_gateway: ReviewDryRunCommentGateway,
):
    """Dry-run: should log and do nothing when no summary comments exist."""
    fake_vcs_client.responses["get_general_comments"] = []

    await review_dry_run_comment_gateway.clear_summary_comments()
    output = capsys.readouterr().out

    assert "[dry-run] No AI summary comments to clear" in output
    assert not any(call[0].startswith("delete_") for call in fake_vcs_client.calls)


@pytest.mark.asyncio
async def test_clear_summary_comments_dry_run_logs_each_comment(
        capsys: pytest.CaptureFixture,
        fake_vcs_client: FakeVCSClient,
        review_dry_run_comment_gateway: ReviewDryRunCommentGateway,
):
    """Dry-run: should log deletion of each summary comment without calling VCS."""
    fake_vcs_client.responses["get_general_comments"] = [
        ReviewCommentSchema(id="10", body=f"{settings.review.summary_tag} First AI summary"),
        ReviewCommentSchema(id="11", body=f"{settings.review.summary_tag} Second AI summary"),
    ]

    await review_dry_run_comment_gateway.clear_summary_comments()
    output = capsys.readouterr().out

    assert "[dry-run] Would clear 2 AI summary comments" in output
    assert "[dry-run] Would delete summary comment 10" in output
    assert "[dry-run] Would delete summary comment 11" in output

    assert not any(call[0].startswith("delete_") for call in fake_vcs_client.calls)
