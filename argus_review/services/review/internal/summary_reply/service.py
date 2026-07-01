from argus_review.libs.logger import get_logger
from argus_review.services.review.internal.summary_reply.schema import SummaryCommentReplySchema
from argus_review.services.review.internal.summary_reply.types import SummaryCommentReplyServiceProtocol

logger = get_logger("SUMMARY_COMMENT_REPLY_SERVICE")


class SummaryCommentReplyService(SummaryCommentReplyServiceProtocol):
    @classmethod
    def parse_model_output(cls, output: str) -> SummaryCommentReplySchema:
        text = (output or "").strip()
        if not text:
            logger.warning("LLM returned empty summary")

        return SummaryCommentReplySchema(text=text)
