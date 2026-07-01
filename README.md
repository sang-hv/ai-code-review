# ArgusReview

<p align="center">
  <img src="./docs/assets/logo.png" alt="ArgusReview logo" width="220" />
</p>

AI-powered code review tool.

[![CI](https://github.com/deha-project/argus-review/actions/workflows/workflow-test.yml/badge.svg)](https://github.com/deha-project/argus-review/actions/workflows/workflow-test.yml)
[![codecov](https://codecov.io/gh/deha-project/argus-review/branch/main/graph/badge.svg)](https://codecov.io/gh/deha-project/argus-review)
[![PyPI version](https://img.shields.io/pypi/v/argus-review.svg)](https://pypi.org/project/argus-review/)
[![License](https://img.shields.io/github/license/deha-project/argus-review)](./LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/deha-project/argus-review?style=social)](https://github.com/deha-project/argus-review/stargazers)

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
  **OpenRouter**, or **Azure OpenAI** and switch anytime.
- **VCS integration** — works out of the box with **GitLab**, **GitHub**, **Bitbucket Cloud**, **Bitbucket Server**,
  **Azure DevOps**, and **Gitea**.
- **Customizable prompts** — adapt inline, context, and summary reviews to match your team's coding guidelines.
- **Agent mode** — iterative ReAct-style loop where the model can **explore the repository** with shell commands
  (`ls`, `cat`, `rg`, `git`) before producing a final review, giving it deeper context than a single-shot call.
- **Reply modes** — AI can now **participate in existing review threads**, adding follow-up replies in both inline and
  summary discussions.
- **Flexible configuration** — supports `YAML`, `JSON`, and `ENV`, with seamless overrides in CI/CD pipelines.
- **ArgusReview runs fully client-side** — it never proxies or inspects your requests.

ArgusReview runs automatically in your CI/CD pipeline and posts both **inline comments**, **summary reviews**, and now
**AI-generated replies** directly inside your merge requests. With **agent mode** enabled, the model can autonomously
explore the codebase before reviewing, resulting in more accurate and context-aware feedback. This makes reviews faster,
more conversational, and still fully under human control.

---

## 🧪 Live Preview

Curious how **ArgusReview** works in practice? Here are real Pull Requests reviewed entirely by the tool — one per
mode:

| Mode             | Description                                                                                                                                  |
|------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| 🧩 Inline        | Adds **line-by-line comments** directly in the diff. Focuses on specific code changes.                                                       |
| 🧠 Context       | Performs a **broader analysis across multiple files**, detecting cross-file issues and inconsistencies.                                      |
| 📄 Summary       | Posts a **concise high-level summary** with key highlights, strengths, and major issues.                                                     |
| 💬 Inline Reply  | Generates a **context-aware reply** to an existing inline comment thread. Can clarify decisions, propose fixes, or provide code suggestions. |
| 💬 Summary Reply | Continues the **summary-level review discussion**, responding to reviewer comments with clarifications, rationale, or actionable next steps. |

👉 Each review was generated automatically via GitHub Actions using the corresponding mode:

```bash
argus-review run-inline
argus-review run-summary
argus-review run-context
argus-review run-inline-reply
argus-review run-summary-reply
```

---

## 🚀 Quick Start

Install via **pip**:

```bash
pip install argus-review
```

📦 Available on [PyPI](https://pypi.org/project/argus-review/)

---

Or run directly via Docker:

```bash
docker run --rm -v $(pwd):/app deha/argus-review:latest run-summary
```

🐳 Pull from [DockerHub](https://hub.docker.com/r/deha/argus-review)

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

> **Note:** Running `argus-review run` executes the full review (inline + summary).
> To run only one mode, use the dedicated subcommands:
> - argus-review run-inline
> - argus-review run-context
> - argus-review run-summary
> - argus-review run-inline-reply
> - argus-review run-summary-reply

---

ArgusReview can be configured via `.ai-review.yaml`, `.ai-review.json`, or `.env`. See [./docs/configs](./docs/configs)
for complete, ready-to-use examples.

Key things you can customize:

- **LLM provider** — OpenAI, Gemini, Claude, Ollama, Bedrock, OpenRouter, or Azure OpenAI
- **Model settings** — model name, temperature, max tokens
- **VCS integration** — works out of the box with **GitLab**, **GitHub**, **Bitbucket Cloud**, **Bitbucket Server**,
  **Azure DevOps**, and **Gitea**
- **Agent mode** — enable iterative repository exploration before review
- **Review policy** — which files to include/exclude, review modes
- **Prompts** — inline/context/summary/agent prompt templates

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
        default: run
        options:
          - run
          - run-inline
          - run-context
          - run-summary
          - run-inline-reply
          - run-summary-reply
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

      - uses: deha-project/argus-review@v0.68.0
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
  image: deha/argus-review:latest
  rules:
    - if: '$CI_MERGE_REQUEST_IID'
  script:
    - argus-review run
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

- 📦 [PyPI](https://pypi.org/project/argus-review/)
- 🐳 [DockerHub](https://hub.docker.com/r/deha/argus-review)
