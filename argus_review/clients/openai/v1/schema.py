from typing import Literal

from pydantic import BaseModel


class OpenAIUsageSchema(BaseModel):
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int


class OpenAIMessageSchema(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str | None = None
    tool_calls: list["OpenAIToolCallSchema"] | None = None


class OpenAIToolFunctionSchema(BaseModel):
    name: str
    arguments: str


class OpenAIToolCallSchema(BaseModel):
    id: str | None = None
    type: Literal["function"]
    function: OpenAIToolFunctionSchema


class OpenAIChatToolFunctionDefSchema(BaseModel):
    name: str
    description: str | None = None
    parameters: dict


class OpenAIChatToolSchema(BaseModel):
    type: Literal["function"]
    function: OpenAIChatToolFunctionDefSchema


class OpenAIChoiceSchema(BaseModel):
    message: OpenAIMessageSchema


class OpenAIChatRequestSchema(BaseModel):
    model: str
    stream: bool = False
    messages: list[OpenAIMessageSchema]
    tools: list[OpenAIChatToolSchema] | None = None
    tool_choice: Literal["auto", "required", "none"] | None = None
    max_tokens: int | None = None
    temperature: float | None = None


class OpenAIChatResponseSchema(BaseModel):
    usage: OpenAIUsageSchema
    choices: list[OpenAIChoiceSchema]

    @property
    def first_text(self) -> str:
        if not self.choices:
            return ""

        return (self.choices[0].message.content or "").strip()

    @property
    def first_tool_call(self) -> OpenAIToolCallSchema | None:
        if not self.choices:
            return None

        tool_calls = getattr(self.choices[0].message, "tool_calls", None)
        if not tool_calls:
            return None

        return tool_calls[0]
