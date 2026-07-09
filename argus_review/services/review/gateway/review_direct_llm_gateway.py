from argus_review.libs.logger import get_logger
from argus_review.config import settings
from argus_review.services.artifacts.types import ArtifactsServiceProtocol
from argus_review.services.cost.schema import CalculateCostSchema
from argus_review.services.cost.types import CostServiceProtocol
from argus_review.services.hook import hook
from argus_review.services.llm.types import LLMClientProtocol, ChatResultSchema
from argus_review.services.review.gateway.types import ReviewLLMGatewayProtocol

logger = get_logger("REVIEW_DIRECT_LLM_GATEWAY")


class ReviewDirectLLMGateway(ReviewLLMGatewayProtocol):
    def __init__(
            self,
            llm: LLMClientProtocol,
            cost: CostServiceProtocol,
            artifacts: ArtifactsServiceProtocol,
    ):
        self.llm = llm
        self.cost = cost
        self.artifacts = artifacts

    @staticmethod
    def _synthesize_empty_response(prompt_system: str) -> str | None:
        system = (prompt_system or "").lower()
        language = (settings.review.language or "").strip().lower()
        is_vietnamese = "vietnam" in language or "tiếng việt" in language

        if (
            ('"summary"' in system and '"comments"' in system)
            or ("single json object" in system and "comments" in system)
        ):
            summary_text = (
                "Kết quả dự phòng: mô hình trả về rỗng cho chunk này."
                if is_vietnamese
                else "Agent fallback: model returned empty response for this chunk."
            )
            return (
                f'{{"summary":"{summary_text}",' 
                '"comments":[]}'
            )

        if "json array of inline comments" in system:
            return "[]"

        if "summary review as plain markdown text" in system:
            return (
                "Kết quả dự phòng: mô hình trả về rỗng cho chunk này."
                if is_vietnamese
                else "Agent fallback: model returned empty response for this chunk."
            )

        return None

    @staticmethod
    def _is_control_protocol_output(text: str) -> bool:
        body = (text or "").strip().lower()
        if not body:
            return False

        if "<tool_calls>" in body or "<tool_call>" in body:
            return True

        return ('"action"' in body and '"tool_call"' in body) or ('"action"' in body and '"final"' in body)

    async def ask(self, prompt: str, prompt_system: str) -> str:
        try:
            await hook.emit_chat_start(prompt, prompt_system)
            result = await self.llm.chat(prompt, prompt_system)
            if self._is_control_protocol_output(result.text or ""):
                synthesized = self._synthesize_empty_response(prompt_system)
                if synthesized is not None:
                    logger.warning(
                        "LLM returned control-protocol content in direct review mode; "
                        "using synthesized fallback output"
                    )
                    result = ChatResultSchema(
                        text=synthesized,
                        total_tokens=result.total_tokens,
                        prompt_tokens=result.prompt_tokens,
                        completion_tokens=result.completion_tokens,
                    )

            if not (result.text or "").strip():
                synthesized = self._synthesize_empty_response(prompt_system)
                if synthesized is not None:
                    logger.warning(
                        f"LLM returned an empty response (prompt length={len(prompt)} chars); "
                        "using synthesized fallback output"
                    )
                    result = ChatResultSchema(
                        text=synthesized,
                        total_tokens=result.total_tokens,
                        prompt_tokens=result.prompt_tokens,
                        completion_tokens=result.completion_tokens,
                    )
                else:
                    logger.warning(
                        f"LLM returned an empty response (prompt length={len(prompt)} chars); retrying once"
                    )
                    retry_result = await self.llm.chat(prompt, prompt_system)
                    if (retry_result.text or "").strip():
                        result = retry_result
                    else:
                        logger.warning("LLM retry also returned empty response")

            report = self.cost.calculate(
                CalculateCostSchema(
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens
                )
            )
            if report:
                logger.info(report.pretty())

            await hook.emit_chat_complete(result, report)
            await self.artifacts.save_llm(
                prompt=prompt,
                response=result.text,
                cost_report=report,
                prompt_system=prompt_system,
            )

            return result.text
        except Exception as error:
            logger.exception(f"LLM request failed: {error}")
            await hook.emit_chat_error(prompt, prompt_system)
