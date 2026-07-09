import json

from argus_review.clients.openai.v1.client import get_openai_v1_http_client
from argus_review.clients.openai.v1.schema import (
    OpenAIChatRequestSchema,
    OpenAIMessageSchema,
    OpenAIChatToolSchema,
    OpenAIChatToolFunctionDefSchema,
    OpenAIChatResponseSchema,
)
from argus_review.clients.openai.v2.client import get_openai_v2_http_client
from argus_review.clients.openai.v2.schema import OpenAIInputMessageSchema, OpenAIResponsesRequestSchema
from argus_review.config import settings
from argus_review.libs.logger import get_logger
from argus_review.services.llm.types import LLMClientProtocol, ChatResultSchema


logger = get_logger("OPENAI_LLM_CLIENT")

_READ_SHELL_COMMAND_TOOL = OpenAIChatToolSchema(
    type="function",
    function=OpenAIChatToolFunctionDefSchema(
        name="read_shell_command",
        description="Return exactly one read-only shell command that should run next.",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "A single read-only command (git/rg/grep/cat/sed/head/tail/wc/ls/find).",
                }
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    ),
)


class OpenAILLMClient(LLMClientProtocol):
    def __init__(self):
        self.meta = settings.llm.meta

        self.http_client_v1 = get_openai_v1_http_client()
        self.http_client_v2 = get_openai_v2_http_client()

    @staticmethod
    def _extract_tool_command_v1(response: OpenAIChatResponseSchema) -> str | None:
        tool_call = response.first_tool_call
        if tool_call is None or tool_call.type != "function":
            return None

        if tool_call.function.name != "read_shell_command":
            return None

        arguments_raw = (tool_call.function.arguments or "").strip()
        if not arguments_raw:
            return None

        try:
            arguments = json.loads(arguments_raw)
        except json.JSONDecodeError:
            logger.debug("OpenAI v1 tool call arguments are not valid JSON")
            return None

        command = arguments.get("command") if isinstance(arguments, dict) else None
        if not isinstance(command, str):
            return None

        normalized = command.strip()
        return normalized or None

    @staticmethod
    def _should_use_tools(prompt_system: str) -> bool:
        # Only the iterative agent-loop system prompt uses the TOOL_CALL/FINAL protocol.
        # Direct review prompts (combined/inline/summary) should stay plain text JSON.
        text = (prompt_system or "")
        return '"action": "TOOL_CALL"' in text and '"action": "FINAL"' in text

    async def chat_v1(self, prompt: str, prompt_system: str) -> ChatResultSchema:
        use_tools = self._should_use_tools(prompt_system)
        request = OpenAIChatRequestSchema(
            model=self.meta.model,
            messages=[
                OpenAIMessageSchema(role="system", content=prompt_system),
                OpenAIMessageSchema(role="user", content=prompt),
            ],
            tools=[_READ_SHELL_COMMAND_TOOL] if use_tools else None,
            tool_choice="auto" if use_tools else None,
            max_tokens=self.meta.max_tokens,
            temperature=self.meta.temperature,
        )
        response = await self.http_client_v1.chat(request)
        return ChatResultSchema(
            text=response.first_text,
            tool_command=self._extract_tool_command_v1(response),
            total_tokens=response.usage.total_tokens,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

    async def chat_v2(self, prompt: str, prompt_system: str) -> ChatResultSchema:
        request = OpenAIResponsesRequestSchema(
            model=self.meta.model,
            input=[
                OpenAIInputMessageSchema(role="system", content=prompt_system),
                OpenAIInputMessageSchema(role="user", content=prompt),
            ],
            temperature=self.meta.temperature,
            max_output_tokens=self.meta.max_tokens,
        )
        response = await self.http_client_v2.chat(request)
        return ChatResultSchema(
            text=response.first_text,
            total_tokens=response.usage.total_tokens,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )

    async def chat(self, prompt: str, prompt_system: str) -> ChatResultSchema:
        if self.meta.is_v2_model:
            return await self.chat_v2(prompt, prompt_system)

        return await self.chat_v1(prompt, prompt_system)
