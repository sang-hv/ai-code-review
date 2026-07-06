# 📘 ArgusReview CLI

The **ArgusReview CLI** provides a simple interface to run reviews, inspect configuration, and integrate with CI/CD
pipelines.

It is built with Typer and fully supports async execution of all review modes.

---

## 🚀 Quick Start

After installing ArgusReview:

````bash
pip install argus-review-code
````

Run any command from your terminal:

```bash
argus-review run
```

Or display help:

```bash
argus-review --help
```

---

## 🧩 Available Commands

| Command                          | Description                                                               | Typical Usage                    |
|----------------------------------|---------------------------------------------------------------------------|----------------------------------|
| `argus-review run`               | Runs the full review pipeline (inline + summary).                         | `argus-review run`               |
| `argus-review run-inline`        | Runs only **inline review** (line-by-line comments).                      | `argus-review run-inline`        |
| `argus-review run-context`       | Runs **context review** across multiple files for architectural feedback. | `argus-review run-context`       |
| `argus-review run-summary`       | Runs **summary review** that posts a single summarizing comment.          | `argus-review run-summary`       |
| `argus-review run-inline-reply`  | Generates **AI replies** to existing inline comment threads.              | `argus-review run-inline-reply`  |
| `argus-review run-summary-reply` | Generates **AI replies** to existing summary review threads.              | `argus-review run-summary-reply` |
| `argus-review run-agent`         | Low-quota: **one agent session** explores the repo via read-only tools and returns summary + inline comments together. | `argus-review run-agent` |
| `argus-review run-agent-inline`  | Low-quota: one agent session, **inline comments only**.                   | `argus-review run-agent-inline`  |
| `argus-review run-agent-summary` | Low-quota: one agent session, **summary only**.                           | `argus-review run-agent-summary` |
| `argus-review clear-inline`      | Removes all **AI-generated inline comments** from the review.             | `argus-review clear-inline`      |
| `argus-review clear-summary`     | Removes all **AI-generated summary comments** from the review.            | `argus-review clear-summary`     |
| `argus-review show-config`       | Prints the currently resolved configuration (merged from YAML/JSON/ENV).  | `argus-review show-config`       |

---

## 💡 Examples

### 🧠 Full Review

Runs the complete review cycle — inline + summary:

```bash
argus-review run
```

### 🧩 Inline Review Only

For quick line-by-line comments:

```bash
argus-review run-inline
```

Typical in CI/CD pipelines for fast feedback on changed files.

### 🧠 Context Review

For broader architectural or cross-file feedback:

```bash
argus-review run-context
```

The model receives the entire diff set and can highlight inconsistencies between modules.

### 🗒️ Summary Review

Posts one concise summary comment under the merge/pull request:

```bash
argus-review run-summary
```

Useful when inline feedback isn't required but a global analysis is.

### 🪶 Low-quota Agent Review

For projects on a tight LLM quota (or a low-throughput OpenAI-compatible provider),
`run-agent` runs a **single agent session**: the model gets only merge-request
metadata and a coding-convention inventory, then explores the diff/source itself
via read-only shell tools (`ls`, `cat`, `rg`, `git diff`, `sed -n`, ...) before
returning both the summary and inline comments in one response:

```bash
argus-review run-agent
```

To get just one half of that (still low-quota, still one agent session):

```bash
argus-review run-agent-inline
argus-review run-agent-summary
```

These three always drive the agent loop regardless of the `agent.enabled` config
flag — that flag only affects `run`/`run-inline`/`run-summary`/`run-context`.
See [docs/agent-review-quota-proposal.md](../agent-review-quota-proposal.md) for
the full design and tuning knobs (`agent.max_iterations`, `agent.max_history_chars`,
`agent.max_total_tokens`, ...).

### 💬 Reply Modes

Generate AI-based follow-ups to existing discussion threads:

```bash
argus-review run-inline-reply
argus-review run-summary-reply
```

Replies only to comments originally created by ArgusReview.

### 🧽 Clear Inline Comments

Removes all AI-generated inline comments:

```bash
argus-review clear-inline
```

> ⚠️ **Warning**
>
> This command **permanently deletes** all inline review comments created by ArgusReview in the current merge / pull
> request.
>
> - The operation cannot be undone
> - Only comments marked with the ArgusReview inline tag are affected
> - Developer and user comments are not touched
>
> It is recommended to run this command **manually** and only when you are sure that existing AI comments are no longer
> needed.

### 🧽 Clear Summary Comments

Removes all AI-generated summary comments:

```bash
argus-review clear-summary
```

> ⚠️ **Warning**
>
> This command **permanently deletes** all summary review comments created by ArgusReview.
>
> - The operation cannot be undone
> - Only ArgusReview summary comments are removed
> - No new comments are created as part of this command
>
> Use with caution, especially in shared or long-running pull requests.

### ⚙️ Inspect Configuration

Display the resolved configuration used by the CLI:

```bash
argus-review show-config
```

Output (formatted JSON):

```json
{
  "llm": {
    "provider": "OPENAI",
    "meta": {
      "model": "gpt-4o-mini",
      "temperature": 0.3
    }
  },
  "vcs": {
    "provider": "GITLAB",
    "pipeline": {
      "project_id": 1
    }
  }
}
```

---

## ⚙️ Tips

- Each command runs **asynchronously** and handles exceptions internally.
- All reviews report **token usage** and **LLM cost** after completion.
- The CLI is designed for **non-interactive** use — perfect for CI/CD jobs.
