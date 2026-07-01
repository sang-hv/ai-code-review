from argus_review.config import settings
from argus_review.libs.constants.vcs_provider import VCSProvider
from argus_review.services.vcs.azure_devops.client import AzureDevOpsVCSClient
from argus_review.services.vcs.bitbucket_cloud.client import BitbucketCloudVCSClient
from argus_review.services.vcs.bitbucket_server.client import BitbucketServerVCSClient
from argus_review.services.vcs.gitea.client import GiteaVCSClient
from argus_review.services.vcs.github.client import GitHubVCSClient
from argus_review.services.vcs.gitlab.client import GitLabVCSClient
from argus_review.services.vcs.types import VCSClientProtocol


def get_vcs_client() -> VCSClientProtocol:
    match settings.vcs.provider:
        case VCSProvider.GITEA:
            return GiteaVCSClient()
        case VCSProvider.GITLAB:
            return GitLabVCSClient()
        case VCSProvider.GITHUB:
            return GitHubVCSClient()
        case VCSProvider.AZURE_DEVOPS:
            return AzureDevOpsVCSClient()
        case VCSProvider.BITBUCKET_CLOUD:
            return BitbucketCloudVCSClient()
        case VCSProvider.BITBUCKET_SERVER:
            return BitbucketServerVCSClient()
        case _:
            raise ValueError(f"Unsupported VCS provider: {settings.vcs.provider}")
