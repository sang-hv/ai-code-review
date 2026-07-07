# Agent Review Quota Proposal

> **Status: Phase 1 + tradeoff mitigations + follow-up optimizations implemented.**
>
> The agent-light flow described below ships as three new commands
> (`run-agent`, `run-agent-inline`, `run-agent-summary`) that run a lightweight,
> metadata-only prompt. Existing commands are unchanged. The known trade-offs
> were addressed up front rather than deferred — see **Implemented Behavior**
> below.

## Implemented Behavior

### Commands

```bash
argus-review run-agent-summary   # one agent session -> one summary comment
argus-review run-agent-inline    # one agent session -> inline comments (single call, not per-file)
argus-review run-agent           # ONE agent session -> summary + inline together
```

All three always drive the agent gateway regardless of `agent.enabled`, feeding
it a light prompt that contains only merge-request metadata, the changed-file
list, and a convention *inventory* — never the full diff or full convention text.
The agent pulls in what it needs through read-only tools and returns a final
answer that flows through the existing inline/summary parsers and comment
gateways.

`run-agent` is a **single combined agent session**: the FINAL response is one
JSON object (`{"summary": ..., "comments": [...]}`), so the agent explores the
diff/conventions once and produces both outputs, instead of chaining the two
standalone `run-agent-inline` + `run-agent-summary` sessions (which would
explore twice and roughly double the quota cost of `run-agent`).

### Trade-off mitigations (shipped)

1. **Inline line-number hallucination** — `AgentInlineReviewRunner` validates
   every returned comment against the real diff. Any comment whose `(file, line)`
   does not anchor to a new-side diff line is dropped before posting (the VCS
   would reject it anyway). Validation is lenient when the diff cannot be parsed,
   so nothing is dropped on a parse failure.
2. **Agent history re-transmission cost** — `AGENT__MAX_HISTORY_CHARS`
   (default `24000`) bounds how much tool-output history is re-sent each
   iteration. The most recent steps stay in full; older tool outputs are elided,
   so per-iteration token cost stays bounded instead of growing with every step.
3. **URL/git conventions not searchable on disk** — `ConventionsService.materialize()`
   writes *all* resolved convention docs (local **and** URL/git) into
   `conventions.cache_dir` (`.argus-review/cache/conventions/` by default) and
   returns an inventory (path + line count). URL/git sources become searchable
   with `rg`/`sed`/`cat` exactly like local files. Writes are skipped when the
   source content hash is unchanged.
4. **`sed` (and line-range reads) were blocked by policy** — the default agent
   allow-list now also permits `head`, `tail`, `wc`, and the read-only
   `sed -n ...p` print form (the in-place `-i` edit flag stays blocked). `wc -l`
   lets the agent cheaply check whole-file rules such as "max 300 lines per file".
5. **`run-agent` doubled the exploration cost** — `run-agent` now runs a single
   `AgentReviewRunner` session instead of chaining the standalone inline +
   summary agent runners. One `ask()` call, one diff/convention exploration,
   one FINAL response containing both outputs.
6. **Guardrails tracked chars, not the token quota they were meant to protect** —
   `agent.max_total_tokens` (default `100000`, `0` disables it) bounds real
   prompt+completion token usage across the whole agent loop, forcing FINAL
   once the budget is hit. This complements `max_total_context_chars`
   (tool-output volume) and `max_iterations` (step count) with a check on the
   metric that actually maps to provider-billed quota.

### Configuration

```yaml
agent:
  # Bounds re-sent tool-output history per iteration (tradeoff #2).
  max_history_chars: 24000
  # Hard budget on real prompt+completion tokens across the whole agent loop.
  # Default 100000 is a safety net; lower it for tighter quotas. 0 disables it.
  max_total_tokens: 100000

conventions:
  enabled: true
  # Where local/URL/git convention docs are materialized for the agent to search.
  cache_dir: .argus-review/cache/conventions
  sources:
    - type: local
      path: ./docs/conventions

prompt:
  # Agent-light prompts are overridable like every other mode. The default task
  # instruction and output contract live as resource .md files; point these at
  # your own files to customize them. Dynamic metadata, tool guidance and the
  # convention inventory are always injected around your instruction text.
  agent_light_inline_prompt_files: [ "./prompts/agent_light_inline.md" ]
  agent_light_summary_prompt_files: [ "./prompts/agent_light_summary.md" ]
  system_agent_light_inline_prompt_files: [ "./prompts/agent_light_inline_contract.md" ]
  system_agent_light_summary_prompt_files: [ "./prompts/agent_light_summary_contract.md" ]
```

### CI guidance for low-quota providers

```yaml
# GitLab CI (env var overrides)
CORE__CONCURRENCY: "1"
AGENT__MAX_ITERATIONS: "8"
AGENT__MAX_HISTORY_CHARS: "24000"
AGENT__MAX_COMMAND_OUTPUT_CHARS: "12000"
AGENT__MAX_TOTAL_CONTEXT_CHARS: "50000"
# Tighter than the 100000 default — forces FINAL sooner on very low quotas.
AGENT__MAX_TOTAL_TOKENS: "30000"
# Keep MAX_TOKENS high enough that the final inline JSON is not truncated.
LLM__META__MAX_TOKENS: "4000"
```

```yaml
script:
  - argus-review run-agent          # or run-agent-summary / run-agent-inline
```

> **Note on `MAX_TOKENS`:** the proposal's original `2500` suggestion is fine for
> summary but risky for inline, where the FINAL step must emit a JSON array for
> all files in one response. Too low a limit truncates the JSON and drops
> comments. Prefer a higher value (≈4000+) when using `run-agent-inline`.

> **Note:** the non-agent commands referenced in the "Original Proposal" section
> below (`run`, `run-inline`, `run-context`, `run-summary`, and the `*-reply`
> variants) have since been **removed**. Only the agent commands remain:
> `run-agent`, `run-agent-inline`, `run-agent-summary` (plus `clear-inline`,
> `clear-summary`, `show-config`, `dump-schema`). The agent loop now also does
> history **compaction** and optional file **chunking** for large merge requests.

---

## Original Proposal

## Current Problem

The current GitLab CI review flow can consume quota very quickly, especially with an OpenAI-compatible API key such as `opencode-go` using `deep-seek-v4-pro`.

The main reasons are:

1. `argus-review run` is not a single model call.
   It runs inline review first, then summary review.

2. Inline review currently calls the LLM once per changed file.
   If a merge request changes 20 files, inline review can make roughly 20 LLM calls before the summary call runs.

3. The current diff strategy can preload too much context.
   `FULL_FILE_DIFF` sends the rendered diff content directly into the prompt. This is useful for quality but expensive for large merge requests.

4. Coding conventions are currently appended directly into review prompts.
   If the convention document is very large, for example one file with around 9000 lines, every review call can carry a huge static context block.

5. Existing agent mode does not solve the quota issue.
   The current agent mode still receives the original prompt, which may already include full diff content and full coding conventions. Each agent iteration then sends task context plus agent history again, so enabling agent mode can be more expensive rather than cheaper.

6. The current behavior is different from CLI agents such as opencode or Kiro.
   Those tools typically keep a session-like working context, inspect files and diffs through tools, and only pull relevant context into the model instead of preloading every diff and every convention line up front.

## Goal

Reduce LLM quota usage while keeping review quality acceptable.

The desired behavior is closer to CLI agent review:

- The model starts with lightweight merge request metadata.
- It uses read-only tools to inspect relevant diffs, source files, and coding convention sections.
- It does not receive full coding conventions or full diffs by default.
- It produces summary comments and inline comments through separate commands.

## Proposed Design

Add new agent-light review commands:

```bash
argus-review run-agent-summary
argus-review run-agent-inline
argus-review run-agent
```

Command behavior:

- `run-agent-summary`: runs one agent session and posts one summary comment.
- `run-agent-inline`: runs one agent session and posts inline comments.
- `run-agent`: runs agent inline review and agent summary review, similar to the existing `run` command, but using the new lightweight agent flow.

> **Status update:** the original proposal kept the non-agent commands
> (`run`, `run-inline`, `run-summary`, `run-context`, `*-reply`) for backward
> compatibility. They have since been removed — the agent flow is now the only
> review path.

## Agent-Light Flow

The initial prompt should include only lightweight metadata:

- merge request title
- merge request description
- author/reviewers if available
- base SHA
- head SHA
- changed file list
- review language
- output format contract
- instructions to inspect diff/source/conventions through tools

The initial prompt should not include:

- full rendered diff
- full changed file content
- full coding convention documents

The agent can inspect context using safe read-only commands such as:

```bash
git diff --name-only <base>..<head>
git diff <base>..<head> -- path/to/file.go
rg "keyword" .
cat path/to/file.go
rg -n "keyword" docs/coding-conventions.md
sed -n '1200,1280p' docs/coding-conventions.md
```

The agent should stop reading once it has enough evidence to produce the review.

## Coding Convention Handling

Do not append full coding conventions to agent-light prompts.

Instead, introduce an `Argus Context Cache` for conventions:

1. Scan configured convention sources.
2. Build a lightweight inventory/index.
3. Cache the index under `.argus-review/cache/`.
4. Invalidate the cache when source file hashes change.
5. Give the agent only the inventory and tool instructions.

Example inventory:

```text
Coding conventions available:
- docs/coding-conventions.md, 9000 lines

Use rg/sed/cat to inspect only relevant convention sections before citing a rule.
```

For local convention files, the agent can inspect the files directly.

For URL or git convention sources, a later phase can materialize them into the workspace cache so the agent can search/read them the same way as local files.

## Context Cache

Add a context cache service that stores derived metadata, not full prompt text:

```json
{
  "source_hash": "sha256...",
  "files": [
    {
      "path": "docs/coding-conventions.md",
      "line_count": 9000,
      "sections": [
        {
          "title": "Error handling",
          "start": 120,
          "end": 260,
          "keywords": ["error", "wrap", "context"]
        }
      ]
    }
  ]
}
```

This is not provider-side prompt caching. It reduces quota because ArgusReview sends less text to the model.

Provider-side prompt caching can only be used if the target OpenAI-compatible API supports it. The generic OpenAI-compatible client should not assume that support.

## Output Contracts

`run-agent-summary` should return plain summary text, then post it through the existing summary comment gateway.

`run-agent-inline` should return JSON compatible with the existing inline comment parser, then post it through the existing inline comment gateway.

Example inline final output:

```json
[
  {
    "file": "path/to/file.go",
    "line": 123,
    "message": "Explain the issue and recommendation."
  }
]
```

## Suggested Guardrails

Recommended CI settings for low-quota providers:

```yaml
CORE__CONCURRENCY: "1"
LLM__META__MAX_TOKENS: "2500"
AGENT__MAX_ITERATIONS: "8"
AGENT__MAX_COMMAND_OUTPUT_CHARS: "12000"
AGENT__MAX_TOTAL_CONTEXT_CHARS: "50000"
```

Recommended GitLab CI command:

```yaml
script:
  - argus-review run-agent
```

Or run only one mode:

```yaml
script:
  - argus-review run-agent-summary
```

```yaml
script:
  - argus-review run-agent-inline
```

## Expected Benefits

- Fewer large prompts.
- No repeated full convention injection.
- No per-file LLM call loop for inline review.
- Better behavior on merge requests with many changed files.
- Review flow closer to CLI agents such as opencode and Kiro.
- Existing commands remain available as a fallback.

## Main Trade-Offs

- The agent must choose the right context to inspect.
- Review quality depends on tool-use behavior and prompt discipline.
- Very large merge requests may still require limits or follow-up runs.
- URL/git convention sources need a materialization step to be searchable like local files.

## Recommended Implementation Phases

### Phase 1 — ✅ Implemented

- Added `run-agent-summary`, `run-agent-inline`, and `run-agent`.
- Built lightweight agent prompts without full diff or full conventions.
- Convention inventory + on-disk materialization for local **and** URL/git sources.
- Reused existing comment gateways and parsers.
- Shipped tradeoff mitigations: inline line-number validation, agent history
  trimming (`max_history_chars`), and an expanded read-only command allow-list
  (`head`/`tail`/`sed -n`).

### Phase 2 — optional / future

- Richer `ContextCacheService` with per-section indexes (title/start/end/keywords)
  under `.argus-review/cache/`. The current inventory (path + line count) already
  lets the agent search with `rg`/`sed`; a full section index is an optimization,
  not a prerequisite.
- Add GitLab CI cache guidance for `.argus-review/cache/`.

### Phase 3 — optional / future

- URL/git convention materialization is already done in Phase 1.
- Optionally add provider-specific prompt cache support if the API supports it.

