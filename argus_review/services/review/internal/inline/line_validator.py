from argus_review.libs.diff.models import FileMode
from argus_review.libs.logger import get_logger
from argus_review.services.diff.types import DiffServiceProtocol
from argus_review.services.git.types import GitServiceProtocol
from argus_review.services.review.internal.inline.schema import InlineCommentSchema
from argus_review.services.vcs.types import ReviewInfoSchema

logger = get_logger("INLINE_LINE_VALIDATOR")


def normalize_file(value: str) -> str:
    return (value or "").strip().replace("\\", "/").lstrip("/")


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
) -> list[InlineCommentSchema]:
    """
    Drop any comment whose (file, line) does not anchor to a real new-side diff
    line (the VCS would reject it anyway). Lenient (keeps everything) when
    `valid_map` is empty, e.g. because the diff could not be parsed.
    """
    if not valid_map:
        return comments

    kept: list[InlineCommentSchema] = []
    dropped = 0
    for comment in comments:
        valid_lines = valid_map.get(normalize_file(comment.file))
        if valid_lines is not None and comment.line in valid_lines:
            kept.append(comment)
        else:
            dropped += 1
            logger.info(f"Dropping inline comment with non-diff line anchor: {comment.file}:{comment.line}")

    if dropped:
        logger.info(f"Dropped {dropped} inline comment(s) that did not anchor to a diff line")

    return kept
