from httpx import AsyncClient, AsyncHTTPTransport

from argus_review.clients.bitbucket_cloud.pr.client import BitbucketCloudPullRequestsHTTPClient
from argus_review.config import settings
from argus_review.libs.http.event_hooks.logger import LoggerEventHook
from argus_review.libs.http.transports.retry import RetryTransport
from argus_review.libs.logger import get_logger


class BitbucketCloudHTTPClient:
    def __init__(self, client: AsyncClient):
        self.pr = BitbucketCloudPullRequestsHTTPClient(client)


def get_bitbucket_cloud_http_client() -> BitbucketCloudHTTPClient:
    logger = get_logger("BITBUCKET_CLOUD_HTTP_CLIENT")
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
        headers={"Authorization": f"Bearer {settings.vcs.http_client.api_token_value}"},
        base_url=settings.vcs.http_client.api_url_value,
        transport=retry_transport,
        event_hooks={
            "request": [logger_event_hook.request],
            "response": [logger_event_hook.response],
        }
    )

    return BitbucketCloudHTTPClient(client=client)
