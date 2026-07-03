from typing import Any

import pytest
from pydantic import HttpUrl, SecretStr

from argus_review.clients.openai.v1.schema import (
    OpenAIChatRequestSchema,
    OpenAIChatResponseSchema,
    OpenAIChoiceSchema,
    OpenAIMessageSchema,
    OpenAIUsageSchema,
)
from argus_review.clients.openai.v1.types import OpenAIV1HTTPClientProtocol
from argus_review.config import settings
from argus_review.libs.config.llm.base import NineRouterLLMConfig, OpenAICompatibleLLMConfig
from argus_review.libs.config.llm.nine_router import NineRouterHTTPClientConfig, NineRouterMetaConfig
from argus_review.libs.config.llm.openai_compatible import (
    OpenAICompatibleHTTPClientConfig,
    OpenAICompatibleMetaConfig,
)
from argus_review.libs.constants.llm_provider import LLMProvider
from argus_review.services.llm.openai_compatible.client import OpenAICompatibleLLMClient


class FakeOpenAICompatibleHTTPClient(OpenAIV1HTTPClientProtocol):
    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.responses = responses or {}

    async def chat(self, request: OpenAIChatRequestSchema) -> OpenAIChatResponseSchema:
        self.calls.append(("chat", {"request": request}))
        return self.responses.get(
            "chat",
            OpenAIChatResponseSchema(
                usage=OpenAIUsageSchema(total_tokens=12, prompt_tokens=5, completion_tokens=7),
                choices=[
                    OpenAIChoiceSchema(
                        message=OpenAIMessageSchema(
                            role="assistant",
                            content="FAKE_OPENAI_COMPATIBLE_RESPONSE",
                        )
                    )
                ],
            ),
        )


@pytest.fixture
def fake_openai_compatible_http_client() -> FakeOpenAICompatibleHTTPClient:
    return FakeOpenAICompatibleHTTPClient()


@pytest.fixture
def openai_compatible_http_client_config(monkeypatch: pytest.MonkeyPatch):
    fake_config = OpenAICompatibleLLMConfig(
        meta=OpenAICompatibleMetaConfig(),
        provider=LLMProvider.OPENAI_COMPATIBLE,
        http_client=OpenAICompatibleHTTPClientConfig(
            timeout=10,
            api_url=HttpUrl("https://my-router.example.com/v1"),
            api_token=SecretStr("fake-token"),
        ),
    )
    monkeypatch.setattr(settings, "llm", fake_config)


@pytest.fixture
def nine_router_http_client_config(monkeypatch: pytest.MonkeyPatch):
    fake_config = NineRouterLLMConfig(
        meta=NineRouterMetaConfig(),
        provider=LLMProvider.NINE_ROUTER,
        http_client=NineRouterHTTPClientConfig(),
    )
    monkeypatch.setattr(settings, "llm", fake_config)


@pytest.fixture
def openai_compatible_llm_client(
        monkeypatch: pytest.MonkeyPatch,
        openai_compatible_http_client_config,
        fake_openai_compatible_http_client: FakeOpenAICompatibleHTTPClient,
) -> OpenAICompatibleLLMClient:
    monkeypatch.setattr(
        "argus_review.services.llm.openai_compatible.client.get_openai_compatible_http_client",
        lambda: fake_openai_compatible_http_client,
    )
    return OpenAICompatibleLLMClient()
