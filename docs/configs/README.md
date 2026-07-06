# 📘 ArgusReview Configuration

ArgusReview supports multiple configuration formats and sources. All of them are automatically detected at runtime.

---

## 📂 Supported formats

- **YAML** (recommended): `.ai-review.yaml`
- **JSON**: `.ai-review.json`
- **ENV**: `.env`

👉 You can combine formats: values are loaded in order of priority.

---

## 📑 Load priority

Highest priority first — a value set by an earlier source overrides the same field from a later one:

1. **Initialization arguments** (if used as a library)
2. **Environment variables** (`LLM__PROVIDER=OPENAI`, etc.) — this includes CI/CD secrets/variables
3. **ENV file** (`.env` or path from `AI_REVIEW_CONFIG_FILE_ENV`)
4. **YAML** (`.ai-review.yaml` or path from `AI_REVIEW_CONFIG_FILE_YAML`) — acts as the baseline/default
5. **JSON** (`.ai-review.json` or path from `AI_REVIEW_CONFIG_FILE_JSON`)

👉 In practice: commit a YAML file with sane defaults, then override specific fields (provider, model, tokens) via
environment variables or CI/CD secrets — no need to edit the committed file per environment.

---

## 🔑 Secrets & tokens (important)

Values in a YAML/JSON config file are used **literally** — `${...}` is **not**
expanded. So do **not** put real secrets there, and don't rely on
`api_token: ${OPENAI_API_KEY}` in the file resolving to your key (it won't).

Instead, pass secrets as **environment variables**, which override the file:

```bash
LLM__HTTP_CLIENT__API_TOKEN=sk-...      # your LLM key (from a CI secret)
VCS__HTTP_CLIENT__API_TOKEN=...         # VCS token (often a CI-provided token)
```

Recommended split:
- **Config file** (committed): provider, model, api_url, review, conventions, agent — nothing secret.
- **Env vars / CI secrets**: all tokens/keys, and the dynamic pipeline context
  (`VCS__PIPELINE__*`) which your CI provides via predefined variables.

The [config builder](../../web) generates both halves for you: a clean
`.ai-review.yaml` plus the matching CI job and the list of secrets to create.

---

## ⚙️ Override file paths

You can override default config locations using environment variables:

- `AI_REVIEW_CONFIG_FILE_YAML` — path to `.yaml` config
- `AI_REVIEW_CONFIG_FILE_JSON` — path to `.json` config
- `AI_REVIEW_CONFIG_FILE_ENV` — path to `.env`

By default, configs are loaded from the **project root**.

---

## 🤖 LLM providers (`LLM__PROVIDER`)

Set `llm.provider` (YAML) or `LLM__PROVIDER` (ENV) to one of the following. Each provider has its own required
`llm.http_client` fields and optional `llm.meta` fields.

| `LLM__PROVIDER`      | Description                                                | Required `http_client` fields                              | Notable `meta` fields                          |
|----------------------|-------------------------------------------------------------|--------------------------------------------------------------|-------------------------------------------------|
| `OPENAI`             | OpenAI API                                                   | `api_url`, `api_token`                                       | `model` (default `gpt-4o-mini`)                 |
| `GEMINI`             | Google Gemini                                                | `api_url`, `api_token`                                       | `model` (default `gemini-2.0-pro`)              |
| `CLAUDE`             | Anthropic Claude                                              | `api_url`, `api_token`                                       | `model` (default `claude-3-sonnet`); `http_client.api_version` (default `2023-06-01`) |
| `OLLAMA`             | Local/self-hosted Ollama runtime                              | `api_url` (no token required)                                 | `model` (default `llama2`); `top_p`, `num_ctx`, `repeat_penalty`, `stop`, `seed` |
| `BEDROCK`            | AWS Bedrock                                                   | `api_url`, `region`, `access_key`, `secret_key` (`session_token` optional) | `model` (default `anthropic.claude-3-sonnet-20240229-v1:0`) |
| `OPENROUTER`         | OpenRouter                                                    | `api_url`, `api_token`                                        | `model` (default `openai/gpt-4o-mini`); `title`, `referer` (optional, for analytics) |
| `AZURE_OPENAI`       | Azure OpenAI                                                  | `api_url`, `api_token`                                        | `model` = **deployment name**, not an OpenAI model id; `http_client.api_version` (default `2024-06-01`) |
| `OPENAI_COMPATIBLE`  | Any OpenAI Chat Completions compatible gateway (LMRouter, vLLM, LocalAI, LiteLLM, ...) | `api_url` (`api_token` optional)   | `model` — whatever your gateway exposes         |
| `9ROUTER`            | [9Router](https://9router.com) local proxy                    | none — `api_url` defaults to `http://localhost:20128/v1` (`api_token` optional) | `model` — whatever your 9Router combo routes to |

Common `http_client` fields available on every provider: `verify` (SSL, default `true`), `timeout` (seconds, default
`120`), `proxy_url` (optional).

---

## 🗂️ VCS providers (`VCS__PROVIDER`)

Set `vcs.provider` (YAML) or `VCS__PROVIDER` (ENV) to one of the following. Each provider has its own required
`vcs.pipeline` fields (identifying which PR/MR to review) and `vcs.http_client` fields.

| `VCS__PROVIDER`     | Description       | Required `pipeline` fields                                                    | Required `http_client` fields                                  |
|---------------------|-------------------|--------------------------------------------------------------------------------|-------------------------------------------------------------------|
| `GITHUB`            | GitHub            | `owner`, `repo`, `pull_number`                                                 | `api_url` (`https://api.github.com`), `api_token`                 |
| `GITLAB`            | GitLab            | `project_id`, `merge_request_id`                                              | `api_url` (GitLab server URL), `api_token`                        |
| `GITEA`             | Gitea             | `owner`, `repo`, `pull_number`                                                 | `api_url`, `api_token`                                             |
| `AZURE_DEVOPS`      | Azure DevOps      | `organization`, `project`, `repository_id`, `pull_request_id`, `iteration_id` | `api_url`, `api_token`; optional `api_version` (default `7.0`), `api_token_type` (`OAUTH2` default or `PAT`) |
| `BITBUCKET_CLOUD`   | Bitbucket Cloud   | `workspace`, `repo_slug`, `pull_request_id`                                    | `api_url` (`https://api.bitbucket.org/2.0`), `api_token`           |
| `BITBUCKET_SERVER`  | Bitbucket Server  | `project_key`, `repo_slug`, `pull_request_id`                                  | `api_url`, `api_token`                                             |

Common `http_client` fields available on every provider: `verify`, `timeout`, `proxy_url` (all optional). Pagination
is shared across all providers via `vcs.pagination.per_page` (default `100`) and `vcs.pagination.max_pages` (default `5`).

---

## 🤖 Agent mode (`agent.*`)

Two different things use the agent loop:

- `agent.enabled: true` turns `run` / `run-inline` / `run-summary` / `run-context`
  into a ReAct loop (the model may call read-only shell tools before answering).
- `run-agent` / `run-agent-inline` / `run-agent-summary` **always** run the agent
  loop with a lightweight, metadata-only prompt, regardless of `agent.enabled`.
  This is the low-quota flow — see
  [docs/agent-review-quota-proposal.md](../agent-review-quota-proposal.md).

| Field                        | Default | Meaning                                                                                   |
|-------------------------------|---------|---------------------------------------------------------------------------------------------|
| `enabled`                     | `false` | Turns agent mode on for `run`/`run-inline`/`run-summary`/`run-context`.                    |
| `max_iterations`               | `25`    | Hard cap on ReAct steps (tool call + LLM response) before forcing a final answer.          |
| `command_timeout`              | `10`    | Max seconds a single shell command may run before being killed.                            |
| `max_total_context_chars`       | `40000` | Running total of tool-output characters per session; once exceeded, forces a final answer. |
| `max_command_output_chars`      | `40000` | Truncates a single command's output before it's added to context.                          |
| `max_history_chars`            | `24000` | Caps re-sent tool-output history per step (older steps get elided) to bound token cost.    |
| `max_total_tokens`             | `100000` | Hard budget on real prompt+completion tokens across the whole loop. This is the most direct quota guardrail — the char-based limits above only approximate it. `0` disables the check (useful if your provider doesn't report usage). |
| `allow_commands`               | see code | Regex allow-list of shell commands the agent may run (`ls`, `cat`, `rg`, `grep`, `head`, `tail`, `wc`, `sed -n ...p`, `git status/show/diff/log/rev-parse/ls-files`). Read-only by design. |

---

## 📐 Coding conventions (`conventions.*`)

Point `conventions.sources` at local `.md` docs, a raw URL, or a git repo. They
get combined into a single section appended to prompts for the enabled modes
(`conventions.modes.*`, all `true` by default: `inline`, `context`, `summary`,
`inline_reply`, `summary_reply`, `combined`).

For the agent-light flow (`run-agent*`), conventions are **not** appended in
full — they are materialized to disk under `conventions.cache_dir`
(default `.argus-review/cache/conventions`) and the agent only receives a
listing (path + line count), inspecting relevant sections itself with
`rg`/`sed -n`/`cat`. This keeps large convention docs (e.g. thousands of lines)
from being sent on every call.

---

## 📘 Examples

- [.ai-review.yaml](./.ai-review.yaml) — main YAML config with comments
- [.ai-review.json](./.ai-review.json) — JSON config example
- [.env.example](./.env.example) — ENV config example

---

## 🔍 Tips

- Use **YAML** for most projects — it’s human-friendly and supports comments.
- **JSON** is convenient for automation (e.g., CI/CD pipelines).
- **ENV** is useful for local development and quick overrides.
