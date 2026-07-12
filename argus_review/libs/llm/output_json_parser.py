import re
from typing import TypeVar, Generic, Type

from pydantic import BaseModel, ValidationError

from argus_review.libs.json import sanitize_json_string
from argus_review.libs.logger import get_logger

logger = get_logger("LLM_JSON_PARSER")

T = TypeVar("T", bound=BaseModel)

CLEAN_JSON_BLOCK_RE = re.compile(r"```(?:json)?(.*?)```", re.DOTALL | re.IGNORECASE)
FIRST_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}", re.MULTILINE)
FIRST_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*]", re.MULTILINE)


def extract_balanced_json(text: str) -> str | None:
    """
    Extract the first brace-balanced JSON object/array from text, ignoring
    braces inside strings. Handles trailing garbage like '{"a":1}}' that a
    greedy regex would swallow.
    """
    start = -1
    opener = closer = ""
    for index, char in enumerate(text):
        if char in "{[":
            start = index
            opener = char
            closer = "}" if char == "{" else "]"
            break
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    return None


class LLMOutputJSONParser(Generic[T]):
    """Reusable JSON parser for LLM responses."""

    def __init__(self, model: Type[T]):
        self.model = model
        self.model_name = self.model.__name__

    def try_parse(self, raw: str) -> T | None:
        logger.debug(f"[{self.model_name}] Attempting JSON parse (len={len(raw)})")

        try:
            return self.model.model_validate_json(raw)
        except ValidationError as error:
            logger.warning(f"[{self.model_name}] Raw JSON parse failed: {error}")
            cleaned = sanitize_json_string(raw)

            if cleaned != raw:
                logger.debug(f"[{self.model_name}] Sanitized JSON differs, retrying parse...")
                try:
                    return self.model.model_validate_json(cleaned)
                except ValidationError as error:
                    logger.warning(f"[{self.model_name}] Sanitized JSON still invalid: {error}")
                    return None
            else:
                logger.debug(f"[{self.model_name}] Sanitized JSON identical — skipping retry")
                return None

    def parse_output(self, output: str) -> T | None:
        output = (output or "").strip()
        if not output:
            logger.warning(f"[{self.model_name}] Empty LLM output")
            return None

        # Some providers/models wrap a JSON object in a single backtick pair,
        # e.g. `{"action":"TOOL_CALL",...}`. Unwrap that form early.
        if output.startswith("`") and output.endswith("`") and len(output) >= 2:
            inline_unwrapped = output[1:-1].strip()
            if inline_unwrapped.startswith("{") or inline_unwrapped.startswith("["):
                output = inline_unwrapped

        logger.debug(f"[{self.model_name}] Parsing output (len={len(output)})")

        if match := CLEAN_JSON_BLOCK_RE.search(output):
            logger.debug(f"[{self.model_name}] Found fenced JSON block, extracting...")
            output = match.group(1).strip()

        if parsed := self.try_parse(output):
            logger.info(f"[{self.model_name}] Successfully parsed")
            return parsed

        # Some models prepend extra prose before/after the real JSON payload.
        # Try extracting the first object/array and parse it as a last resort.
        candidates: list[str] = []
        if balanced := extract_balanced_json(output):
            candidates.append(balanced)
        for pattern in (FIRST_JSON_OBJECT_RE, FIRST_JSON_ARRAY_RE):
            if match := pattern.search(output):
                candidates.append(match.group(0).strip())

        seen: set[str] = set()
        for extracted in candidates:
            if extracted == output or extracted in seen:
                continue
            seen.add(extracted)

            logger.debug(
                f"[{self.model_name}] Trying extracted JSON candidate (len={len(extracted)})"
            )
            if parsed := self.try_parse(extracted):
                logger.info(f"[{self.model_name}] Successfully parsed extracted JSON candidate")
                return parsed

        logger.error(f"[{self.model_name}] No valid JSON found in output")
        return None
