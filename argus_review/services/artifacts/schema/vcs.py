from pydantic import BaseModel

from argus_review.services.artifacts.schema.base import BaseArtifactSchema, ArtifactType
from argus_review.services.review.internal.inline.schema import InlineCommentSchema
from argus_review.services.review.internal.summary.schema import SummaryCommentSchema


class VCSInlineArtifactDataSchema(BaseModel):
    inline_comment: InlineCommentSchema


class VCSSummaryArtifactDataSchema(BaseModel):
    summary_comment: SummaryCommentSchema


class VCSInlineArtifactSchema(BaseArtifactSchema[VCSInlineArtifactDataSchema]):
    type: ArtifactType = ArtifactType.VCS_INLINE


class VCSSummaryArtifactSchema(BaseArtifactSchema[VCSSummaryArtifactDataSchema]):
    type: ArtifactType = ArtifactType.VCS_SUMMARY
