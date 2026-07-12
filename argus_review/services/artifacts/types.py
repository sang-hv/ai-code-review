from pathlib import Path
from typing import Protocol

from argus_review.services.artifacts.schema.base import BaseArtifactSchema
from argus_review.services.cost.schema import CostReportSchema
from argus_review.services.review.internal.inline.schema import InlineCommentSchema
from argus_review.services.review.internal.summary.schema import SummaryCommentSchema


class ArtifactsServiceProtocol(Protocol):

    # ==========================================
    # Low-level writer
    # ==========================================
    async def save(
            self,
            artifact: BaseArtifactSchema,
            artifacts_dir: Path,
            artifacts_enabled: bool,
    ) -> str | None:
        ...

    # ==========================================
    # High-level: LLM
    # ==========================================
    async def save_llm(
            self,
            prompt: str,
            response: str,
            prompt_system: str,
            cost_report: CostReportSchema | None = None,
    ) -> str | None:
        ...

    # ==========================================
    # High-level: VCS Inline Comment
    # ==========================================
    async def save_vcs_inline(self, comment: InlineCommentSchema) -> str | None:
        ...

    # ==========================================
    # High-level: VCS Summary Comment
    # ==========================================
    async def save_vcs_summary(self, comment: SummaryCommentSchema) -> str | None:
        ...
