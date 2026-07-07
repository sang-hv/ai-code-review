from argus_review.libs.diff.models import FileMode, DiffLineType, DiffFile
from argus_review.libs.diff.parser import DiffParser


# ---------- helpers ----------


def parse_and_get_file(raw_diff: str) -> DiffFile:
    """Helper: parse diff and return the first file."""
    diff = DiffParser.parse(raw_diff)
    assert diff.files, "Expected at least one parsed file"
    return diff.files[0]


# ---------- tests ----------

def test_parse_added_lines_only() -> None:
    """Should correctly parse diff with only added lines."""
    raw_diff = """diff --git a/x b/x
index 0000000..1111111 100644
--- a/x
+++ b/x
@@ -0,0 +1,2 @@
+line1
+line2
"""
    file = parse_and_get_file(raw_diff)

    assert file.mode == FileMode.MODIFIED
    assert file.orig_name == "x"
    assert file.new_name == "x"
    assert len(file.hunks) == 1

    added_lines: list[str] = [
        line.content for line in file.hunks[0].new_range.lines if line.type is DiffLineType.ADDED
    ]
    assert added_lines == ["line1", "line2"]


def test_parse_removed_lines_only() -> None:
    """Should correctly parse diff with only removed lines."""
    raw_diff = """diff --git a/x b/x
index 2222222..3333333 100644
--- a/x
+++ b/x
@@ -1,2 +0,0 @@
-line1
-line2
"""
    file = parse_and_get_file(raw_diff)

    assert file.mode == FileMode.MODIFIED
    removed_lines: list[str] = [
        line.content for line in file.hunks[0].orig_range.lines if line.type is DiffLineType.REMOVED
    ]
    assert removed_lines == ["line1", "line2"]


def test_parse_added_and_removed_lines() -> None:
    """Should parse diff with added, removed and unchanged lines."""
    raw_diff = """diff --git a/x b/x
index 4444444..5555555 100644
--- a/x
+++ b/x
@@ -1,3 +1,3 @@
 line1
-line2
+line2_changed
 line3
"""
    file = parse_and_get_file(raw_diff)
    hunk = file.hunks[0]

    assert [line.content for line in hunk.lines] == [
        "line1",
        "line2",
        "line2_changed",
        "line3",
    ]
    assert hunk.lines[0].type == DiffLineType.UNCHANGED
    assert hunk.lines[1].type == DiffLineType.REMOVED
    assert hunk.lines[2].type == DiffLineType.ADDED
    assert hunk.lines[3].type == DiffLineType.UNCHANGED


def test_parse_new_file_mode() -> None:
    """Should mark file as NEW when old side is /dev/null."""
    raw_diff = """diff --git a/x b/x
new file mode 100644
--- /dev/null
+++ b/x
@@ -0,0 +1,1 @@
+new line
"""
    file = parse_and_get_file(raw_diff)

    assert file.mode == FileMode.NEW
    assert file.new_name == "x"
    assert [line.content for line in file.hunks[0].new_range.lines] == ["new line"]


def test_parse_deleted_file_mode() -> None:
    """Should mark file as DELETED when new side is /dev/null."""
    raw_diff = """diff --git a/x b/x
deleted file mode 100644
--- a/x
+++ /dev/null
@@ -1,1 +0,0 @@
-old line
"""
    file = parse_and_get_file(raw_diff)

    assert file.mode == FileMode.DELETED
    assert file.orig_name == "x"
    assert [line.content for line in file.hunks[0].orig_range.lines] == ["old line"]


def test_parse_multiple_files() -> None:
    """Should parse a diff containing several files without leaking hunk state.

    Regression test: previously the parser did not reset ``current_hunk`` when a
    new file started, so metadata lines of subsequent files (e.g. ``index ...``)
    were misclassified as source lines and raised
    ``ValueError: Unknown diff line prefix: 'index ...'``.
    """
    raw_diff = """diff --git a/first.yaml b/first.yaml
index d8c89d03..ce408803 100644
--- a/first.yaml
+++ b/first.yaml
@@ -1,3 +1,3 @@
 line1
-old
+new
 line3
diff --git a/second.py b/second.py
index 02b947f5..74c55077 100644
--- a/second.py
+++ b/second.py
@@ -1,2 +1,3 @@
 keep
+added
 keep2
"""
    diff = DiffParser.parse(raw_diff)

    assert len(diff.files) == 2

    first, second = diff.files
    assert first.orig_name == "first.yaml"
    assert first.new_name == "first.yaml"
    assert len(first.hunks) == 1

    assert second.orig_name == "second.py"
    assert second.new_name == "second.py"
    assert len(second.hunks) == 1

    second_added: list[str] = [
        line.content for line in second.hunks[0].new_range.lines if line.type is DiffLineType.ADDED
    ]
    assert second_added == ["added"]


def test_parse_multiple_files_index_line_not_treated_as_source() -> None:
    """The ``index`` metadata line of a later file must not become a diff line."""
    raw_diff = """diff --git a/a.txt b/a.txt
index 1111111..2222222 100644
--- a/a.txt
+++ b/a.txt
@@ -1,1 +1,1 @@
-a
+b
diff --git a/b.txt b/b.txt
index 3333333..4444444 100644
--- a/b.txt
+++ b/b.txt
@@ -1,1 +1,1 @@
-c
+d
"""
    diff = DiffParser.parse(raw_diff)

    for file in diff.files:
        contents = [line.content for line in file.hunks[0].lines]
        assert not any(content.startswith("index ") for content in contents)
