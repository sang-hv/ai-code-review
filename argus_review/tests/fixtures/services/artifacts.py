from pathlib import Path

import pytest

from argus_review.services.artifacts.schema.base import BaseArtifactSchema
from argus_review.services.artifacts.service import ArtifactsService
from argus_review.services.artifacts.types import ArtifactsServiceProtocol
from argus_review.services.cost.schema import CostReportSchema
from argus_review.services.review.internal.inline.schema import InlineCommentSchema
from argus_review.services.review.internal.summary.schema import SummaryCommentSchema


class FakeArtifactsService(ArtifactsServiceProtocol):
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def save(self, artifact: BaseArtifactSchema, artifacts_dir: Path, artifacts_enabled: bool) -> str | None:
        self.calls.append((
            "save",
            {
                "artifact": artifact,
                "artifacts_dir": artifacts_dir,
                "artifacts_enabled": artifacts_enabled,
            }
        ))
        return "fake-id"

    async def save_llm(
            self,
            prompt: str,
            response: str,
            prompt_system: str,
            cost_report: CostReportSchema | None = None
    ) -> str | None:
        self.calls.append((
            "save_llm",
            {
                "prompt": prompt,
                "response": response,
                "prompt_system": prompt_system,
                "cost_report": cost_report,
            }
        ))
        return "fake-llm-id"

    async def save_vcs_inline(self, comment: InlineCommentSchema) -> str | None:
        self.calls.append(("save_vcs_inline", {"comment": comment}))
        return "fake-inline-id"

    async def save_vcs_summary(self, comment: SummaryCommentSchema) -> str | None:
        self.calls.append(("save_vcs_summary", {"comment": comment}))
        return "fake-summary-id"


@pytest.fixture
def fake_artifacts_service() -> FakeArtifactsService:
    return FakeArtifactsService()


@pytest.fixture
def artifacts_service() -> ArtifactsService:
    return ArtifactsService()
