from pydantic import HttpUrl, SecretStr

from argus_review.libs.config.llm.base import NineRouterLLMConfig, OpenAICompatibleLLMConfig
from argus_review.libs.config.llm.nine_router import (
    NINE_ROUTER_DEFAULT_API_URL,
    NineRouterHTTPClientConfig,
)
from argus_review.libs.config.llm.openai_compatible import (
    OpenAICompatibleHTTPClientConfig,
    OpenAICompatibleMetaConfig,
)
from argus_review.libs.constants.llm_provider import LLMProvider


def test_openai_compatible_token_is_optional():
    http_client = OpenAICompatibleHTTPClientConfig(api_url=HttpUrl("https://router.example.com/v1"))
    assert http_client.api_token is None
    assert http_client.api_token_value is None


def test_openai_compatible_token_value_when_set():
    http_client = OpenAICompatibleHTTPClientConfig(
        api_url=HttpUrl("https://router.example.com/v1"),
        api_token=SecretStr("secret"),
    )
    assert http_client.api_token_value == "secret"


def test_openai_compatible_meta_default_model():
    assert OpenAICompatibleMetaConfig().model == "gpt-4o-mini"


def test_openai_compatible_config_discriminator():
    config = OpenAICompatibleLLMConfig(
        meta=OpenAICompatibleMetaConfig(),
        provider=LLMProvider.OPENAI_COMPATIBLE,
        http_client=OpenAICompatibleHTTPClientConfig(api_url=HttpUrl("https://router.example.com/v1")),
    )
    assert config.provider == LLMProvider.OPENAI_COMPATIBLE


def test_nine_router_defaults_to_local_proxy():
    http_client = NineRouterHTTPClientConfig()
    assert http_client.api_url_value == NINE_ROUTER_DEFAULT_API_URL
    assert http_client.api_token_value is None


def test_nine_router_config_minimal():
    """9Router should be usable with just the provider set."""
    config = NineRouterLLMConfig(provider=LLMProvider.NINE_ROUTER)
    assert config.provider == LLMProvider.NINE_ROUTER
    assert config.http_client.api_url_value == NINE_ROUTER_DEFAULT_API_URL
    assert config.meta.model == "gpt-4o-mini"
