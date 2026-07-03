from functools import lru_cache

from argus_review.config import settings
from argus_review.libs.config.conventions import ConventionSourceType
from argus_review.libs.logger import get_logger
from argus_review.services.conventions.schema import ResolvedConventionSchema
from argus_review.services.conventions.sources import resolve_git, resolve_local, resolve_url
from argus_review.services.conventions.types import ConventionsServiceProtocol

logger = get_logger("CONVENTIONS_SERVICE")


class ConventionsService(ConventionsServiceProtocol):
    """
    Resolves project coding-convention docs (local / URL / git) once, caches the
    combined markdown, and renders it as a prompt section for enabled modes.

    Resolution is fail-soft: a broken source is logged and skipped so a review is
    never blocked by unreachable conventions.
    """

    def __init__(self):
        self._cached_block: str | None = None

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

    def _resolve_all(self) -> str:
        docs: list[ResolvedConventionSchema] = []
        for source in settings.conventions.sources:
            try:
                docs.extend(self._resolve_source(source))
            except Exception as error:
                logger.warning(f"Failed to resolve convention source ({source.type}): {error}")

        sections = [
            f"### {doc.name}\n\n{doc.content.strip()}"
            for doc in docs
            if doc.content.strip()
        ]
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


@lru_cache(maxsize=1)
def get_conventions_service() -> ConventionsService:
    return ConventionsService()
