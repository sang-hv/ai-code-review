import re

from argus_review.libs.llm.output_json_parser import LLMOutputJSONParser
from argus_review.libs.logger import get_logger
from argus_review.services.review.internal.agent_combined.schema import AgentCombinedResultSchema
from argus_review.services.review.internal.agent_combined.types import AgentCombinedResultServiceProtocol

logger = get_logger("AGENT_COMBINED_RESULT_SERVICE")

FIRST_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*}", re.MULTILINE)


class AgentCombinedResultService(AgentCombinedResultServiceProtocol):
    def __init__(self):
        self.parser = LLMOutputJSONParser(model=AgentCombinedResultSchema)

    def parse_model_output(self, output: str) -> AgentCombinedResultSchema:
        output = (output or "").strip()
        if not output:
            logger.warning("LLM returned empty string for agent combined review")
            return AgentCombinedResultSchema()

        if parsed := self.parser.parse_output(output):
            return parsed

        logger.warning("Failed to parse JSON, trying to extract first JSON object...")

        if json_object_match := FIRST_JSON_OBJECT_RE.search(output):
            extracted = json_object_match.group(0)
            logger.debug(f"Extracted potential JSON object (len={len(extracted)})")

            if parsed := self.parser.try_parse(extracted):
                logger.info("Successfully parsed JSON after extracting object from output")
                return parsed
            else:
                logger.error("Extracted JSON object is still invalid after sanitization")
        else:
            logger.error("No JSON object found in LLM output")

        return AgentCombinedResultSchema()
