from argus_review.libs.asynchronous.gather import bounded_gather
from argus_review.libs.logger import get_logger
from argus_review.services.cost.types import CostServiceProtocol
from argus_review.services.diff.types import DiffServiceProtocol
from argus_review.services.git.types import GitServiceProtocol
from argus_review.services.hook import hook
from argus_review.services.policy.types import PolicyServiceProtocol
from argus_review.services.prompt.adapter import build_prompt_context_from_review_info
from argus_review.services.prompt.types import PromptServiceProtocol
from argus_review.services.review.gateway.types import ReviewLLMGatewayProtocol, ReviewCommentGatewayProtocol
from argus_review.services.review.internal.inline.types import InlineCommentServiceProtocol
from argus_review.services.review.runner.types import ReviewRunnerProtocol
from argus_review.services.vcs.types import ReviewInfoSchema, VCSClientProtocol

logger = get_logger("INLINE_REVIEW_RUNNER")


class InlineReviewRunner(ReviewRunnerProtocol):
    def __init__(
            self,
            vcs: VCSClientProtocol,
            git: GitServiceProtocol,
            diff: DiffServiceProtocol,
            cost: CostServiceProtocol,
            prompt: PromptServiceProtocol,
            policy: PolicyServiceProtocol,
            inline_comment: InlineCommentServiceProtocol,
            review_llm_gateway: ReviewLLMGatewayProtocol,
            review_comment_gateway: ReviewCommentGatewayProtocol,
    ):
        self.vcs = vcs
        self.git = git
        self.diff = diff
        self.cost = cost
        self.prompt = prompt
        self.policy = policy
        self.inline_comment = inline_comment
        self.review_llm_gateway = review_llm_gateway
        self.review_comment_gateway = review_comment_gateway

    async def process_file(self, file: str, review_info: ReviewInfoSchema) -> None:
        raw_diff = self.git.get_diff_for_file(review_info.base_sha, review_info.head_sha, file)
        if not raw_diff.strip():
            logger.debug(f"No diff for {file}, skipping")
            return

        rendered_file = self.diff.render_file(
            file=file,
            base_sha=review_info.base_sha,
            head_sha=review_info.head_sha,
            raw_diff=raw_diff,
        )
        prompt_context = build_prompt_context_from_review_info(review_info)
        prompt = self.prompt.build_inline_request(rendered_file, prompt_context)
        prompt_system = self.prompt.build_system_inline_request(prompt_context)
        prompt_result = await self.review_llm_gateway.ask(prompt, prompt_system)

        comments = self.inline_comment.parse_model_output(prompt_result).dedupe()
        comments.root = self.policy.apply_for_inline_comments(comments.root)
        if not comments.root:
            logger.info(f"No inline comments for file: {file}")
            return

        logger.info(f"Posting {len(comments.root)} inline comments to {file}")
        await self.review_comment_gateway.process_inline_comments(comments)

    async def run(self) -> None:
        await hook.emit_inline_review_start()

        comments = await self.review_comment_gateway.get_inline_comments()
        if comments:
            logger.info(f"Detected {len(comments)} existing AI inline comments, skipping inline review")
            return

        review_info = await self.vcs.get_review_info()
        logger.info(f"Starting inline review: {len(review_info.changed_files)} files changed")

        changed_files = self.policy.apply_for_files(review_info.changed_files)
        await bounded_gather([
            self.process_file(changed_file, review_info)
            for changed_file in changed_files
        ])
        await hook.emit_inline_review_complete(self.cost.aggregate())
