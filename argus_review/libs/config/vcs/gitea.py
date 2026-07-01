from pydantic import BaseModel

from argus_review.libs.config.http import HTTPClientWithTokenConfig


class GiteaPipelineConfig(BaseModel):
    repo: str
    owner: str
    pull_number: str


class GiteaHTTPClientConfig(HTTPClientWithTokenConfig):
    pass
