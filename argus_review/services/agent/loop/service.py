import re

from argus_review.config import settings
from argus_review.libs.llm.output_json_parser import LLMOutputJSONParser
from argus_review.libs.logger import get_logger
from argus_review.services.agent.loop.schema import (
    AgentAction,
    AgentStepSchema,
    AgentTraceSchema,
    AgentLoopResultSchema
)
from argus_review.services.agent.loop.types import AgentLoopServiceProtocol
from argus_review.services.agent.tool.types import AgentToolServiceProtocol
from argus_review.services.llm.types import LLMClientProtocol, ChatResultSchema
from argus_review.services.prompt.types import PromptServiceProtocol

logger = get_logger("AGENT_LOOP_SERVICE")

_BASE_SHA_RE = re.compile(r"- Base SHA:\s*([0-9a-fA-F]{7,40})")
_HEAD_SHA_RE = re.compile(r"- Head SHA:\s*([0-9a-fA-F]{7,40})")
_FENCED_COMMAND_RE = re.compile(r"```(?:bash|sh|shell|zsh)?\s*([\s\S]*?)```", re.IGNORECASE)
_INLINE_COMMAND_RE = re.compile(r"`((?:git|rg|grep|cat|sed|head|tail|wc|ls|find)\b[^`]*)`")
_COMMAND_START_RE = re.compile(r"^(?:\$\s*)?(git|rg|grep|cat|sed|head|tail|wc|ls|find)\b", re.IGNORECASE)
# Malformed TOOL_CALL JSON (e.g. unescaped quotes inside the command value)
# still exposes the command between '"command":"' and the closing '"}'.
_MALFORMED_TOOL_CALL_RE = re.compile(
    r'"action"\s*:\s*"TOOL_CALL"\s*,\s*"command"\s*:\s*"(.+)"\s*}\s*`?\s*$',
    re.DOTALL,
)


class AgentLoopService(AgentLoopServiceProtocol):
    def __init__(
            self,
            llm: LLMClientProtocol,
            prompt: PromptServiceProtocol,
            agent_tool: AgentToolServiceProtocol,
    ):
        self.llm = llm
        self.prompt = prompt
        self.agent_tool = agent_tool
        self.max_iterations = settings.agent.max_iterations
        self.structured_tool_calls_enabled = settings.agent.structured_tool_calls_enabled
        self.unstructured_recovery_enabled = settings.agent.unstructured_recovery_enabled
        self.max_context_chars = settings.agent.max_total_context_chars
        # 0 disables the token budget check (not every provider reports usage).
        self.max_total_tokens = settings.agent.max_total_tokens

        self.compaction_enabled = settings.agent.compaction_enabled
        self.compaction_threshold = int(
            settings.agent.max_total_context_chars * settings.agent.compaction_threshold_ratio
        )
        self.max_compactions_per_run = settings.agent.max_compactions_per_run
        self.compactions_used = 0
        self.compaction_summary = ""

        self.parser = LLMOutputJSONParser(AgentStepSchema)
        self.traces: list[AgentTraceSchema] = []
        self.signatures: set[str] = set()
        self.context_used = 0
        self.tokens_used = 0

    def clear(self):
        self.traces = []
        self.signatures = set()
        self.context_used = 0
        self.tokens_used = 0
        self.compactions_used = 0
        self.compaction_summary = ""
        logger.debug("Agent loop state cleared")

    async def compact(self) -> bool:
        if self.max_compactions_per_run and self.compactions_used >= self.max_compactions_per_run:
            logger.info(
                f"Compaction cap reached ({self.compactions_used}/{self.max_compactions_per_run}); "
                "forcing final response"
            )
            return False

        logger.info(f"Compacting agent history: {len(self.traces)} traces, context_used={self.context_used}")

        prompt = self.prompt.build_agent_compaction_request(self.traces, prior_summary=self.compaction_summary)
        prompt_system = self.prompt.build_system_agent_compaction_request()
        result = await self.llm.chat(prompt=prompt, prompt_system=prompt_system)

        summary_text = (result.text or "").strip()
        if summary_text:
            self.compaction_summary = summary_text

        self.tokens_used += result.total_tokens or 0
        self.compactions_used += 1

        # Drop the raw traces/tool-output now that they're folded into the
        # summary — signatures (duplicate-command guard) are intentionally
        # NOT reset here, so the agent won't re-run a command it already used.
        self.traces = []
        self.context_used = 0

        logger.info(f"Compaction done: summary_chars={len(self.compaction_summary)}")
        if not self.compaction_summary:
            logger.info("Compaction returned empty summary; forcing final response")
            return False

        return True

    async def run_step(self, step: AgentStepSchema, chat: ChatResultSchema, iteration: int) -> AgentTraceSchema:
        if step.command in self.signatures:
            logger.debug(f"Duplicate tool call blocked at iteration {iteration}: {step.command}")
            return AgentTraceSchema(
                step=step,
                warning=f"Duplicate tool call blocked: {step.command}",
                iteration=iteration,
                raw_output=chat.text,
                total_tokens=chat.total_tokens,
                prompt_tokens=chat.prompt_tokens,
                completion_tokens=chat.completion_tokens,
            )

        self.signatures.add(step.command)
        logger.debug(f"Executing agent tool command at iteration {iteration}: {step.command}")
        tool_output = await self.agent_tool.execute(step.command)

        return AgentTraceSchema(
            step=step,
            iteration=iteration,
            raw_output=chat.text,
            tool_output=tool_output,
            total_tokens=chat.total_tokens,
            prompt_tokens=chat.prompt_tokens,
            completion_tokens=chat.completion_tokens,
        )

    @staticmethod
    def _extract_sha(pattern: re.Pattern[str], text: str) -> str | None:
        if match := pattern.search(text or ""):
            return match.group(1)
        return None

    @staticmethod
    def _normalize_candidate_command(text: str) -> str | None:
        candidate = (text or "").strip()
        if not candidate:
            return None

        # Strip common shell wrappers and prompt prefixes.
        if candidate.lower() in {"bash", "sh", "zsh", "shell"}:
            return None
        if candidate.startswith("$ "):
            candidate = candidate[2:].strip()

        if _COMMAND_START_RE.match(candidate):
            return candidate
        return None

    def _fallback_diff_command(self, original_prompt: str) -> str:
        base_sha = self._extract_sha(_BASE_SHA_RE, original_prompt)
        head_sha = self._extract_sha(_HEAD_SHA_RE, original_prompt)

        if base_sha and head_sha:
            return f"git diff --name-only {base_sha}..{head_sha}"

        return "git diff --name-only"

    def _recover_unstructured_step(
            self,
            output: str,
            original_prompt: str,
            allow_diff_intent_fallback: bool = True,
    ) -> AgentStepSchema | None:
        text = (output or "").strip()
        if not text:
            return None

        # Malformed TOOL_CALL JSON (unescaped quotes in command) — recover the raw command.
        if malformed := _MALFORMED_TOOL_CALL_RE.search(text):
            command = malformed.group(1).strip().replace('\\"', '"')
            if command:
                logger.info(f"Recovered TOOL_CALL from malformed JSON: {command}")
                return AgentStepSchema(action=AgentAction.TOOL_CALL, command=command)

        candidates: list[str] = []

        if fenced := _FENCED_COMMAND_RE.search(text):
            fenced_body = (fenced.group(1) or "").strip()
            for line in fenced_body.splitlines():
                candidates.append(line.strip())

        for line in text.splitlines():
            candidates.append(line.strip())

        for inline_command in _INLINE_COMMAND_RE.findall(text):
            candidates.append(inline_command.strip())

        for candidate in candidates:
            if command := self._normalize_candidate_command(candidate):
                logger.info(f"Recovered TOOL_CALL from unstructured output: {command}")
                return AgentStepSchema(action=AgentAction.TOOL_CALL, command=command)

        lowered = text.lower()
        if allow_diff_intent_fallback and "diff" in lowered and any(
            token in lowered for token in ("need", "missing", "cannot", "can't")
        ):
            command = self._fallback_diff_command(original_prompt)
            logger.info(f"Recovered TOOL_CALL using diff fallback command: {command}")
            return AgentStepSchema(action=AgentAction.TOOL_CALL, command=command)

        return None

    async def force_final(
            self,
            prompt: str,
            prompt_system: str,
    ) -> AgentLoopResultSchema:
        logger.info("Forcing FINAL response after loop limits reached")

        agent_prompt = self.prompt.build_agent_request(
            traces=self.traces,
            force_final=True,
            original_prompt=prompt,
            original_prompt_system=prompt_system,
            compaction_summary=self.compaction_summary,
        )
        agent_prompt_system = self.prompt.build_system_agent_request()
        logger.debug(
            f"Force-final prompt "
            f"(prompt_chars={len(agent_prompt)}, system_chars={len(agent_prompt_system)}, "
            f"traces={len(self.traces)})"
        )

        fallback_result = await self.llm.chat(
            prompt=agent_prompt,
            prompt_system=agent_prompt_system,
        )
        fallback_text = fallback_result.text
        fallback_step: AgentStepSchema | None = self.parser.parse_output(fallback_text)
        logger.debug(
            f"Forced FINAL raw response received; "
            f"parsed_as_final={bool(fallback_step and fallback_step.action.is_final)}"
        )

        final_text = (
            fallback_step.content
            if fallback_step and fallback_step.action.is_final
            else fallback_text
        )

        self.traces.append(
            AgentTraceSchema(
                step=fallback_step or AgentStepSchema(
                    action=AgentAction.FINAL,
                    content=fallback_text or "Empty model response",
                ),
                warning="Forced final response after max_requests/context_limit.",
                iteration=len(self.traces) + 1,
                raw_output=fallback_text,
                total_tokens=fallback_result.total_tokens,
                prompt_tokens=fallback_result.prompt_tokens,
                completion_tokens=fallback_result.completion_tokens,
            )
        )

        return AgentLoopResultSchema(
            traces=self.traces,
            final_text=final_text,
            stop_reason="max_requests_or_context_limit",
        )

    async def run(self, prompt: str, prompt_system: str) -> AgentLoopResultSchema:
        self.clear()
        logger.info(
            f"Starting agent loop: max_iterations={self.max_iterations}, "
            f"max_context_chars={self.max_context_chars}, max_total_tokens={self.max_total_tokens or 'disabled'}"
        )

        for iteration in range(1, self.max_iterations + 1):
            logger.debug(f"Agent loop iteration started: {iteration}")

            agent_prompt = self.prompt.build_agent_request(
                traces=self.traces,
                force_final=False,
                original_prompt=prompt,
                original_prompt_system=prompt_system,
                compaction_summary=self.compaction_summary,
            )
            agent_prompt_system = self.prompt.build_system_agent_request()
            logger.debug(
                f"Agent prompt for iteration {iteration} "
                f"(prompt_chars={len(agent_prompt)}, system_chars={len(agent_prompt_system)}, "
                f"traces={len(self.traces)})"
            )
            
            result = await self.llm.chat(
                prompt=agent_prompt,
                prompt_system=agent_prompt_system,
            )
            logger.debug(f"Agent LLM response at iteration {iteration}: {result.text[:500]}")

            if self.structured_tool_calls_enabled and result.tool_command:
                trace = await self.run_step(
                    step=AgentStepSchema(action=AgentAction.TOOL_CALL, command=result.tool_command),
                    chat=result,
                    iteration=iteration,
                )
                self.traces.append(trace)

                self.context_used += len(trace.tool_output or "")
                self.tokens_used += trace.total_tokens or 0
                logger.debug(
                    f"Agent loop context usage after iteration {iteration}: "
                    f"{self.context_used}/{self.max_context_chars} chars, "
                    f"{self.tokens_used}/{self.max_total_tokens or '∞'} tokens"
                )

                if self.context_used >= self.max_context_chars:
                    if self.compaction_enabled:
                        if not await self.compact():
                            break
                    else:
                        logger.info("Agent context limit reached, forcing final response")
                        break
                elif self.compaction_enabled and self.context_used >= self.compaction_threshold:
                    if not await self.compact():
                        break

                if self.max_total_tokens and self.tokens_used >= self.max_total_tokens:
                    logger.info("Agent token budget reached, forcing final response")
                    break

                continue

            if not (result.text or "").strip():
                self.tokens_used += result.total_tokens or 0
                logger.warning(
                    f"Agent loop iteration {iteration} returned empty LLM output; retrying next iteration"
                )
                continue

            step: AgentStepSchema | None = self.parser.parse_output(result.text)
            if step is None:
                fallback_text = result.text or ""
                recovered_step = (
                    self._recover_unstructured_step(fallback_text, prompt)
                    if self.unstructured_recovery_enabled
                    else None
                )
                if recovered_step is not None:
                    trace = await self.run_step(step=recovered_step, chat=result, iteration=iteration)
                    trace.warning = "Recovered from unstructured model output using fallback step parser."
                    self.traces.append(trace)

                    self.context_used += len(trace.tool_output or "")
                    self.tokens_used += trace.total_tokens or 0

                    if self.context_used >= self.max_context_chars:
                        if self.compaction_enabled:
                            if not await self.compact():
                                break
                        else:
                            logger.info("Agent context limit reached, forcing final response")
                            break
                    elif self.compaction_enabled and self.context_used >= self.compaction_threshold:
                        if not await self.compact():
                            break

                    if self.max_total_tokens and self.tokens_used >= self.max_total_tokens:
                        logger.info("Agent token budget reached, forcing final response")
                        break

                    continue

                logger.info(f"Agent loop iteration {iteration} returned unstructured response; stopping")
                self.traces.append(
                    AgentTraceSchema(
                        step=AgentStepSchema(
                            action=AgentAction.FINAL,
                            content=fallback_text or "Empty model response",
                        ),
                        warning="Failed to parse structured action. Returning raw model output.",
                        iteration=iteration,
                        raw_output=fallback_text,
                        total_tokens=result.total_tokens,
                        prompt_tokens=result.prompt_tokens,
                        completion_tokens=result.completion_tokens,
                    )
                )

                return AgentLoopResultSchema(
                    traces=self.traces,
                    final_text=fallback_text,
                    stop_reason="unstructured_response",
                )

            if step.action.is_final:
                recovered_from_final = None
                if self.unstructured_recovery_enabled:
                    recovered_from_final = self._recover_unstructured_step(
                        step.content or "",
                        prompt,
                        allow_diff_intent_fallback=False,
                    )
                if recovered_from_final and recovered_from_final.action == AgentAction.TOOL_CALL:
                    trace = await self.run_step(step=recovered_from_final, chat=result, iteration=iteration)
                    trace.warning = "Recovered TOOL_CALL from malformed FINAL content."
                    self.traces.append(trace)

                    self.context_used += len(trace.tool_output or "")
                    self.tokens_used += trace.total_tokens or 0

                    if self.context_used >= self.max_context_chars:
                        if self.compaction_enabled:
                            if not await self.compact():
                                break
                        else:
                            logger.info("Agent context limit reached, forcing final response")
                            break
                    elif self.compaction_enabled and self.context_used >= self.compaction_threshold:
                        if not await self.compact():
                            break

                    if self.max_total_tokens and self.tokens_used >= self.max_total_tokens:
                        logger.info("Agent token budget reached, forcing final response")
                        break

                    continue

                logger.info(f"Agent loop iteration {iteration} returned FINAL action")
                self.traces.append(
                    AgentTraceSchema(
                        step=step,
                        iteration=iteration,
                        raw_output=result.text,
                        total_tokens=result.total_tokens,
                        prompt_tokens=result.prompt_tokens,
                        completion_tokens=result.completion_tokens,
                    )
                )

                return AgentLoopResultSchema(
                    traces=self.traces,
                    final_text=step.content,
                    stop_reason="final",
                )

            trace = await self.run_step(step=step, chat=result, iteration=iteration)
            self.traces.append(trace)

            self.context_used += len(trace.tool_output or "")
            self.tokens_used += trace.total_tokens or 0
            logger.debug(
                f"Agent loop context usage after iteration {iteration}: "
                f"{self.context_used}/{self.max_context_chars} chars, "
                f"{self.tokens_used}/{self.max_total_tokens or '∞'} tokens"
            )
            if self.context_used >= self.max_context_chars:
                if self.compaction_enabled:
                    if not await self.compact():
                        break
                    # continue the loop with the freed-up budget instead of
                    # cutting the review short.
                else:
                    logger.info("Agent context limit reached, forcing final response")
                    break
            elif self.compaction_enabled and self.context_used >= self.compaction_threshold:
                if not await self.compact():
                    break

            if self.max_total_tokens and self.tokens_used >= self.max_total_tokens:
                logger.info("Agent token budget reached, forcing final response")
                break

        logger.info("Agent loop finished regular iterations without FINAL action; switching to force-final flow")
        return await self.force_final(prompt=prompt, prompt_system=prompt_system)
