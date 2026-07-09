import re

from argus_review.libs.llm.output_json_parser import LLMOutputJSONParser
from argus_review.libs.logger import get_logger
from argus_review.services.review.internal.agent_combined.schema import AgentCombinedResultSchema
from argus_review.services.review.internal.agent_combined.types import AgentCombinedResultServiceProtocol
from argus_review.services.review.internal.inline.schema import InlineCommentSchema, InlineCommentListSchema

logger = get_logger("AGENT_COMBINED_RESULT_SERVICE")

FIRST_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*}", re.MULTILINE)
_BULLET_PREFIX_RE = re.compile(r"^(?:[-*]\s+|\d+\.\s+)")
_LINE_WITH_POSITION_RE = re.compile(r"^(?P<line>\d+)\s*(?:[:-]\s*|\s+)(?P<message>.+)$")


class AgentCombinedResultService(AgentCombinedResultServiceProtocol):
    def __init__(self):
        self.parser = LLMOutputJSONParser(model=AgentCombinedResultSchema)

    @staticmethod
    def _is_probable_file_path(value: str) -> bool:
        candidate = value.strip().strip("`")
        if not candidate or " " in candidate:
            return False

        special = {"Dockerfile", "Makefile", "Jenkinsfile"}
        return "/" in candidate or "." in candidate or candidate in special

    def _parse_inline_comment_line(self, line: str) -> InlineCommentSchema | None:
        text = _BULLET_PREFIX_RE.sub("", (line or "").strip())
        if ":" not in text:
            return None

        file_part, remainder = text.split(":", 1)
        file_candidate = file_part.strip().strip("`")
        if not self._is_probable_file_path(file_candidate):
            return None

        remainder = remainder.strip()
        match = _LINE_WITH_POSITION_RE.match(remainder)
        if not match:
            return None

        try:
            return InlineCommentSchema(
                file=file_candidate,
                line=int(match.group("line")),
                message=match.group("message").strip(),
            )
        except Exception:
            return None

    def _extract_inline_comments_from_text(self, output: str) -> tuple[list[InlineCommentSchema], str]:
        comments: list[InlineCommentSchema] = []
        summary_lines: list[str] = []

        for line in (output or "").splitlines():
            parsed = self._parse_inline_comment_line(line)
            if parsed is None:
                summary_lines.append(line)
                continue
            comments.append(parsed)

        deduped_comments = InlineCommentListSchema(root=comments).dedupe().root
        summary = "\n".join(line for line in summary_lines if line.strip()).strip()
        return deduped_comments, summary

    def parse_model_output(self, output: str) -> AgentCombinedResultSchema:
        output = (output or "").strip()
        if not output:
            logger.warning("LLM returned empty string for agent combined review")
            return AgentCombinedResultSchema()

        if parsed := self.parser.parse_output(output):
            return parsed

        logger.info("Combined result is not valid JSON, trying recovery strategies")

        if json_object_match := FIRST_JSON_OBJECT_RE.search(output):
            extracted = json_object_match.group(0)
            logger.debug(f"Extracted potential JSON object (len={len(extracted)})")

            if parsed := self.parser.try_parse(extracted):
                logger.info("Successfully parsed JSON after extracting object from output")
                return parsed
            else:
                logger.debug("Extracted JSON object is still invalid after sanitization")
        else:
            logger.debug("No JSON object found in LLM output")

        comments, summary = self._extract_inline_comments_from_text(output)
        if comments:
            logger.info(f"Recovered {len(comments)} inline comment(s) from plain-text fallback")

        logger.info("Falling back to plain-text summary for combined result")
        return AgentCombinedResultSchema(summary=summary or output, comments=comments)
