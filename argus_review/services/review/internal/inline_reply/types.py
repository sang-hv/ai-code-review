from typing import Protocol

from argus_review.services.review.internal.inline_reply.schema import InlineCommentReplySchema


class InlineCommentReplyServiceProtocol(Protocol):
    def parse_model_output(self, output: str) -> InlineCommentReplySchema | None:
        ...
