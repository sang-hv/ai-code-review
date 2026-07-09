import asyncio

from argus_review.config import settings
from argus_review.libs.logger import get_logger
from argus_review.services.agent.loop.types import AgentLoopServiceProtocol
from argus_review.services.artifacts.types import ArtifactsServiceProtocol
from argus_review.services.cost.schema import CalculateCostSchema
from argus_review.services.cost.types import CostServiceProtocol
from argus_review.services.hook import hook
from argus_review.services.llm.types import LLMClientProtocol
from argus_review.services.review.gateway.types import ReviewLLMGatewayProtocol

logger = get_logger("REVIEW_AGENT_LLM_GATEWAY")


class ReviewAgentLLMGateway(ReviewLLMGatewayProtocol):
    def __init__(
            self,
            llm: LLMClientProtocol,
            cost: CostServiceProtocol,
            artifacts: ArtifactsServiceProtocol,
            agent_loop: AgentLoopServiceProtocol,
            fallback_gateway: ReviewLLMGatewayProtocol,
    ):
        self.llm = llm
        self.cost = cost
        self.artifacts = artifacts
        self.agent_loop = agent_loop
        self.fallback_gateway = fallback_gateway

    @staticmethod
    def _synthesize_empty_response(prompt_system: str) -> str:
        system = (prompt_system or "").lower()
        language = (settings.review.language or "").strip().lower()
        is_vietnamese = "vietnam" in language or "tiếng việt" in language

        if (
            ('"summary"' in system and '"comments"' in system)
            or ("single json object" in system and "comments" in system)
        ):
            summary_text = (
                "Kết quả dự phòng: agent trả về rỗng cho chunk này."
                if is_vietnamese
                else "Agent fallback: empty output for this chunk."
            )
            return f'{{"summary":"{summary_text}","comments":[]}}'

        if "json array of inline comments" in system:
            return "[]"

        if "summary review as plain markdown text" in system:
            return (
                "Kết quả dự phòng: agent trả về rỗng cho chunk này."
                if is_vietnamese
                else "Agent fallback: empty output for this chunk."
            )

        return "Agent fallback: empty output."

    @staticmethod
    def _is_invalid_final_output(text: str) -> bool:
        body = (text or "").strip().lower()
        if not body:
            return True

        if body.startswith("<bash>") and body.endswith("</bash>"):
            return True

        if "<tool_calls>" in body or "<tool_call>" in body:
            return True

        if body.startswith("git ") or body.startswith("rg ") or body.startswith("grep "):
            return True

        return ('"action"' in body and '"tool_call"' in body) or ('"action"' in body and '"final"' in body)

    async def _fallback_or_synthesize(self, prompt: str, prompt_system: str) -> str:
        fallback_timeout = max(15, min(int(settings.llm.http_client.timeout) + 5, 120))
        try:
            fallback_text = await asyncio.wait_for(
                self.fallback_gateway.ask(prompt, prompt_system),
                timeout=fallback_timeout,
            )
            if (fallback_text or "").strip():
                return fallback_text

            logger.warning(
                "Direct fallback returned empty output after invalid/empty agent FINAL; "
                "using synthesized fallback output"
            )
            return self._synthesize_empty_response(prompt_system)
        except Exception as fallback_error:
            logger.warning(
                f"Direct fallback failed after invalid/empty agent FINAL: {fallback_error}. "
                "Using synthesized fallback output"
            )
            return self._synthesize_empty_response(prompt_system)

    async def ask(self, prompt: str, prompt_system: str) -> str:
        try:
            await hook.emit_chat_start(prompt, prompt_system)
            loop_result = await self.agent_loop.run(
                prompt=prompt,
                prompt_system=prompt_system,
            )

            if self._is_invalid_final_output(loop_result.final_text or ""):
                logger.warning(
                    "Agent loop returned invalid/empty FINAL output, falling back to direct chat"
                )
                return await self._fallback_or_synthesize(prompt, prompt_system)

            report = self.cost.calculate(
                CalculateCostSchema(
                    prompt_tokens=loop_result.prompt_tokens,
                    completion_tokens=loop_result.completion_tokens
                )
            )
            if report:
                logger.info(report.pretty())

            await hook.emit_chat_complete(loop_result.final_text, report)
            await self.artifacts.save_llm(
                prompt=prompt,
                response=loop_result.final_text,
                cost_report=report,
                prompt_system=prompt_system,
            )
            return loop_result.final_text
        except Exception as error:
            logger.exception(f"Agent mode failed, falling back to direct chat: {error}")
            await hook.emit_chat_error(prompt, prompt_system)
            return await self.fallback_gateway.ask(prompt, prompt_system)
