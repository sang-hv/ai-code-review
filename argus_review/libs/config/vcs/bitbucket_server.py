from pydantic import BaseModel

from argus_review.libs.config.http import HTTPClientWithTokenConfig


class BitbucketServerPipelineConfig(BaseModel):
    project_key: str
    repo_slug: str
    pull_request_id: int


class BitbucketServerHTTPClientConfig(HTTPClientWithTokenConfig):
    pass
