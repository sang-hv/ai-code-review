from httpx import AsyncClient, AsyncHTTPTransport

from argus_review.clients.openai.v1.client import OpenAIV1HTTPClient
from argus_review.config import settings
from argus_review.libs.http.event_hooks.logger import LoggerEventHook
from argus_review.libs.http.transports.retry import RetryTransport
from argus_review.libs.logger import get_logger


def get_openai_compatible_http_client() -> OpenAIV1HTTPClient:
    """
    Build an OpenAI Chat Completions compatible HTTP client.

    Reuses the OpenAI v1 request/response schemas and client, but sends the
    Authorization header only when an api_token is configured, so unauthenticated
    local gateways (9Router, vLLM, LocalAI, ...) work without a token.
    """
    logger = get_logger("OPENAI_COMPATIBLE_HTTP_CLIENT")
    logger_event_hook = LoggerEventHook(logger=logger)
    retry_transport = RetryTransport(
        logger=logger,
        transport=AsyncHTTPTransport(
            proxy=settings.llm.http_client.proxy_url_value,
            verify=settings.llm.http_client.verify,
        ),
    )

    headers: dict[str, str] = {}
    api_token = settings.llm.http_client.api_token_value
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    client = AsyncClient(
        verify=settings.llm.http_client.verify,
        timeout=settings.llm.http_client.timeout,
        headers=headers,
        base_url=settings.llm.http_client.api_url_value,
        transport=retry_transport,
        event_hooks={
            "request": [logger_event_hook.request],
            "response": [logger_event_hook.response],
        },
    )

    return OpenAIV1HTTPClient(client=client)
