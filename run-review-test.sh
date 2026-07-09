#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/Users/hoangsang/Downloads/argus-code-review"
AI_REVIEW="$REPO_DIR/.venv/bin/argus-review"

# Repo đích của MR cần review — agent sẽ chạy git/rg/cat trong thư mục này.
# PHẢI là local clone của đúng project (VCS__PIPELINE__PROJECT_ID).
TARGET_REPO_DIR="${TARGET_REPO_DIR:-/Users/hoangsang/deha-project/bsn/sale-fe}"

# ---------------------------------------------------------------------------
# 1. Build/refresh the local package into .venv (editable install)
# ---------------------------------------------------------------------------
if [ ! -x "$REPO_DIR/.venv/bin/python" ]; then
  echo "Creating venv at $REPO_DIR/.venv ..."
  /opt/homebrew/bin/python3.12 -m venv "$REPO_DIR/.venv"
fi

echo "Installing/updating argus-review-code (editable) ..."
"$REPO_DIR/.venv/bin/pip" install -e "$REPO_DIR" -q

export CONVENTIONS_PATH="${CONVENTIONS_PATH:-/Users/hoangsang/deha-project/bsn/sale-fe/AGENTS.md}"
export CONVENTIONS__CACHE_DIR="${CONVENTIONS__CACHE_DIR:-.argus-review/cache/conventions}"
export GITLAB_TOKEN="${GITLAB_TOKEN:-}"
export OPENCODE_TOKEN="${OPENCODE_TOKEN:-}"

# ---------------------------------------------------------------------------
# 2. Runtime config
# ---------------------------------------------------------------------------
export REVIEW__DRY_RUN=false
export REVIEW__LANGUAGE="${REVIEW__LANGUAGE:-Vietnamese}"

export LLM__PROVIDER=OPENAI
export LLM__META__MODEL="${LLM__META__MODEL:-deepseek-v4-pro}"
export LLM__HTTP_CLIENT__API_URL="https://opencode.ai/zen/go/v1"
export LLM__HTTP_CLIENT__API_TOKEN="${OPENCODE_TOKEN:?Set OPENCODE_TOKEN env var first}"
export LLM__HTTP_CLIENT__TIMEOUT="${LLM__HTTP_CLIENT__TIMEOUT:-90}"

export VCS__PROVIDER=GITLAB
export VCS__PIPELINE__PROJECT_ID="${VCS__PIPELINE__PROJECT_ID:-1405}"
export VCS__PIPELINE__MERGE_REQUEST_ID="${VCS__PIPELINE__MERGE_REQUEST_ID:-88}"
export VCS__HTTP_CLIENT__API_URL="https://gitlab.dehasoft.vn"
export VCS__HTTP_CLIENT__API_TOKEN="${GITLAB_TOKEN:?Set GITLAB_TOKEN env var first}"
export VCS__HTTP_CLIENT__VERIFY="false"

export AGENT__STRUCTURED_TOOL_CALLS_ENABLED="${AGENT__STRUCTURED_TOOL_CALLS_ENABLED:-true}"
export AGENT__UNSTRUCTURED_RECOVERY_ENABLED="${AGENT__UNSTRUCTURED_RECOVERY_ENABLED:-true}"
export AGENT__MAX_FILES_PER_CHUNK="${AGENT__MAX_FILES_PER_CHUNK:-10}"
export AGENT__MAX_ITERATIONS="${AGENT__MAX_ITERATIONS:-6}"
export AGENT__MAX_TOTAL_TOKENS="${AGENT__MAX_TOTAL_TOKENS:-80000}"
export AGENT__MAX_TOTAL_CONTEXT_CHARS="${AGENT__MAX_TOTAL_CONTEXT_CHARS:-60000}"
export AGENT__COMMAND_TIMEOUT="${AGENT__COMMAND_TIMEOUT:-10}"
export AGENT__COMPACTION_ENABLED="${AGENT__COMPACTION_ENABLED:-true}"
export AGENT__MAX_COMPACTIONS_PER_RUN="${AGENT__MAX_COMPACTIONS_PER_RUN:-2}"

echo "Agent mode: codex-like defaults"
echo "Agent runtime: chunks=$AGENT__MAX_FILES_PER_CHUNK iterations=$AGENT__MAX_ITERATIONS token_budget=$AGENT__MAX_TOTAL_TOKENS context_budget=$AGENT__MAX_TOTAL_CONTEXT_CHARS cmd_timeout=$AGENT__COMMAND_TIMEOUT compaction_enabled=$AGENT__COMPACTION_ENABLED compactions=$AGENT__MAX_COMPACTIONS_PER_RUN structured=$AGENT__STRUCTURED_TOOL_CALLS_ENABLED recover=$AGENT__UNSTRUCTURED_RECOVERY_ENABLED http_timeout=$LLM__HTTP_CLIENT__TIMEOUT"

# ---------------------------------------------------------------------------
# 3. Coding conventions
#    Point CONVENTIONS_PATH at a local .md file or a directory of .md files
#    (relative to CWD, or absolute). Skips the conventions feature entirely
#    if CONVENTIONS_PATH is left unset.
# ---------------------------------------------------------------------------
CONVENTIONS_PATH="${CONVENTIONS_PATH:-}"

if [ -n "$CONVENTIONS_PATH" ]; then
  export CONVENTIONS__ENABLED=true
  export CONVENTIONS__SOURCES="[{\"type\":\"local\",\"path\":\"${CONVENTIONS_PATH}\"}]"
  echo "Conventions enabled from: $CONVENTIONS_PATH"
else
  export CONVENTIONS__ENABLED=false
fi

# ---------------------------------------------------------------------------
# 4. Git preflight — tránh 'fatal: bad object' khi local thiếu base/head SHA
#    (inline line validator cần git diff base..head chạy được ở local)
# ---------------------------------------------------------------------------
cd "$TARGET_REPO_DIR"
echo "Running review from target repo: $TARGET_REPO_DIR"

if git rev-parse --git-dir >/dev/null 2>&1 && git remote get-url origin >/dev/null 2>&1; then
  if [ "$(git rev-parse --is-shallow-repository)" = "true" ]; then
    echo "Shallow repo detected, unshallowing..."
    git fetch --unshallow origin || git fetch --depth=2000 origin || true
  fi

  echo "Fetching MR refs for !${VCS__PIPELINE__MERGE_REQUEST_ID} ..."
  git fetch origin \
    "+refs/merge-requests/${VCS__PIPELINE__MERGE_REQUEST_ID}/head:refs/remotes/origin/mr-${VCS__PIPELINE__MERGE_REQUEST_ID}" \
    "+refs/heads/*:refs/remotes/origin/*" || true
else
  echo "Warning: $TARGET_REPO_DIR is not a git repo with origin — diff validation may fail"
fi

# ---------------------------------------------------------------------------
# 5. Run (từ TARGET_REPO_DIR để agent explore đúng codebase)
# ---------------------------------------------------------------------------
"$AI_REVIEW" run-agent
