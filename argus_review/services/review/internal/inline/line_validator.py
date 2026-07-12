from argus_review.libs.diff.models import FileMode
from argus_review.libs.logger import get_logger
from argus_review.services.diff.types import DiffServiceProtocol
from argus_review.services.git.types import GitServiceProtocol
from argus_review.services.review.internal.inline.schema import InlineCommentSchema
from argus_review.services.vcs.types import ReviewInfoSchema

logger = get_logger("INLINE_LINE_VALIDATOR")


def normalize_file(value: str) -> str:
    path = (value or "").strip().replace("\\", "/").lstrip("/")
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def compute_valid_lines_by_file(
        git: GitServiceProtocol,
        diff: DiffServiceProtocol,
        review_info: ReviewInfoSchema,
) -> dict[str, set[int]]:
    """Map each changed file to the set of new-side line numbers a diff comment can anchor to."""
    try:
        raw_diff = git.get_diff(review_info.base_sha, review_info.head_sha)
        parsed_diff = diff.parse(raw_diff)
    except Exception as error:
        logger.warning(f"Could not parse diff for line validation, skipping validation: {error}")
        return {}

    result: dict[str, set[int]] = {}
    for file in parsed_diff.files:
        if file.mode == FileMode.DELETED:
            continue
        lines = {
            line.number
            for hunk in file.hunks
            for line in hunk.new_range.lines
            if line.number is not None
        }
        result[normalize_file(file.new_name or file.orig_name)] = lines

    return result


def filter_by_valid_lines(
        comments: list[InlineCommentSchema],
        valid_map: dict[str, set[int]],
    changed_files: list[str] | None = None,
) -> list[InlineCommentSchema]:
    """
    Drop any comment whose file is not part of changed files, and when a diff
    line map is available also drop comments whose (file, line) does not anchor
    to a real new-side diff line.

    If `valid_map` is empty (e.g. diff parse failure), line validation is
    skipped but changed-file validation still applies.
    """
    allowed_files = {normalize_file(path) for path in (changed_files or []) if normalize_file(path)}

    kept: list[InlineCommentSchema] = []
    dropped = 0
    for comment in comments:
        comment_file = normalize_file(comment.file)

        if allowed_files and comment_file not in allowed_files:
            dropped += 1
            logger.info(f"Dropping inline comment for non-changed file: {comment.file}:{comment.line}")
            continue

        if not valid_map:
            kept.append(comment)
            continue

        valid_lines = valid_map.get(comment_file)
        if valid_lines is None or comment.line not in valid_lines:
            dropped += 1
            logger.info(f"Dropping inline comment with non-diff line anchor: {comment.file}:{comment.line}")
            continue

        kept.append(comment)

    if dropped:
        logger.info(f"Dropped {dropped} inline comment(s) that did not anchor to a diff line")

    return kept
