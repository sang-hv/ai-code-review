from argus_review.config import settings
from argus_review.libs.logger import get_logger
from argus_review.services.conventions.service import get_conventions_service
from argus_review.services.cost.types import CostServiceProtocol
from argus_review.services.git.types import GitServiceProtocol
from argus_review.services.hook import hook
from argus_review.services.policy.types import PolicyServiceProtocol
from argus_review.services.prompt.adapter import build_prompt_context_from_review_info
from argus_review.services.prompt.types import PromptServiceProtocol
from argus_review.services.review.gateway.types import ReviewLLMGatewayProtocol, ReviewCommentGatewayProtocol
from argus_review.services.review.internal.summary.schema import SummaryCommentSchema
from argus_review.services.review.internal.summary.types import SummaryCommentServiceProtocol
from argus_review.services.review.runner.chunk import _chunk
from argus_review.services.review.runner.types import ReviewRunnerProtocol
from argus_review.services.vcs.types import ReviewInfoSchema, VCSClientProtocol

logger = get_logger("AGENT_SUMMARY_REVIEW_RUNNER")


class AgentSummaryReviewRunner(ReviewRunnerProtocol):
    """
    Agent-light summary review: one agent session driven by a lightweight prompt
    (metadata + convention inventory only). The agent pulls in the diff/source it
    needs through read-only tools instead of receiving the full diff and full
    conventions up front. The final text is posted through the existing summary
    comment gateway.
    """

    def __init__(
            self,
            vcs: VCSClientProtocol,
            git: GitServiceProtocol,
            cost: CostServiceProtocol,
            prompt: PromptServiceProtocol,
            policy: PolicyServiceProtocol,
            summary_comment: SummaryCommentServiceProtocol,
            review_agent_llm_gateway: ReviewLLMGatewayProtocol,
            review_comment_gateway: ReviewCommentGatewayProtocol,
    ):
        self.vcs = vcs
        self.git = git
        self.cost = cost
        self.prompt = prompt
        self.policy = policy
        self.summary_comment = summary_comment
        self.review_agent_llm_gateway = review_agent_llm_gateway
        self.review_comment_gateway = review_comment_gateway

    async def _review_chunk(
            self,
            review_info: ReviewInfoSchema,
            files: list[str],
            inventory: str,
    ) -> str:
        """Run one agent session (clean context) for a single chunk of files."""
        chunk_review_info = review_info.model_copy(deep=True)
        chunk_review_info.changed_files = files

        prompt_context = build_prompt_context_from_review_info(chunk_review_info)
        prompt = self.prompt.build_agent_light_summary_request(
            context=prompt_context,
            base_sha=chunk_review_info.base_sha,
            head_sha=chunk_review_info.head_sha,
            conventions_inventory=inventory,
        )
        prompt_system = self.prompt.build_system_agent_light_summary_request()
        prompt_result = await self.review_agent_llm_gateway.ask(prompt, prompt_system)

        return self.summary_comment.parse_model_output(prompt_result).text

    async def run(self) -> None:
        await hook.emit_summary_review_start()

        comments = await self.review_comment_gateway.get_summary_comments()
        if comments:
            logger.info(f"Detected {len(comments)} existing AI summary comments, skipping agent summary review")
            return

        review_info = await self.vcs.get_review_info()
        changed_files = self.policy.apply_for_files(review_info.changed_files)
        if not changed_files:
            logger.info("No files to review for agent summary")
            return

        chunks = _chunk(changed_files, settings.agent.max_files_per_chunk)
        logger.info(
            f"Starting agent summary review: {len(changed_files)} files changed in {len(chunks)} chunk(s)"
        )

        review_info.changed_files = changed_files
        inventory = get_conventions_service().materialize("summary")

        summaries: list[str] = []
        for index, files in enumerate(chunks, 1):
            logger.info(f"Reviewing chunk {index}/{len(chunks)} ({len(files)} files)")
            text = await self._review_chunk(review_info, files, inventory)
            if text.strip():
                summaries.append(text.strip())

        # Reduce: concatenate per-chunk summaries instead of an extra LLM call.
        final_text = "\n\n".join(summaries)
        if not final_text:
            logger.warning("Agent summary output was empty, skipping comment")
            return

        logger.info(f"Posting agent summary review comment ({len(final_text)} chars)")
        await self.review_comment_gateway.process_summary_comment(SummaryCommentSchema(text=final_text))
        await hook.emit_summary_review_complete(self.cost.aggregate())
