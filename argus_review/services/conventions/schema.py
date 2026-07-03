from pydantic import BaseModel


class ResolvedConventionSchema(BaseModel):
    name: str  # friendly label shown to the model (filename or URL)
    content: str
