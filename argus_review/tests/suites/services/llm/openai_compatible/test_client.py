import pytest

from argus_review.services.llm.openai_compatible.client import OpenAICompatibleLLMClient
from argus_review.services.llm.types import ChatResultSchema
from argus_review.tests.fixtures.clients.openai_compatible import FakeOpenAICompatibleHTTPClient


@pytest.mark.asyncio
@pytest.mark.usefixtures("openai_compatible_http_client_config")
async def test_openai_compatible_llm_chat(
        openai_compatible_llm_client: OpenAICompatibleLLMClient,
        fake_openai_compatible_http_client: FakeOpenAICompatibleHTTPClient,
):
    result = await openai_compatible_llm_client.chat("prompt", "prompt_system")

    assert isinstance(result, ChatResultSchema)
    assert result.text == "FAKE_OPENAI_COMPATIBLE_RESPONSE"
    assert result.total_tokens == 12
    assert result.prompt_tokens == 5
    assert result.completion_tokens == 7

    assert fake_openai_compatible_http_client.calls[0][0] == "chat"


@pytest.mark.asyncio
@pytest.mark.usefixtures("openai_compatible_http_client_config")
async def test_openai_compatible_llm_chat_sends_system_and_user_messages(
        openai_compatible_llm_client: OpenAICompatibleLLMClient,
        fake_openai_compatible_http_client: FakeOpenAICompatibleHTTPClient,
):
    await openai_compatible_llm_client.chat("USER_PROMPT", "SYSTEM_PROMPT")

    request = fake_openai_compatible_http_client.calls[0][1]["request"]
    assert [message.role for message in request.messages] == ["system", "user"]
    assert request.messages[0].content == "SYSTEM_PROMPT"
    assert request.messages[1].content == "USER_PROMPT"
