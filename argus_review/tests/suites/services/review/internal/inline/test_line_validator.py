from argus_review.services.review.internal.inline.line_validator import filter_by_valid_lines, normalize_file
from argus_review.services.review.internal.inline.schema import InlineCommentSchema


def _comment(file: str, line: int) -> InlineCommentSchema:
    return InlineCommentSchema(file=file, line=line, message="msg")


def test_normalize_file_strips_diff_prefixes() -> None:
    assert normalize_file("b/src/app.py") == "src/app.py"
    assert normalize_file("a/src/app.py") == "src/app.py"


def test_filter_drops_non_changed_files_even_when_valid_map_is_empty() -> None:
    comments = [
        _comment("src/exists.py", 10),
        _comment("src/missing.py", 5),
    ]

    kept = filter_by_valid_lines(comments, valid_map={}, changed_files=["src/exists.py"])

    assert len(kept) == 1
    assert kept[0].file == "src/exists.py"


def test_filter_keeps_only_valid_lines_when_valid_map_exists() -> None:
    comments = [
        _comment("src/exists.py", 10),
        _comment("src/exists.py", 99),
        _comment("src/missing.py", 10),
    ]

    kept = filter_by_valid_lines(
        comments,
        valid_map={"src/exists.py": {10, 11}},
        changed_files=["src/exists.py"],
    )

    assert len(kept) == 1
    assert kept[0].file == "src/exists.py"
    assert kept[0].line == 10
