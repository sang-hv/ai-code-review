from argus_review.config import settings
from argus_review.libs.asynchronous.gather import bounded_gather
from argus_review.libs.logger import get_logger
from argus_review.services.artifacts.types import ArtifactsServiceProtocol
from argus_review.services.hook import hook
from argus_review.services.review.gateway.types import ReviewCommentGatewayProtocol
from argus_review.services.review.internal.inline.schema import InlineCommentListSchema, InlineCommentSchema
from argus_review.services.review.internal.summary.schema import SummaryCommentSchema
from argus_review.services.vcs.types import VCSClientProtocol, ReviewCommentSchema

logger = get_logger("REVIEW_COMMENT_GATEWAY")


class ReviewCommentGateway(ReviewCommentGatewayProtocol):
    def __init__(self, vcs: VCSClientProtocol, artifacts: ArtifactsServiceProtocol):
        self.vcs = vcs
        self.artifacts = artifacts

    async def get_inline_comments(self) -> list[ReviewCommentSchema]:
        comments = await self.vcs.get_inline_comments()
        inline_comments = [
            comment for comment in comments
            if settings.review.inline_tag in comment.body
        ]
        logger.info(f"Detected {len(inline_comments)}/{len(comments)} AI inline comments")
        return inline_comments

    async def get_summary_comments(self) -> list[ReviewCommentSchema]:
        comments = await self.vcs.get_general_comments()
        summary_comments = [
            comment for comment in comments
            if settings.review.summary_tag in comment.body
        ]
        logger.info(f"Detected {len(summary_comments)}/{len(comments)} AI summary comments")
        return summary_comments

    async def process_inline_comment(self, comment: InlineCommentSchema) -> None:
        try:
            await hook.emit_inline_comment_start(comment)
            await self.vcs.create_inline_comment(
                file=comment.file,
                line=comment.line,
                message=comment.body_with_tag,
            )
            await hook.emit_inline_comment_complete(comment)

            await self.artifacts.save_vcs_inline(comment)
        except Exception as error:
            logger.exception(
                f"Failed to process inline comment for {comment.file}:{comment.line} — {error}"
            )
            await hook.emit_inline_comment_error(comment)

            if settings.review.inline_comment_fallback:
                logger.warning(f"Falling back to general comment for {comment.file}:{comment.line}")
                await self.process_inline_fallback_comment(SummaryCommentSchema(text=comment.fallback_body))

    async def process_inline_fallback_comment(self, comment: SummaryCommentSchema) -> None:
        try:
            await hook.emit_summary_comment_start(comment)
            await self.vcs.create_general_comment(comment.body_with_fallback_tag)
            await hook.emit_summary_comment_complete(comment)

            await self.artifacts.save_vcs_summary(comment)
        except Exception as error:
            logger.exception(f"Failed to process inline fallback comment: {comment} — {error}")
            await hook.emit_summary_comment_error(comment)

    async def process_summary_comment(self, comment: SummaryCommentSchema) -> None:
        try:
            await hook.emit_summary_comment_start(comment)
            await self.vcs.create_general_comment(comment.body_with_tag)
            await hook.emit_summary_comment_complete(comment)

            await self.artifacts.save_vcs_summary(comment)
        except Exception as error:
            logger.exception(f"Failed to process summary comment: {comment} — {error}")
            await hook.emit_summary_comment_error(comment)

    async def process_inline_comments(self, comments: InlineCommentListSchema) -> None:
        await bounded_gather([self.process_inline_comment(comment) for comment in comments.root])

    async def clear_inline_comments(self) -> None:
        await hook.emit_clear_inline_comments_start()

        try:
            comments = await self.get_inline_comments()
            if not comments:
                logger.info("No AI inline comments to clear")
                await hook.emit_clear_inline_comments_complete(comments=comments)
                return

            logger.info(f"Clearing {len(comments)} AI inline comments")

            await bounded_gather([self.vcs.delete_inline_comment(comment.id) for comment in comments])
            await hook.emit_clear_inline_comments_complete(comments=comments)
        except Exception as error:
            logger.exception(f"Failed to clear inline comments: {error}")
            await hook.emit_clear_inline_comments_error()

    async def clear_summary_comments(self) -> None:
        await hook.emit_clear_summary_comments_start()

        try:
            comments = await self.get_summary_comments()
            if not comments:
                logger.info("No AI summary comments to clear")
                await hook.emit_clear_summary_comments_complete(comments=comments)
                return

            logger.info(f"Clearing {len(comments)} AI summary comments")

            await bounded_gather([self.vcs.delete_general_comment(comment.id) for comment in comments])
            await hook.emit_clear_summary_comments_complete(comments=comments)
        except Exception as error:
            logger.exception(f"Failed to clear summary comments: {error}")
            await hook.emit_clear_summary_comments_error()
