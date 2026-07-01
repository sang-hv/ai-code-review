from argus_review.config import settings
from argus_review.services.review.internal.summary.schema import SummaryCommentSchema


class SummaryCommentReplySchema(SummaryCommentSchema):
    @property
    def body_with_tag(self):
        return f"{self.text}\n\n{settings.review.summary_reply_tag}"
