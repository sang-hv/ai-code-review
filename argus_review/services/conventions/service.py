import re
from functools import lru_cache
from pathlib import Path

from argus_review.config import settings
from argus_review.libs.config.conventions import ConventionSourceType
from argus_review.libs.crypto.sha import sha256_hex
from argus_review.libs.logger import get_logger
from argus_review.services.conventions.schema import ResolvedConventionSchema
from argus_review.services.conventions.sources import resolve_git, resolve_local, resolve_url
from argus_review.services.conventions.types import ConventionsServiceProtocol

logger = get_logger("CONVENTIONS_SERVICE")

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class ConventionsService(ConventionsServiceProtocol):
    """
    Resolves project coding-convention docs (local / URL / git) once, caches the
    combined markdown, and renders it as a prompt section for enabled modes.

    For the agent-light flow it can also `materialize()` the resolved docs onto
    disk (under `conventions.cache_dir`) and return a lightweight inventory, so
    the agent inspects only the relevant sections with rg/sed/cat instead of
    receiving the full convention text up front. URL/git sources become
    searchable on disk exactly like local ones.

    Resolution is fail-soft: a broken source is logged and skipped so a review is
    never blocked by unreachable conventions.
    """

    def __init__(self):
        self._cached_block: str | None = None
        self._cached_docs: list[ResolvedConventionSchema] | None = None

    def _resolve_source(self, source) -> list[ResolvedConventionSchema]:
        match source.type:
            case ConventionSourceType.LOCAL:
                return resolve_local(source)
            case ConventionSourceType.URL:
                return resolve_url(source, settings.conventions.timeout)
            case ConventionSourceType.GIT:
                return resolve_git(source, settings.conventions.timeout)
            case _:
                return []

    def _resolve_docs(self) -> list[ResolvedConventionSchema]:
        if self._cached_docs is not None:
            return self._cached_docs

        docs: list[ResolvedConventionSchema] = []
        for source in settings.conventions.sources:
            try:
                docs.extend(self._resolve_source(source))
            except Exception as error:
                logger.warning(f"Failed to resolve convention source ({source.type}): {error}")

        self._cached_docs = [doc for doc in docs if doc.content.strip()]
        return self._cached_docs

    def _resolve_all(self) -> str:
        docs = self._resolve_docs()

        sections = [f"### {doc.name}\n\n{doc.content.strip()}" for doc in docs]
        if sections:
            logger.info(f"Loaded {len(sections)} coding-convention document(s)")

        return "\n\n".join(sections)

    def _block(self) -> str:
        if self._cached_block is None:
            self._cached_block = self._resolve_all()
        return self._cached_block

    def render(self, mode: str) -> str:
        if not settings.conventions.enabled:
            return ""
        if not settings.conventions.modes.is_enabled(mode):
            return ""

        block = self._block()
        if not block.strip():
            return ""

        return f"## {settings.conventions.heading}\n\n{block}"

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Turn an arbitrary doc name (path/URL) into a safe, unique .md filename."""
        stem = _SAFE_NAME_RE.sub("-", name).strip("-") or "convention"
        # Keep names short but unique across sources with a short content-independent hash.
        digest = sha256_hex(name)[:8]
        if not stem.lower().endswith(".md"):
            stem = f"{stem}.md"
        return f"{stem[:-3]}-{digest}.md"

    def materialize(self, mode: str | None = None) -> str:
        """
        Write resolved convention docs to `conventions.cache_dir` and return a
        lightweight inventory (path + line count) for the agent to search.

        Returns "" when conventions are disabled (or disabled for `mode`), or
        when there are no resolvable docs. The write is skipped when the cached
        content hash is unchanged.
        """
        if not settings.conventions.enabled:
            return ""
        if mode is not None and not settings.conventions.modes.is_enabled(mode):
            return ""

        docs = self._resolve_docs()
        if not docs:
            return ""

        cache_dir = Path(settings.conventions.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        combined_hash = sha256_hex("\n".join(f"{doc.name}\n{doc.content}" for doc in docs))
        hash_file = cache_dir / ".source-hash"
        cached_hash = hash_file.read_text(encoding="utf-8").strip() if hash_file.exists() else None
        write_needed = cached_hash != combined_hash

        entries: list[str] = []
        for doc in docs:
            filename = self._safe_filename(doc.name)
            target = cache_dir / filename
            content = doc.content
            if write_needed or not target.exists():
                target.write_text(content, encoding="utf-8")

            line_count = content.count("\n") + 1
            entries.append(f"- {target.as_posix()} ({doc.name}), {line_count} lines")

        if write_needed:
            hash_file.write_text(combined_hash, encoding="utf-8")
            logger.info(f"Materialized {len(docs)} coding-convention document(s) into {cache_dir.as_posix()}")

        listing = "\n".join(entries)
        return (
            f"## {settings.conventions.heading}\n\n"
            f"The following coding-convention documents are available on disk. "
            f"Inspect only the relevant sections with `rg`/`sed -n`/`cat` before citing a rule; "
            f"do not assume rules that are not present.\n\n"
            f"{listing}"
        )


@lru_cache(maxsize=1)
def get_conventions_service() -> ConventionsService:
    return ConventionsService()
