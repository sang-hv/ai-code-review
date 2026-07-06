The FINAL content MUST be a JSON array of inline comments and nothing else.

Each item has the shape:
{"file": "<repo-relative path>", "line": <new-file line number in the diff>, "message": "<issue and recommendation>", "suggestion": "<optional replacement code or null>"}

Use the exact file path and a line number that appears on the new side of the diff.
If there are no issues, return an empty array [].
