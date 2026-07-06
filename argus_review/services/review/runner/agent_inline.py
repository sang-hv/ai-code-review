from argus_review.libs.diff.models import FileMode
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
from argus_review.services.review.internal.inline.schema import InlineCommentSchema
from argus_review.services.review.internal.inline.types import InlineCommentServiceProtocol
from argus_review.services.review.runner.types import ReviewRunnerProtocol
from argus_review.services.vcs.types import ReviewInfoSchema, VCSClientProtocol

logger = get_logger("AGENT_INLINE_REVIEW_RUNNER")


def _normalize_file(value: str) -> str:
    return (value or "").strip().replace("\\", "/").lstrip("/")


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
        try:
            raw_diff = self.git.get_diff(review_info.base_sha, review_info.head_sha)
            diff = self.diff.parse(raw_diff)
        except Exception as error:
            logger.warning(f"Could not parse diff for line validation, skipping validation: {error}")
            return {}

        result: dict[str, set[int]] = {}
        for file in diff.files:
            if file.mode == FileMode.DELETED:
                continue
            lines = {
                line.number
                for hunk in file.hunks
                for line in hunk.new_range.lines
                if line.number is not None
            }
            result[_normalize_file(file.new_name or file.orig_name)] = lines

        return result

    def _validate_line_numbers(
            self,
            comments: list[InlineCommentSchema],
            review_info: ReviewInfoSchema,
    ) -> list[InlineCommentSchema]:
        valid_map = self._valid_lines_by_file(review_info)
        if not valid_map:
            # Nothing to validate against (empty or unparsable diff) — stay lenient.
            return comments

        kept: list[InlineCommentSchema] = []
        dropped = 0
        for comment in comments:
            valid_lines = valid_map.get(_normalize_file(comment.file))
            if valid_lines is not None and comment.line in valid_lines:
                kept.append(comment)
            else:
                dropped += 1
                logger.info(
                    f"Dropping inline comment with non-diff line anchor: {comment.file}:{comment.line}"
                )

        if dropped:
            logger.info(f"Dropped {dropped} inline comment(s) that did not anchor to a diff line")

        return kept

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

        logger.info(f"Starting agent inline review: {len(changed_files)} files changed")

        review_info.changed_files = changed_files
        inventory = get_conventions_service().materialize("inline")
        prompt_context = build_prompt_context_from_review_info(review_info)

        prompt = self.prompt.build_agent_light_inline_request(
            context=prompt_context,
            base_sha=review_info.base_sha,
            head_sha=review_info.head_sha,
            conventions_inventory=inventory,
        )
        prompt_system = self.prompt.build_system_agent_light_inline_request()
        prompt_result = await self.review_agent_llm_gateway.ask(prompt, prompt_system)

        parsed = self.inline_comment.parse_model_output(prompt_result).dedupe()
        parsed.root = self._validate_line_numbers(parsed.root, review_info)
        parsed.root = self.policy.apply_for_inline_comments(parsed.root)
        if not parsed.root:
            logger.info("No inline comments from agent inline review")
            return

        logger.info(f"Posting {len(parsed.root)} inline comments (agent inline review)")
        await self.review_comment_gateway.process_inline_comments(parsed)
        await hook.emit_inline_review_complete(self.cost.aggregate())
