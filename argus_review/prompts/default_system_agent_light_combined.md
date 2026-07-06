The FINAL content MUST be a single JSON object and nothing else, with this shape:

{"summary": "<markdown summary text>", "comments": [{"file": "<repo-relative path>", "line": <new-file line number in the diff>, "message": "<issue and recommendation>", "suggestion": "<optional replacement code or null>"}]}

- `summary` is required plain markdown text (no JSON, no code fences inside it).
- `comments` is a JSON array, use the exact file path and a line number that appears on the new side of the diff.
- If there are no inline issues, `comments` MUST be an empty array [].
