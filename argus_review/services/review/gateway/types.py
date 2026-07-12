from typing import Protocol

from argus_review.services.artifacts.types import ArtifactsServiceProtocol
from argus_review.services.cost.types import CostServiceProtocol
from argus_review.services.llm.types import LLMClientProtocol
from argus_review.services.review.internal.inline.schema import InlineCommentSchema, InlineCommentListSchema
from argus_review.services.review.internal.summary.schema import SummaryCommentSchema
from argus_review.services.vcs.types import VCSClientProtocol, ReviewCommentSchema


class ReviewLLMGatewayProtocol(Protocol):
    llm: LLMClientProtocol
    cost: CostServiceProtocol
    artifacts: ArtifactsServiceProtocol

    async def ask(self, prompt: str, prompt_system: str) -> str:
        ...


class ReviewCommentGatewayProtocol(Protocol):
    vcs: VCSClientProtocol
    artifacts: ArtifactsServiceProtocol

    async def get_inline_comments(self) -> list[ReviewCommentSchema]:
        ...

    async def get_summary_comments(self) -> list[ReviewCommentSchema]:
        ...

    async def process_inline_comment(self, comment: InlineCommentSchema) -> None:
        ...

    async def process_summary_comment(self, comment: SummaryCommentSchema) -> None:
        ...

    async def process_inline_comments(self, comments: InlineCommentListSchema) -> None:
        ...

    async def clear_inline_comments(self) -> None:
        ...

    async def clear_summary_comments(self) -> None:
        ...
