from pydantic import BaseModel, Field, field_validator

from argus_review.services.review.internal.inline.schema import InlineCommentSchema


class AgentCombinedResultSchema(BaseModel):
    """
    FINAL output contract for the single-session `run-agent` flow: one agent
    session returns both the summary text and the inline comments in one JSON
    object, instead of running two separate agent sessions (and re-exploring
    the diff/conventions twice).
    """

    summary: str = ""
    comments: list[InlineCommentSchema] = Field(default_factory=list)

    @field_validator("summary")
    def normalize_summary(cls, value: str) -> str:
        return (value or "").strip()
