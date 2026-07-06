from argus_review.libs.logger import get_logger
from argus_review.services.conventions.service import get_conventions_service
from argus_review.services.cost.types import CostServiceProtocol
from argus_review.services.git.types import GitServiceProtocol
from argus_review.services.hook import hook
from argus_review.services.policy.types import PolicyServiceProtocol
from argus_review.services.prompt.adapter import build_prompt_context_from_review_info
from argus_review.services.prompt.types import PromptServiceProtocol
from argus_review.services.review.gateway.types import ReviewLLMGatewayProtocol, ReviewCommentGatewayProtocol
from argus_review.services.review.internal.summary.types import SummaryCommentServiceProtocol
from argus_review.services.review.runner.types import ReviewRunnerProtocol
from argus_review.services.vcs.types import VCSClientProtocol

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

        logger.info(f"Starting agent summary review: {len(changed_files)} files changed")

        review_info.changed_files = changed_files
        inventory = get_conventions_service().materialize("summary")
        prompt_context = build_prompt_context_from_review_info(review_info)

        prompt = self.prompt.build_agent_light_summary_request(
            context=prompt_context,
            base_sha=review_info.base_sha,
            head_sha=review_info.head_sha,
            conventions_inventory=inventory,
        )
        prompt_system = self.prompt.build_system_agent_light_summary_request()
        prompt_result = await self.review_agent_llm_gateway.ask(prompt, prompt_system)

        summary = self.summary_comment.parse_model_output(prompt_result)
        if not summary.text.strip():
            logger.warning("Agent summary output was empty, skipping comment")
            return

        logger.info(f"Posting agent summary review comment ({len(summary.text)} chars)")
        await self.review_comment_gateway.process_summary_comment(summary)
        await hook.emit_summary_review_complete(self.cost.aggregate())
