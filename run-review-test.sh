#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/Users/sanghv/Downloads/ai-code-review"
AI_REVIEW="$REPO_DIR/.venv/bin/argus-review"

# ---------------------------------------------------------------------------
# 1. Build/refresh the local package into .venv (editable install)
# ---------------------------------------------------------------------------
if [ ! -x "$REPO_DIR/.venv/bin/python" ]; then
  echo "Creating venv at $REPO_DIR/.venv ..."
  /opt/homebrew/bin/python3.12 -m venv "$REPO_DIR/.venv"
fi

echo "Installing/updating argus-review-code (editable) ..."
"$REPO_DIR/.venv/bin/pip" install -e "$REPO_DIR" -q

# ---------------------------------------------------------------------------
# 2. Runtime config
# ---------------------------------------------------------------------------
export REVIEW__DRY_RUN=true

export LLM__PROVIDER=OPENAI
export LLM__META__MODEL=glm-5.2
export LLM__HTTP_CLIENT__API_URL="https://opencode.ai/zen/go/v1"
export LLM__HTTP_CLIENT__API_TOKEN="${OPENCODE_TOKEN:?Set OPENCODE_TOKEN env var first}"
export LLM__HTTP_CLIENT__TIMEOUT=300

export VCS__PROVIDER=GITLAB
export VCS__PIPELINE__PROJECT_ID=1405
export VCS__PIPELINE__MERGE_REQUEST_ID=102
export VCS__HTTP_CLIENT__API_URL="https://gitlab.dehasoft.vn"
export VCS__HTTP_CLIENT__API_TOKEN="${GITLAB_TOKEN:?Set GITLAB_TOKEN env var first}"

export AGENT__MAX_FILES_PER_CHUNK=10
export AGENT__MAX_ITERATIONS="${AGENT_MAX_ITERATIONS:-8}"

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
# 4. Run
# ---------------------------------------------------------------------------
"$AI_REVIEW" run-agent
