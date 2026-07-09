from argus_review.config import settings
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
from argus_review.services.review.internal.inline.line_validator import (
    compute_valid_lines_by_file,
    filter_by_valid_lines,
)
from argus_review.services.review.internal.inline.schema import InlineCommentListSchema, InlineCommentSchema
from argus_review.services.review.internal.inline.types import InlineCommentServiceProtocol
from argus_review.services.review.runner.chunk import _chunk
from argus_review.services.review.runner.types import ReviewRunnerProtocol
from argus_review.services.vcs.types import ReviewInfoSchema, VCSClientProtocol

logger = get_logger("AGENT_INLINE_REVIEW_RUNNER")


class AgentInlineReviewRunner(ReviewRunnerProtocol):
    """
    Agent-light inline review: one agent session driven by a lightweight prompt
    (metadata + convention inventory only). Instead of one LLM call per file, the
    agent explores diffs/source through read-only tools and returns a single JSON
    array of inline comments.

    Because a model can hallucinate line numbers, comments are validated against
    the actual diff: any comment whose (file, line) does not anchor to a real
    new-side diff line is dropped before posting (the VCS would reject them
    anyway). Validation is lenient when the diff can't be parsed.
    """

    def __init__(
            self,
            vcs: VCSClientProtocol,
            git: GitServiceProtocol,
            diff: DiffServiceProtocol,
            cost: CostServiceProtocol,
            prompt: PromptServiceProtocol,
            policy: PolicyServiceProtocol,
            inline_comment: InlineCommentServiceProtocol,
            review_agent_llm_gateway: ReviewLLMGatewayProtocol,
            review_comment_gateway: ReviewCommentGatewayProtocol,
    ):
        self.vcs = vcs
        self.git = git
        self.diff = diff
        self.cost = cost
        self.prompt = prompt
        self.policy = policy
        self.inline_comment = inline_comment
        self.review_agent_llm_gateway = review_agent_llm_gateway
        self.review_comment_gateway = review_comment_gateway

    def _valid_lines_by_file(self, review_info: ReviewInfoSchema) -> dict[str, set[int]]:
        """Map each changed file to the set of new-side line numbers a diff comment can anchor to."""
        return compute_valid_lines_by_file(self.git, self.diff, review_info)

    def _validate_line_numbers(
            self,
            comments: list[InlineCommentSchema],
            review_info: ReviewInfoSchema,
    ) -> list[InlineCommentSchema]:
        valid_map = self._valid_lines_by_file(review_info)
        return filter_by_valid_lines(comments, valid_map, review_info.changed_files)

    async def _review_chunk(
            self,
            review_info: ReviewInfoSchema,
            files: list[str],
            inventory: str,
    ) -> list[InlineCommentSchema]:
        """Run one agent session (clean context) for a single chunk of files."""
        chunk_review_info = review_info.model_copy(deep=True)
        chunk_review_info.changed_files = files

        prompt_context = build_prompt_context_from_review_info(chunk_review_info)
        prompt = self.prompt.build_agent_light_inline_request(
            context=prompt_context,
            base_sha=chunk_review_info.base_sha,
            head_sha=chunk_review_info.head_sha,
            conventions_inventory=inventory,
        )
        prompt_system = self.prompt.build_system_agent_light_inline_request()
        prompt_result = await self.review_agent_llm_gateway.ask(prompt, prompt_system)

        return self.inline_comment.parse_model_output(prompt_result).root

    async def run(self) -> None:
        await hook.emit_inline_review_start()

        comments = await self.review_comment_gateway.get_inline_comments()
        if comments:
            logger.info(f"Detected {len(comments)} existing AI inline comments, skipping agent inline review")
            return

        review_info = await self.vcs.get_review_info()
        changed_files = self.policy.apply_for_files(review_info.changed_files)
        if not changed_files:
            logger.info("No files to review for agent inline")
            return

        chunks = _chunk(changed_files, settings.agent.max_files_per_chunk)
        logger.info(
            f"Starting agent inline review: {len(changed_files)} files changed in {len(chunks)} chunk(s)"
        )

        review_info.changed_files = changed_files
        inventory = get_conventions_service().materialize("inline")

        all_comments: list[InlineCommentSchema] = []
        for index, files in enumerate(chunks, 1):
            logger.info(f"Reviewing chunk {index}/{len(chunks)} ({len(files)} files)")
            all_comments.extend(await self._review_chunk(review_info, files, inventory))

        parsed = InlineCommentListSchema(root=all_comments).dedupe()
        parsed.root = self._validate_line_numbers(parsed.root, review_info)
        parsed.root = self.policy.apply_for_inline_comments(parsed.root)
        if not parsed.root:
            logger.info("No inline comments from agent inline review")
            return

        logger.info(f"Posting {len(parsed.root)} inline comments (agent inline review)")
        await self.review_comment_gateway.process_inline_comments(parsed)
        await hook.emit_inline_review_complete(self.cost.aggregate())
