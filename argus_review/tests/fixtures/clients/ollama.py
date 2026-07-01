from typing import Any

import pytest
from pydantic import HttpUrl

from argus_review.clients.ollama.schema import (
    OllamaUsageSchema,
    OllamaMessageSchema,
    OllamaChatRequestSchema,
    OllamaChatResponseSchema,
)
from argus_review.clients.ollama.types import OllamaHTTPClientProtocol
from argus_review.config import settings
from argus_review.libs.config.llm.base import OllamaLLMConfig
from argus_review.libs.config.llm.ollama import OllamaMetaConfig, OllamaHTTPClientConfig
from argus_review.libs.constants.llm_provider import LLMProvider
from argus_review.services.llm.ollama.client import OllamaLLMClient


class FakeOllamaHTTPClient(OllamaHTTPClientProtocol):
    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.responses = responses or {}

    async def chat(self, request: OllamaChatRequestSchema) -> OllamaChatResponseSchema:
        self.calls.append(("chat", {"request": request}))
        return self.responses.get(
            "chat",
            OllamaChatResponseSchema(
                done=True,
                model="llama2",
                usage=OllamaUsageSchema(prompt_tokens=3, completion_tokens=5),
                message=OllamaMessageSchema(role="assistant", content="FAKE_OLLAMA_RESPONSE"),
            ),
        )


@pytest.fixture
def fake_ollama_http_client():
    return FakeOllamaHTTPClient()


@pytest.fixture
def ollama_llm_client(
        monkeypatch: pytest.MonkeyPatch,
        fake_ollama_http_client: FakeOllamaHTTPClient
) -> OllamaLLMClient:
    monkeypatch.setattr(
        "argus_review.services.llm.ollama.client.get_ollama_http_client",
        lambda: fake_ollama_http_client,
    )
    return OllamaLLMClient()


@pytest.fixture
def ollama_http_client_config(monkeypatch: pytest.MonkeyPatch):
    fake_config = OllamaLLMConfig(
        meta=OllamaMetaConfig(),
        provider=LLMProvider.OLLAMA,
        http_client=OllamaHTTPClientConfig(
            timeout=10,
            api_url=HttpUrl("http://localhost:11434")
        )
    )
    monkeypatch.setattr(settings, "llm", fake_config)
