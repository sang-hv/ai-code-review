from argus_review.libs.asynchronous.gather import bounded_gather
from argus_review.libs.logger import get_logger
from argus_review.services.artifacts.types import ArtifactsServiceProtocol
from argus_review.services.hook import hook
from argus_review.services.review.gateway.review_comment_gateway import ReviewCommentGateway
from argus_review.services.review.internal.inline.schema import InlineCommentListSchema, InlineCommentSchema
from argus_review.services.review.internal.summary.schema import SummaryCommentSchema
from argus_review.services.vcs.types import VCSClientProtocol

logger = get_logger("REVIEW_DRY_RUN_COMMENT_GATEWAY")


class ReviewDryRunCommentGateway(ReviewCommentGateway):
    def __init__(self, vcs: VCSClientProtocol, artifacts: ArtifactsServiceProtocol):
        super().__init__(vcs=vcs, artifacts=artifacts)
        logger.warning("Running in DRY RUN mode — no comments will be posted to VCS")

    async def process_inline_comment(self, comment: InlineCommentSchema) -> None:
        await hook.emit_inline_comment_start(comment)
        logger.info(
            f"[dry-run] Would create inline comment for {comment.file}:{comment.line}:\n{comment.body_with_tag}"
        )
        await hook.emit_inline_comment_complete(comment)

        await self.artifacts.save_vcs_inline(comment)

    async def process_summary_comment(self, comment: SummaryCommentSchema) -> None:
        await hook.emit_summary_comment_start(comment)
        logger.info(f"[dry-run] Would create summary comment:\n{comment.body_with_tag}")
        await hook.emit_summary_comment_complete(comment)

        await self.artifacts.save_vcs_summary(comment)

    async def process_inline_comments(self, comments: InlineCommentListSchema) -> None:
        await bounded_gather([self.process_inline_comment(comment) for comment in comments.root])

    async def clear_inline_comments(self) -> None:
        await hook.emit_clear_inline_comments_start()

        comments = await self.get_inline_comments()
        if not comments:
            logger.info("[dry-run] No AI inline comments to clear")
            await hook.emit_clear_inline_comments_complete(comments=comments)
            return

        logger.info(f"[dry-run] Would clear {len(comments)} AI inline comments")
        for comment in comments:
            logger.info(f"[dry-run] Would delete inline comment {comment.id}")

        await hook.emit_clear_inline_comments_complete(comments=comments)

    async def clear_summary_comments(self) -> None:
        await hook.emit_clear_summary_comments_start()

        comments = await self.get_summary_comments()
        if not comments:
            logger.info("[dry-run] No AI summary comments to clear")
            await hook.emit_clear_summary_comments_complete(comments=comments)
            return

        logger.info(f"[dry-run] Would clear {len(comments)} AI summary comments")
        for comment in comments:
            logger.info(f"[dry-run] Would delete summary comment {comment.id}")

        await hook.emit_clear_summary_comments_complete(comments=comments)
