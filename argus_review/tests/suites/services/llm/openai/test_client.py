import pytest

from argus_review.clients.openai.v1.schema import (
    OpenAIChatResponseSchema,
    OpenAIChoiceSchema,
    OpenAIMessageSchema,
    OpenAIToolCallSchema,
    OpenAIToolFunctionSchema,
    OpenAIUsageSchema,
)
from argus_review.services.llm.openai.client import OpenAILLMClient
from argus_review.services.llm.types import ChatResultSchema
from argus_review.tests.fixtures.clients.openai import FakeOpenAIV1HTTPClient, FakeOpenAIV2HTTPClient


@pytest.mark.asyncio
@pytest.mark.usefixtures("openai_v1_http_client_config")
async def test_openai_llm_chat_v1(
    openai_llm_client: OpenAILLMClient,
    fake_openai_v1_http_client: FakeOpenAIV1HTTPClient,
):
    result = await openai_llm_client.chat("prompt", "prompt_system")

    assert isinstance(result, ChatResultSchema)
    assert result.text == "FAKE_OPENAI_V1_RESPONSE"
    assert result.total_tokens == 12
    assert result.prompt_tokens == 5
    assert result.completion_tokens == 7

    assert fake_openai_v1_http_client.calls[0][0] == "chat"
    request = fake_openai_v1_http_client.calls[0][1]["request"]
    assert request.tools is None
    assert request.tool_choice is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("openai_v2_http_client_config")
async def test_openai_llm_chat_v2(
    openai_llm_client: OpenAILLMClient,
    fake_openai_v2_http_client: FakeOpenAIV2HTTPClient,
):
    result = await openai_llm_client.chat("prompt", "prompt_system")

    assert isinstance(result, ChatResultSchema)
    assert result.text == "FAKE_OPENAI_V2_RESPONSE"
    assert result.total_tokens == 20
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 10

    assert fake_openai_v2_http_client.calls[0][0] == "chat"


@pytest.mark.asyncio
@pytest.mark.usefixtures("openai_v1_http_client_config")
async def test_openai_llm_chat_v1_extracts_tool_command(
    openai_llm_client: OpenAILLMClient,
    fake_openai_v1_http_client: FakeOpenAIV1HTTPClient,
):
    fake_openai_v1_http_client.responses["chat"] = OpenAIChatResponseSchema(
        usage=OpenAIUsageSchema(total_tokens=18, prompt_tokens=10, completion_tokens=8),
        choices=[
            OpenAIChoiceSchema(
                message=OpenAIMessageSchema(
                    role="assistant",
                    content=None,
                    tool_calls=[
                        OpenAIToolCallSchema(
                            id="call_1",
                            type="function",
                            function=OpenAIToolFunctionSchema(
                                name="read_shell_command",
                                arguments='{"command":"git diff --name-only"}',
                            ),
                        )
                    ],
                )
            )
        ],
    )

    result = await openai_llm_client.chat(
        "prompt",
        'Protocol: {"action": "TOOL_CALL", "command": "..."} or {"action": "FINAL", "content": "..."}',
    )

    assert result.tool_command == "git diff --name-only"
    request = fake_openai_v1_http_client.calls[0][1]["request"]
    assert request.tools is not None
    assert request.tool_choice == "auto"
