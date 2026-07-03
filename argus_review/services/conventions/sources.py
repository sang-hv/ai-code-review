import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx

from argus_review.libs.config.conventions import (
    GitConventionSource,
    LocalConventionSource,
    UrlConventionSource,
)
from argus_review.libs.logger import get_logger
from argus_review.services.conventions.schema import ResolvedConventionSchema

logger = get_logger("CONVENTIONS_SOURCES")


def _read_docs_from_path(root: Path, glob: str) -> list[ResolvedConventionSchema]:
    if root.is_file():
        return [ResolvedConventionSchema(name=root.name, content=root.read_text(encoding="utf-8"))]

    docs: list[ResolvedConventionSchema] = []
    for file in sorted(root.glob(glob)):
        if not file.is_file():
            continue
        docs.append(
            ResolvedConventionSchema(
                name=str(file.relative_to(root)),
                content=file.read_text(encoding="utf-8"),
            )
        )
    return docs


def resolve_local(source: LocalConventionSource) -> list[ResolvedConventionSchema]:
    path = Path(source.path).expanduser()
    if not path.exists():
        logger.warning(f"Local convention path not found, skipping: {path}")
        return []

    return _read_docs_from_path(path, source.glob)


def resolve_url(source: UrlConventionSource, timeout: float) -> list[ResolvedConventionSchema]:
    headers: dict[str, str] = {}
    if source.token:
        headers["Authorization"] = f"Bearer {source.token.get_secret_value()}"

    response = httpx.get(str(source.url), headers=headers, timeout=timeout, follow_redirects=True)
    response.raise_for_status()

    return [ResolvedConventionSchema(name=str(source.url), content=response.text)]


def _inject_git_token(repo: str, token: str | None) -> str:
    if not token or not repo.startswith("https://"):
        return repo

    parts = urlsplit(repo)
    # Use the widely-supported x-access-token scheme for HTTPS git auth.
    netloc = f"x-access-token:{token}@{parts.hostname}"
    if parts.port:
        netloc = f"{netloc}:{parts.port}"

    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def resolve_git(source: GitConventionSource, timeout: float) -> list[ResolvedConventionSchema]:
    token = source.token.get_secret_value() if source.token else None
    repo_url = _inject_git_token(source.repo, token)
    tmp_dir = Path(tempfile.mkdtemp(prefix="argus-conventions-"))

    try:
        subprocess.run(
            [
                "git", "clone",
                "--depth", "1",
                "--branch", source.ref,
                repo_url, str(tmp_dir),
            ],
            check=True,
            capture_output=True,
            timeout=timeout,
        )

        target = tmp_dir / source.path
        if not target.exists():
            logger.warning(f"Path '{source.path}' not found in {source.repo}@{source.ref}, skipping")
            return []

        docs = _read_docs_from_path(target, source.glob)
        # Prefix names with the repo so multiple git sources stay distinguishable.
        return [
            ResolvedConventionSchema(name=f"{source.repo}@{source.ref}:{doc.name}", content=doc.content)
            for doc in docs
        ]
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
