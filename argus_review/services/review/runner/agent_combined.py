from argus_review.libs.logger import get_logger
from argus_review.services.conventions.service import get_conventions_service
from argus_review.services.cost.types import CostServiceProtocol
from argus_review.services.diff.types import DiffServiceProtocol
from argus_review.services.git.types import GitServiceProtocol
from argus_review.services.hook import hook
from argus_review.services.policy.types import PolicyServiceProtocol
from argus_review.services.prompt.adapter import build_prompt_context_from_review_info
from argus_review.services.prompt.types import PromptServiceProtocol
from argus_review.services.review.gateway.types import ReviewLLMGatewayProtocol, ReviewCommentGatewayProtocol
from argus_review.services.review.internal.agent_combined.types import AgentCombinedResultServiceProtocol
from argus_review.services.review.internal.inline.line_validator import (
    compute_valid_lines_by_file,
    filter_by_valid_lines,
)
from argus_review.services.review.internal.inline.schema import InlineCommentListSchema
from argus_review.services.review.internal.summary.schema import SummaryCommentSchema
from argus_review.services.review.runner.types import ReviewRunnerProtocol
from argus_review.services.vcs.types import VCSClientProtocol

logger = get_logger("AGENT_REVIEW_RUNNER")


class AgentReviewRunner(ReviewRunnerProtocol):
    """
    Agent-light combined review: a *single* agent session produces both the
    summary and the inline comments, instead of running two independent agent
    sessions (`run-agent-inline` + `run-agent-summary`) that would each explore
    the diff/conventions from scratch. This is the runner behind `run-agent`
    and roughly halves the quota cost of that command compared to running the
    two standalone flows back to back.

    The FINAL output is a single JSON object `{"summary": ..., "comments": [...]}`,
    parsed by `AgentCombinedResultService`. Inline comments go through the same
    diff-line validation as `AgentInlineReviewRunner`.
    """

    def __init__(
            self,
            vcs: VCSClientProtocol,
            git: GitServiceProtocol,
            diff: DiffServiceProtocol,
            cost: CostServiceProtocol,
            prompt: PromptServiceProtocol,
            policy: PolicyServiceProtocol,
            agent_combined_result: AgentCombinedResultServiceProtocol,
            review_agent_llm_gateway: ReviewLLMGatewayProtocol,
            review_comment_gateway: ReviewCommentGatewayProtocol,
    ):
        self.vcs = vcs
        self.git = git
        self.diff = diff
        self.cost = cost
        self.prompt = prompt
        self.policy = policy
        self.agent_combined_result = agent_combined_result
        self.review_agent_llm_gateway = review_agent_llm_gateway
        self.review_comment_gateway = review_comment_gateway

    async def run(self) -> None:
        await hook.emit_inline_review_start()
        await hook.emit_summary_review_start()

        existing_inline = await self.review_comment_gateway.get_inline_comments()
        existing_summary = await self.review_comment_gateway.get_summary_comments()
        skip_inline = bool(existing_inline)
        skip_summary = bool(existing_summary)
        if skip_inline:
            logger.info(f"Detected {len(existing_inline)} existing AI inline comments, skipping agent inline part")
        if skip_summary:
            logger.info(f"Detected {len(existing_summary)} existing AI summary comments, skipping agent summary part")
        if skip_inline and skip_summary:
            return

        review_info = await self.vcs.get_review_info()
        changed_files = self.policy.apply_for_files(review_info.changed_files)
        if not changed_files:
            logger.info("No files to review for agent review")
            return

        logger.info(f"Starting agent review (combined, single session): {len(changed_files)} files changed")

        review_info.changed_files = changed_files
        inventory = get_conventions_service().materialize("combined")
        prompt_context = build_prompt_context_from_review_info(review_info)

        prompt = self.prompt.build_agent_light_combined_request(
            context=prompt_context,
            base_sha=review_info.base_sha,
            head_sha=review_info.head_sha,
            conventions_inventory=inventory,
        )
        prompt_system = self.prompt.build_system_agent_light_combined_request()
        prompt_result = await self.review_agent_llm_gateway.ask(prompt, prompt_system)

        result = self.agent_combined_result.parse_model_output(prompt_result)

        if not skip_inline:
            comments = InlineCommentListSchema(root=result.comments).dedupe()
            valid_map = compute_valid_lines_by_file(self.git, self.diff, review_info)
            comments.root = filter_by_valid_lines(comments.root, valid_map)
            comments.root = self.policy.apply_for_inline_comments(comments.root)
            if comments.root:
                logger.info(f"Posting {len(comments.root)} inline comments (agent review)")
                await self.review_comment_gateway.process_inline_comments(comments)
            else:
                logger.info("No inline comments from agent review")
            await hook.emit_inline_review_complete(self.cost.aggregate())

        if not skip_summary:
            if result.summary:
                logger.info(f"Posting agent summary review comment ({len(result.summary)} chars)")
                await self.review_comment_gateway.process_summary_comment(
                    SummaryCommentSchema(text=result.summary)
                )
            else:
                logger.warning("Agent summary output was empty, skipping comment")
            await hook.emit_summary_review_complete(self.cost.aggregate())
