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
argus-review run-agent
```

Or display help:

```bash
argus-review --help
```

---

## 🧩 Available Commands

| Command                          | Description                                                               | Typical Usage                    |
|----------------------------------|---------------------------------------------------------------------------|----------------------------------|
| `argus-review run-agent`         | **One agent session** explores the repo via read-only tools and returns summary + inline comments together. | `argus-review run-agent` |
| `argus-review run-agent-inline`  | One agent session, **inline comments only**.                              | `argus-review run-agent-inline`  |
| `argus-review run-agent-summary` | One agent session, **summary only**.                                      | `argus-review run-agent-summary` |
| `argus-review clear-inline`      | Removes all **AI-generated inline comments** from the review.             | `argus-review clear-inline`      |
| `argus-review clear-summary`     | Removes all **AI-generated summary comments** from the review.            | `argus-review clear-summary`     |
| `argus-review show-config`       | Prints the currently resolved configuration (merged from YAML/JSON/ENV).  | `argus-review show-config`       |
| `argus-review dump-schema`       | Dumps the configuration JSON Schema (source of truth for all options).    | `argus-review dump-schema`       |

---

## 💡 Examples

### 🪶 Agent Review

`run-agent` runs a **single agent session**: the model gets only merge-request
metadata and a coding-convention inventory, then explores the diff/source itself
via read-only shell tools (`ls`, `cat`, `rg`, `git diff`, `sed -n`, ...) before
returning both the summary and inline comments in one response:

```bash
argus-review run-agent
```

To get just one half of that (still one agent session):

```bash
argus-review run-agent-inline
argus-review run-agent-summary
```

The agent loop supports **compaction** (summarizes its history instead of
cutting off when the context budget is near full) and optional **file chunking**
(`agent.max_files_per_chunk` splits large merge requests into batches). Tuning
knobs live under the `agent:` config block — `agent.max_iterations`,
`agent.max_total_context_chars`, `agent.max_command_output_chars`,
`agent.max_history_chars`, `agent.max_total_tokens`,
`agent.compaction_enabled`, `agent.compaction_threshold_ratio`,
`agent.max_files_per_chunk`.

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
