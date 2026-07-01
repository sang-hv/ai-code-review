from httpx import AsyncClient, AsyncHTTPTransport

from argus_review.clients.azure_devops.pr.client import AzureDevOpsPullRequestsHTTPClient
from argus_review.clients.azure_devops.tools import build_azure_devops_headers
from argus_review.config import settings
from argus_review.libs.http.event_hooks.logger import LoggerEventHook
from argus_review.libs.http.transports.retry import RetryTransport
from argus_review.libs.logger import get_logger


class AzureDevOpsHTTPClient:
    def __init__(self, client: AsyncClient):
        self.pr = AzureDevOpsPullRequestsHTTPClient(client)


def get_azure_devops_http_client() -> AzureDevOpsHTTPClient:
    logger = get_logger("AZURE_DEVOPS_HTTP_CLIENT")
    logger_event_hook = LoggerEventHook(logger=logger)
    retry_transport = RetryTransport(
        logger=logger,
        transport=AsyncHTTPTransport(
            proxy=settings.vcs.http_client.proxy_url_value,
            verify=settings.vcs.http_client.verify
        )
    )

    client = AsyncClient(
        verify=settings.vcs.http_client.verify,
        timeout=settings.vcs.http_client.timeout,
        headers=build_azure_devops_headers(),
        base_url=settings.vcs.http_client.api_url_value,
        transport=retry_transport,
        event_hooks={
            "request": [logger_event_hook.request],
            "response": [logger_event_hook.response],
        },
    )

    return AzureDevOpsHTTPClient(client=client)
