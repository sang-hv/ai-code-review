from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl, SecretStr


class ConventionSourceType(StrEnum):
    LOCAL = "local"
    URL = "url"
    GIT = "git"


class LocalConventionSource(BaseModel):
    """A coding-convention document (or folder of `.md` docs) on the local filesystem."""

    type: Literal[ConventionSourceType.LOCAL] = ConventionSourceType.LOCAL
    path: str  # file or directory, relative to the repo root or absolute
    glob: str = "**/*.md"  # used only when `path` is a directory


class UrlConventionSource(BaseModel):
    """A coding-convention document fetched from an HTTPS URL (e.g. a raw `.md`)."""

    type: Literal[ConventionSourceType.URL] = ConventionSourceType.URL
    url: HttpUrl
    token: SecretStr | None = None  # optional bearer token for private URLs


class GitConventionSource(BaseModel):
    """Coding-convention `.md` docs pulled from a git repository."""

    type: Literal[ConventionSourceType.GIT] = ConventionSourceType.GIT
    repo: str  # e.g. https://github.com/org/standards.git
    ref: str = "main"
    path: str = "."  # file or subdirectory within the repo
    glob: str = "**/*.md"  # used only when `path` is a directory
    token: SecretStr | None = None  # optional token for private repositories


ConventionSource = Annotated[
    LocalConventionSource | UrlConventionSource | GitConventionSource,
    Field(discriminator="type"),
]


class ConventionModesConfig(BaseModel):
    """Toggle convention injection per review mode. All enabled by default."""

    inline: bool = True
    context: bool = True
    summary: bool = True
    inline_reply: bool = True
    summary_reply: bool = True

    def is_enabled(self, mode: str) -> bool:
        return bool(getattr(self, mode, True))


class ConventionsConfig(BaseModel):
    """
    Project coding conventions injected into every review prompt.

    Point `sources` at local docs, a raw URL, or a git repo containing `.md`
    files. They are combined into a single `## <heading>` section and appended
    to the review prompt for the enabled modes.
    """

    enabled: bool = False
    heading: str = "Project Coding Conventions"
    timeout: float = 30  # seconds, per URL/git source
    # Where URL/git (and local) convention docs are materialized so the
    # agent-light flow can inspect them on disk with rg/sed/cat like any other
    # repository file. Relative to the repo root.
    cache_dir: str = ".argus-review/cache/conventions"
    sources: list[ConventionSource] = Field(default_factory=list)
    modes: ConventionModesConfig = ConventionModesConfig()
