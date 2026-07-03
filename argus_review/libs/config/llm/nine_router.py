from pydantic import Field, HttpUrl

from argus_review.libs.config.llm.openai_compatible import (
    OpenAICompatibleHTTPClientConfig,
    OpenAICompatibleMetaConfig,
)

# Default local endpoint exposed by the 9Router proxy (`npx 9router`).
NINE_ROUTER_DEFAULT_API_URL = "http://localhost:20128/v1"


class NineRouterMetaConfig(OpenAICompatibleMetaConfig):
    pass


class NineRouterHTTPClientConfig(OpenAICompatibleHTTPClientConfig):
    # Preset to the local proxy so no api_url is needed for the common case.
    api_url: HttpUrl = Field(default=NINE_ROUTER_DEFAULT_API_URL, validate_default=True)
