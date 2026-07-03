from pydantic import SecretStr

from argus_review.libs.config.http import HTTPClientConfig
from argus_review.libs.config.llm.meta import LLMMetaConfig


class OpenAICompatibleMetaConfig(LLMMetaConfig):
    model: str = "gpt-4o-mini"


class OpenAICompatibleHTTPClientConfig(HTTPClientConfig):
    """
    HTTP config for any OpenAI-compatible endpoint.

    Unlike the first-party providers, the API token is optional here so that
    local gateways (9Router, vLLM, LocalAI, Ollama-compatible servers, ...) that
    don't require authentication work out of the box.
    """

    api_token: SecretStr | None = None

    @property
    def api_token_value(self) -> str | None:
        return self.api_token.get_secret_value() if self.api_token else None
