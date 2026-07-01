# ArgusReview Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fully rebrand the fork from AI Review / `xai-review` / `ai_review` to ArgusReview / `argus-review` / `argus_review`.

**Architecture:** Keep runtime review behavior unchanged and make the rename mechanical at package, import, CLI, Docker, Action, workflow, documentation, and test surfaces. The source tree becomes `argus_review/`; `pyproject.toml` becomes the source of truth for the `argus-review` distribution and `argus-review` console script.

**Tech Stack:** Python 3.11+, setuptools, Typer, pytest, Docker, GitHub Actions.

---

## File Structure

- Rename directory: `ai_review/` -> `argus_review/`.
- Modify: `pyproject.toml` for distribution metadata, package discovery, package data, and console script.
- Modify: `Dockerfile` to install the local package instead of upstream `xai-review` from PyPI.
- Modify: `action.yml` to install and run local ArgusReview.
- Modify: `.github/workflows/reusable-docker.yml` to publish `argus-review` Docker tags and remove `AI_REVIEW_VERSION` build arg.
- Modify: docs and examples under `README.md`, `docs/`, and `ci/` to use `ArgusReview`, `argus-review`, and future `argus-review` image names.
- Modify: `conftest.py`, all package imports, tests, monkeypatch strings, and string literals that intentionally reference the old module path.
- Add or update tests in `argus_review/tests/suites/cli/test_main.py` and `argus_review/tests/suites/packaging/test_metadata.py` to pin the new package identity.

### Task 1: Add Failing Identity Tests

**Files:**
- Modify after rename: `argus_review/tests/suites/cli/test_main.py`
- Create after rename: `argus_review/tests/suites/packaging/__init__.py`
- Create after rename: `argus_review/tests/suites/packaging/test_metadata.py`

- [ ] **Step 1: Rename package directory first so new test paths can exist**

Run:

```bash
mv ai_review argus_review
```

Expected: `argus_review/cli/main.py` exists and `ai_review/` no longer exists.

- [ ] **Step 2: Mechanically update import paths in Python files**

Run:

```bash
perl -pi -e 's/\bai_review\b/argus_review/g' $(find . -name '*.py' -not -path './.git/*')
```

Expected: Python imports and monkeypatch strings now use `argus_review`.

- [ ] **Step 3: Update CLI test expectation for the new display name**

In `argus_review/tests/suites/cli/test_main.py`, change the final assertion in `test_show_config_outputs_json` to:

```python
assert "Loaded ArgusReview configuration" in result.output
```

- [ ] **Step 4: Add package metadata tests**

Create `argus_review/tests/suites/packaging/__init__.py`:

```python
"""Packaging tests for ArgusReview."""
```

Create `argus_review/tests/suites/packaging/test_metadata.py`:

```python
import tomllib
from pathlib import Path


def load_pyproject() -> dict:
    return tomllib.loads(Path("pyproject.toml").read_text())


def test_distribution_identity_is_argusreview():
    pyproject = load_pyproject()

    assert pyproject["project"]["name"] == "argus-review"
    assert pyproject["project"]["scripts"] == {
        "argus-review": "argus_review.cli.main:app",
    }


def test_setuptools_discovers_argusreview_package_data():
    pyproject = load_pyproject()

    assert pyproject["tool"]["setuptools"]["packages"]["find"]["include"] == [
        "argus_review*",
    ]
    assert pyproject["tool"]["setuptools"]["package-data"] == {
        "argus_review.prompts": ["*.md"],
        "argus_review.resources": ["*.yaml"],
    }
```

- [ ] **Step 5: Run tests to verify they fail before metadata/app text is fixed**

Run:

```bash
pytest argus_review/tests/suites/cli/test_main.py::test_show_config_outputs_json argus_review/tests/suites/packaging/test_metadata.py -q
```

Expected: FAIL because `pyproject.toml` still names `xai-review`, the console script still points at `ai_review`, and CLI output still says `AI Review`.

### Task 2: Update Python Package Metadata and CLI Branding

**Files:**
- Modify: `pyproject.toml`
- Modify: `argus_review/cli/main.py`

- [ ] **Step 1: Update `pyproject.toml` identity**

Set these exact values in `pyproject.toml`:

```toml
[project]
name = "argus-review"
description = "ArgusReview is an AI-powered code review tool for GitHub, GitLab, Bitbucket Cloud, Bitbucket Server, Azure DevOps and Gitea"

[project.urls]
Issues = "https://github.com/deha-project/argus-review/issues"
Homepage = "https://github.com/deha-project/argus-review"
Repository = "https://github.com/deha-project/argus-review"

[project.scripts]
argus-review = "argus_review.cli.main:app"

[tool.setuptools.packages.find]
where = ["."]
include = ["argus_review*"]

[tool.setuptools.package-data]
"argus_review.prompts" = ["*.md"]
"argus_review.resources" = ["*.yaml"]
```

Keep the existing version, dependencies, Python requirement, classifiers, and license.

- [ ] **Step 2: Update CLI display strings**

In `argus_review/cli/main.py`, update the app help and config heading:

```python
app = typer.Typer(help="ArgusReview CLI")
```

and:

```python
typer.secho("Loaded ArgusReview configuration:", fg=typer.colors.CYAN, bold=True)
```

- [ ] **Step 3: Run focused metadata and CLI tests**

Run:

```bash
pytest argus_review/tests/suites/cli/test_main.py::test_show_config_outputs_json argus_review/tests/suites/packaging/test_metadata.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit package identity changes**

Run:

```bash
git add pyproject.toml argus_review/tests/suites/cli/test_main.py argus_review/tests/suites/packaging
git commit -m "refactor: rename package identity to ArgusReview"
```

### Task 3: Complete Import Rename and Runtime Smoke Tests

**Files:**
- Modify: all Python files under `argus_review/`
- Modify: `conftest.py`

- [ ] **Step 1: Search for old module references**

Run:

```bash
rg -n "\bai_review\b" --glob '*.py' .
```

Expected: no results. If results appear in Python imports or monkeypatch paths, replace `ai_review` with `argus_review`.

- [ ] **Step 2: Run import smoke test**

Run:

```bash
python -c "import argus_review; import argus_review.cli.main"
```

Expected: command exits with code 0.

- [ ] **Step 3: Run CLI tests**

Run:

```bash
pytest argus_review/tests/suites/cli/test_main.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit import rename**

Run:

```bash
git add conftest.py argus_review
git commit -m "refactor: rename Python module to argus_review"
```

### Task 4: Update Dockerfile, GitHub Action, and Publish Workflows

**Files:**
- Modify: `Dockerfile`
- Modify: `action.yml`
- Modify: `.github/workflows/reusable-docker.yml`

- [ ] **Step 1: Replace Dockerfile with local-source install**

Set `Dockerfile` to:

```dockerfile
ARG PYTHON_VERSION=3.12-slim-bullseye
FROM python:${PYTHON_VERSION}

WORKDIR /app

RUN apt-get update && \
    apt-get install -y bash ca-certificates curl git libexpat1 openssh-client ripgrep && \
    rm -rf /var/lib/apt/lists/*

RUN git config --global --add safe.directory '*'
RUN git config --global core.quotepath false

COPY pyproject.toml README.md LICENSE ./
COPY argus_review ./argus_review

RUN pip install --no-cache-dir .

ENTRYPOINT ["argus-review"]
```

- [ ] **Step 2: Update `action.yml` branding and local install**

Set the relevant action values to:

```yaml
name: 'ArgusReview'
author: 'DEHA'
branding:
  icon: 'eye'
  color: 'purple'
description: 'AI-powered code review tool'
```

Set the install and run steps to:

```yaml
    - name: Install ArgusReview
      run: pip install --no-cache-dir .
      shell: bash

    - name: Run ArgusReview
      run: |
        argus-review show-config
        argus-review ${{ inputs.review-command }}
      shell: bash
```

- [ ] **Step 3: Update Docker publish tags**

In `.github/workflows/reusable-docker.yml`, remove the `build-args` block and change tags to:

```yaml
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/argus-review:latest
            ${{ secrets.DOCKER_USERNAME }}/argus-review:${{ github.ref_name }}
```

- [ ] **Step 4: Run YAML/text checks**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in ["action.yml", ".github/workflows/reusable-docker.yml"]:
    text = Path(path).read_text()
    assert "argus-review" in text or "ArgusReview" in text
assert "xai-review" not in Path("action.yml").read_text()
assert "ai-review show-config" not in Path("action.yml").read_text()
PY
```

Expected: command exits with code 0.

- [ ] **Step 5: Commit container/action updates**

Run:

```bash
git add Dockerfile action.yml .github/workflows/reusable-docker.yml
git commit -m "build: run ArgusReview from local package"
```

### Task 5: Update Documentation and CI Examples

**Files:**
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `docs/cli/README.md`
- Modify: `docs/ci/*.yaml`, `docs/ci/Jenkinsfile`, `docs/ci/README.md`
- Modify: `docs/configs/README.md`
- Modify: `docs/hooks/README.md`
- Modify: `docs/prompts/README.md`
- Modify: `docs/troubleshooting/README.md`
- Modify: `ci/review/config.yaml`

- [ ] **Step 1: Apply mechanical documentation replacements**

Run:

```bash
perl -pi -e 's/xai-review/argus-review/g; s/\bai-review\b/argus-review/g; s/AI Review/ArgusReview/g; s/XAI Review/ArgusReview/g; s#Nikita-Filonov/ai-review#deha-project/argus-review#g; s#nikitafilonov/ai-review#deha/argus-review#g' README.md docs/**/*.md docs/ci/* ci/review/config.yaml
```

Expected: docs and CI examples point at ArgusReview package, CLI, repo, and image names.

- [ ] **Step 2: Manually repair heading and prose after replacements**

Review `README.md` and `docs/cli/README.md` for awkward text caused by mechanical replacement. Keep examples consistent:

```bash
pip install argus-review
argus-review run
argus-review run-inline
argus-review run-context
argus-review run-summary
argus-review run-inline-reply
argus-review run-summary-reply
docker run --rm -v $(pwd):/app deha/argus-review:latest run-summary
```

Because the Dockerfile has `ENTRYPOINT ["argus-review"]`, Docker examples should pass only the subcommand after the image name.

- [ ] **Step 3: Search docs for old package or command instructions**

Run:

```bash
rg -n "xai-review|ai-review|AI Review|XAI Review|nikitafilonov/ai-review|Nikita-Filonov/ai-review" README.md docs ci action.yml Dockerfile pyproject.toml .github/workflows
```

Expected: no results except in the approved design spec and implementation plan if included in the search. When searching implementation files only, no old user-facing instructions should remain.

- [ ] **Step 4: Commit documentation updates**

Run:

```bash
git add README.md docs ci
git commit -m "docs: update ArgusReview usage"
```

### Task 6: Verify Package Build and Test Suite

**Files:**
- No planned source edits unless verification exposes rename misses.

- [ ] **Step 1: Install build dependencies if available**

Run:

```bash
python -m pip install --upgrade pip build
```

Expected: PASS. If network is unavailable, skip package-build verification and record that in the final summary.

- [ ] **Step 2: Build local distribution**

Run:

```bash
python -m build
```

Expected: `dist/argus_review-0.68.0.tar.gz` and `dist/argus_review-0.68.0-py3-none-any.whl` are created.

- [ ] **Step 3: Install package in editable mode**

Run:

```bash
python -m pip install -e .
```

Expected: installation succeeds and exposes `argus-review`.

- [ ] **Step 4: Run CLI smoke test**

Run:

```bash
argus-review --help
```

Expected: output includes `ArgusReview CLI`.

- [ ] **Step 5: Run full tests**

Run:

```bash
pytest -q
```

Expected: PASS.

- [ ] **Step 6: Search runtime files for old module imports**

Run:

```bash
rg -n "\bai_review\b|xai-review|ai-review" --glob '!docs/superpowers/**' --glob '!dist/**' .
```

Expected: no results in runtime code, package metadata, Dockerfile, Action, workflows, or docs. If results are historical links in README that the team wants to keep, document them explicitly; otherwise replace them.

- [ ] **Step 7: Optional Docker build**

Run:

```bash
docker build -t argus-review:local .
docker run --rm argus-review:local --help
```

Expected: build succeeds and help output includes `ArgusReview CLI`. If Docker is unavailable in the environment, record that in the final summary.

- [ ] **Step 8: Commit verification fixes**

If verification found missing replacements, run:

```bash
git add <changed-files>
git commit -m "chore: finish ArgusReview rename"
```

If no changes are needed, do not create an empty commit.
