# ArgusReview

<p align="center">
  <img src="./docs/assets/logo.png" alt="ArgusReview logo" width="220" />
</p>

AI-powered code review tool.

> This is a personal fork ([sang-hv/argus-code-review](https://github.com/sang-hv/argus-code-review)) of ArgusReview
> (originally [ai-review by Nikita Filonov](https://github.com/Nikita-Filonov/ai-review), rebranded by
> [deha-project](https://github.com/deha-project/argus-review)). See [NOTICE](./NOTICE) for full attribution.

[![CI](https://github.com/sang-hv/argus-code-review/actions/workflows/workflow-test.yml/badge.svg)](https://github.com/sang-hv/argus-code-review/actions/workflows/workflow-test.yml)
[![PyPI version](https://img.shields.io/pypi/v/argus-review-code.svg)](https://pypi.org/project/argus-review-code/)
[![License](https://img.shields.io/github/license/sang-hv/argus-code-review)](./LICENSE)

---

## 📑 Table of Contents

- ✨ [About](#-about)
- 🧪 [Live Preview](#-live-preview)
- 🚀 [Quick Start](#-quick-start)
- ⚙️ [️CI/CD Integration](#-cicd-integration)
    - 🚀 [GitHub Actions](#-github-actions)
    - 🚀 [GitLab CI/CD](#-gitlab-cicd)
- 📘 [Documentation](#-documentation)
- ⚠️ [Privacy & Responsibility Notice](#-privacy--responsibility-notice)

---

## ✨ About

**ArgusReview** is a developer tool that brings **AI-powered code review** directly into your workflow. It helps teams
improve code quality, enforce consistency, and speed up the review process.

✨ Key features:

- **Multiple LLM providers** — choose between **OpenAI**, **Claude**, **Gemini**, **Ollama**, **Bedrock**,
  **OpenRouter**, or **Azure OpenAI** and switch anytime. Plus a generic **OpenAI-compatible** provider and a
  **9Router** preset, so any OpenAI-style gateway (LMRouter, vLLM, LocalAI, LiteLLM, ...) works by just setting a base URL.
- **Project coding conventions** — feed your team's standards (Markdown) into every review from a **local folder**, a
  **raw URL**, or a **git repo** (public or private). The AI reviews against *your* rules, not just generic defaults.
- **VCS integration** — works out of the box with **GitLab**, **GitHub**, **Bitbucket Cloud**, **Bitbucket Server**,
  **Azure DevOps**, and **Gitea**.
- **Customizable prompts** — adapt inline and summary reviews to match your team's coding guidelines.
- **Agent mode** — iterative ReAct-style loop where the model can **explore the repository** with shell commands
  (`ls`, `cat`, `rg`, `git`) before producing a final review, giving it deeper context than a single-shot call.
- **Flexible configuration** — supports `YAML`, `JSON`, and `ENV`, with seamless overrides in CI/CD pipelines.
- **ArgusReview runs fully client-side** — it never proxies or inspects your requests.

ArgusReview runs automatically in your CI/CD pipeline and posts both **inline comments** and **summary reviews**
directly inside your merge requests. The agent autonomously explores the codebase before reviewing, resulting in
more accurate and context-aware feedback, while keeping quota usage low. This makes reviews faster and still fully
under human control.

---

## 🧪 Live Preview

Curious how **ArgusReview** works in practice? Here are real Pull Requests reviewed entirely by the tool — one per
mode:

| Mode                | Description                                                                                                                             |
|---------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| 🤖 Agent (combined) | Single agent session that explores the repo and produces both inline comments and a summary. Lowest quota cost.                          |
| 🧩 Agent Inline     | Agent session focused on **line-by-line comments** directly in the diff.                                                                  |
| 📄 Agent Summary    | Agent session that posts a **concise high-level summary** with key highlights, strengths, and major issues.                              |

👉 Each review was generated automatically via GitHub Actions using the corresponding mode:

```bash
argus-review run-agent
argus-review run-agent-inline
argus-review run-agent-summary
```

---

## 🚀 Quick Start

Install via **pip**:

```bash
pip install argus-review-code
```

📦 Package name on PyPI: **`argus-review-code`** (the CLI command is still `argus-review`)

Or install from source:

```bash
git clone https://github.com/sang-hv/argus-code-review.git
cd argus-code-review
pip install .
```

Or build the Docker image locally:

```bash
docker run --rm -v $(pwd):/app supersentaj/argus-review:latest run-agent
```

🐳 Pull from [Docker Hub](https://hub.docker.com/r/supersentaj/argus-review)

👉 Before running, create a basic configuration file [.ai-review.yaml](./docs/configs/.ai-review.yaml) in the root of
your project:

```yaml
llm:
  provider: OPENAI

  meta:
    model: gpt-4o-mini
    max_tokens: 1200
    temperature: 0.3

  http_client:
    timeout: 120
    api_url: https://api.openai.com/v1
    api_token: ${OPENAI_API_KEY}

vcs:
  provider: GITLAB

  pipeline:
    project_id: "1"
    merge_request_id: "100"

  http_client:
    timeout: 120
    api_url: https://gitlab.com
    api_token: ${GITLAB_API_TOKEN}
```

👉 This will:

- Run ArgusReview against your codebase.
- Generate inline and/or summary comments (depending on the selected mode).
- Use your chosen LLM provider (OpenAI GPT-4o-mini in this example).

> **Note:** `argus-review run-agent` runs a single low-quota agent session
> (metadata + read-only repo exploration) that produces both the summary and
> inline comments, instead of one LLM call per file. To run only one part of
> the review, use the dedicated subcommands:
> - argus-review run-agent-inline
> - argus-review run-agent-summary
>
> Utility commands are also available: `clear-inline`, `clear-summary` (remove
> AI-generated comments), `show-config` (print the resolved configuration),
> and `dump-schema` (dump the config JSON Schema). See
> [docs/agent-review-quota-proposal.md](./docs/agent-review-quota-proposal.md).

---

ArgusReview can be configured via `.ai-review.yaml`, `.ai-review.json`, or `.env`. See [./docs/configs](./docs/configs)
for complete, ready-to-use examples.

Key things you can customize:

- **LLM provider** — OpenAI, Gemini, Claude, Ollama, Bedrock, OpenRouter, Azure OpenAI, any **OpenAI-compatible**
  endpoint, or **9Router**
- **Model settings** — model name, temperature, max tokens
- **VCS integration** — works out of the box with **GitLab**, **GitHub**, **Bitbucket Cloud**, **Bitbucket Server**,
  **Azure DevOps**, and **Gitea**
- **Agent mode** — enable iterative repository exploration before review
- **Coding conventions** — load your team's `.md` standards from a local folder, a URL, or a git repo
- **Review language** — have the AI write comments/summaries/replies in any language (English, Vietnamese, ...)
- **Review policy** — which files to include/exclude, review modes
- **Prompts** — inline/context/summary/agent prompt templates

---

### 🔌 OpenAI-compatible providers & 9Router

Any gateway that speaks the OpenAI Chat Completions API works with the `OPENAI_COMPATIBLE` provider — you only set a
base URL and a model:

```yaml
llm:
  provider: OPENAI_COMPATIBLE
  meta:
    model: meta-llama/llama-3.1-70b-instruct
  http_client:
    api_url: https://my-router.example.com/v1
    api_token: ${LLM_API_TOKEN}   # optional — omit for token-less local gateways
```

For the [9Router](https://9router.com) local proxy, use the `9ROUTER` preset. `api_url` defaults to
`http://localhost:20128/v1`, so config stays minimal:

```yaml
llm:
  provider: 9ROUTER
  meta:
    model: gpt-4o-mini
```

---

### 📐 Project coding conventions

Every team has its own standards. Point ArgusReview at your convention docs and they get injected into each review
prompt automatically. Sources can be a local file/folder, a raw URL, or a git repo — private ones supported via token:

```yaml
conventions:
  enabled: true
  sources:
    # Local file or folder of .md docs
    - type: local
      path: ./docs/conventions

    # Raw Markdown from a URL (token optional, for private URLs)
    - type: url
      url: https://raw.githubusercontent.com/my-org/standards/main/PYTHON.md
      token: ${CONVENTIONS_URL_TOKEN}

    # .md docs pulled from a git repo (token optional, for private repos)
    - type: git
      repo: https://github.com/my-org/standards.git
      ref: main
      path: python
      token: ${GIT_TOKEN}

  # Optional: enable/disable per review mode (all on by default)
  modes:
    inline: true
    context: true
    summary: true
    inline_reply: true
    summary_reply: true
```

Convention loading is fail-soft: an unreachable source is logged and skipped, so a review is never blocked.

---

### 🌐 Review language

Have the AI write its review (inline comments, summaries, and replies) in the language your team prefers. It's a
single free-form field — use any language name the model understands. Code identifiers, file paths, and code snippets
are always kept unchanged.

```yaml
review:
  language: Vietnamese   # or English (default), Tiếng Việt, 日本語, Français, ...
```

👉 Minimal configuration is enough to get started. Use the full reference configs if you want fine-grained control (
timeouts, artifacts, logging, etc.).

---

## ⚙️ CI/CD Integration

ArgusReview works out-of-the-box with major CI providers.
Use these snippets to run ArgusReview automatically on Pull/Merge Requests.  
Each integration uses environment variables for LLM and VCS configuration.

> For full configuration details (timeouts, artifacts, logging, prompt overrides), see [./docs/configs](./docs/configs).

### 🚀 GitHub Actions

Add a workflow like this (manual trigger from **Actions** tab):

```yaml
name: ArgusReview

on:
  workflow_dispatch:
    inputs:
      review-command:
        type: choice
        default: run-agent
        options:
          - run-agent
          - run-agent-inline
          - run-agent-summary
          - clear-inline
          - clear-summary
      pull-request-number:
        type: string
        required: true
jobs:
  argus-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - uses: sang-hv/argus-code-review@main
        with:
          review-command: ${{ inputs.review-command }}
        env:
          # --- LLM configuration ---
          LLM__PROVIDER: "OPENAI"
          LLM__META__MODEL: "gpt-4o-mini"
          LLM__META__MAX_TOKENS: "15000"
          LLM__META__TEMPERATURE: "0.3"
          LLM__HTTP_CLIENT__API_URL: "https://api.openai.com/v1"
          LLM__HTTP_CLIENT__API_TOKEN: ${{ secrets.OPENAI_API_KEY }}

          # --- GitHub integration ---
          VCS__PROVIDER: "GITHUB"
          VCS__PIPELINE__OWNER: ${{ github.repository_owner }}
          VCS__PIPELINE__REPO: ${{ github.event.repository.name }}
          VCS__PIPELINE__PULL_NUMBER: ${{ inputs.pull-request-number }}
          VCS__HTTP_CLIENT__API_URL: "https://api.github.com"
          VCS__HTTP_CLIENT__API_TOKEN: ${{ secrets.GITHUB_TOKEN }}

```

🔗 Full example: [./docs/ci/github.yaml](./docs/ci/github.yaml)

### 🚀 GitLab CI/CD

For GitLab users:

```yaml
argus-review:
  when: manual
  stage: review
  image: supersentaj/argus-review:latest
  rules:
    - if: '$CI_MERGE_REQUEST_IID'
  script:
    - argus-review run-agent
  variables:
    # --- LLM configuration ---
    LLM__PROVIDER: "OPENAI"
    LLM__META__MODEL: "gpt-4o-mini"
    LLM__META__MAX_TOKENS: "15000"
    LLM__META__TEMPERATURE: "0.3"
    LLM__HTTP_CLIENT__API_URL: "https://api.openai.com/v1"
    LLM__HTTP_CLIENT__API_TOKEN: "$OPENAI_API_KEY"

    # --- GitLab integration ---
    VCS__PROVIDER: "GITLAB"
    VCS__PIPELINE__PROJECT_ID: "$CI_PROJECT_ID"
    VCS__PIPELINE__MERGE_REQUEST_ID: "$CI_MERGE_REQUEST_IID"
    VCS__HTTP_CLIENT__API_URL: "$CI_SERVER_URL"
    VCS__HTTP_CLIENT__API_TOKEN: "$CI_JOB_TOKEN"
  allow_failure: true  # Optional: don't block pipeline if ArgusReview fails

```

🔗 Full example: [./docs/ci/gitlab.yaml](./docs/ci/gitlab.yaml)

---

## 📘 Documentation

See these folders for reference templates and full configuration options:

- [./docs/ci](./docs/ci) — CI/CD integration templates (GitHub Actions, GitLab CI, Bitbucket Pipelines, Jenkins)
- [./docs/cli](./docs/cli) — CLI command reference and usage examples
- [./docs/hooks](./docs/hooks) — hook reference and lifecycle events
- [./docs/configs](./docs/configs) — full configuration examples (`.yaml`, `.json`, `.env`)
- [./docs/prompts](./docs/prompts) — prompt templates for Python/Go (light & strict modes)
- [./docs/troubleshooting.md](./docs/troubleshooting) — common environment and Git-related issues

---

## ⚠️ Privacy & Responsibility Notice

ArgusReview does **not store**, **log**, or **transmit** your source code to any external service other than the **LLM
provider** explicitly configured in your `.ai-review.yaml`.

All data is sent **directly** from your CI/CD environment to the selected LLM API endpoint (e.g. OpenAI, Gemini,
Claude, OpenRouter). No intermediary servers or storage layers are involved.

If you use **Ollama**, requests are sent to your **local or self-hosted Ollama runtime**  
(by default `http://localhost:11434`). This allows you to run reviews completely **offline**, keeping all data strictly
inside your infrastructure.

> ⚠️ Please ensure you use proper API tokens and avoid exposing corporate or personal secrets.
> If you accidentally leak private code or credentials due to incorrect configuration (e.g., using a personal key
> instead of an enterprise one), it is **your responsibility** — the tool does not retain or share any data by itself.

---

🧠 **ArgusReview** — open-source AI-powered code reviewer

- 📂 [Source (this fork)](https://github.com/sang-hv/argus-code-review)
- 📦 [PyPI](https://pypi.org/project/argus-review-code/)
- 📜 [NOTICE — attribution & fork history](./NOTICE)
# test change for review
