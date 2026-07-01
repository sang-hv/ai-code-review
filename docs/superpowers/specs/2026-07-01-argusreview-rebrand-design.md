# ArgusReview Rebrand Design

## Goal

Rebrand this fork from AI Review / `xai-review` to **ArgusReview** as a full product rename. The result should expose a new Python distribution, import package, CLI command, Docker build, GitHub Action metadata, documentation, and tests under the ArgusReview identity.

## Scope

The rebrand includes:

- Python distribution name: `argus-review`.
- Python import package: `argus_review`.
- CLI command: `argus-review`.
- Project-facing display name: `ArgusReview`.
- Dockerfile updated to build or install the local ArgusReview package rather than the upstream `xai-review` package.
- GitHub Action metadata updated to ArgusReview and running `argus-review`.
- Documentation and examples updated from `ai-review` / `xai-review` to ArgusReview equivalents.
- Tests and imports updated from `ai_review.*` to `argus_review.*`.

The old `ai-review` CLI alias will not be kept. This keeps the fork clean and avoids mixed branding.

## Non-Goals

- No behavior changes to review logic, LLM providers, VCS integrations, prompts, config schema, or comment format unless needed because of the rename.
- No publishing to PyPI or Docker Hub during implementation.
- No redesign of configuration keys such as `LLM__PROVIDER` or `VCS__PROVIDER`.
- No large refactor unrelated to package/module renaming.

## Architecture

The source package directory will be renamed from `ai_review/` to `argus_review/`. All internal imports, test imports, package discovery rules, and package-data mappings will reference `argus_review`.

`pyproject.toml` will become the source of truth for the new package identity:

- `[project].name = "argus-review"`
- description, URLs, keywords, and author/maintainer metadata updated where appropriate for this fork.
- `[project.scripts]` exposes `argus-review = "argus_review.cli.main:app"`.
- setuptools package discovery includes `argus_review*`.
- package data maps `argus_review.prompts` and `argus_review.resources`.

The Dockerfile should install the project from local source inside the image. This ensures custom code in the repo is what runs in CI or containers. It should no longer install `xai-review==${AI_REVIEW_VERSION}` from PyPI as the primary path.

`action.yml` should install the local package and execute `argus-review show-config` followed by `argus-review ${{ inputs.review-command }}`.

## Data Flow

The runtime flow remains unchanged:

1. `argus-review` starts the Typer app.
2. Configuration loads from YAML, JSON, ENV, and environment variables.
3. The review service creates LLM and VCS clients from config.
4. Review runners fetch PR/MR info, gather diffs, build prompts, call the LLM, parse output, and post comments.

Only module paths and user-facing command names change.

## Error Handling

Existing error behavior stays in place. Rename-specific risk is mainly import or package discovery failure. Implementation should catch these with:

- Import smoke test: `python -c "import argus_review"`.
- CLI smoke test: `argus-review --help`.
- Test suite run.
- Optional Docker build if dependencies are available.

## Testing

Minimum verification:

- Run targeted import/CLI checks after rename.
- Run the existing Python tests.
- Check there are no remaining unintended `ai_review` imports.
- Check docs and config examples do not still instruct users to install or run `xai-review` / `ai-review`, except if historical context is explicitly needed.

## Rollout Notes

This is a breaking rename. Consumers must update:

- Package install command from `xai-review` to `argus-review`.
- CLI command from `ai-review` to `argus-review`.
- Any Python imports from `ai_review` to `argus_review`.
- CI/Docker references to the new local build or future ArgusReview image.
