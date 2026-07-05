// Generate a ready-to-paste CI integration snippet per VCS provider, plus the
// list of secrets the user must create. Secrets (tokens) are passed via env
// vars in CI — NOT in .ai-review.yaml, because the tool does not expand
// ${...} inside YAML values.

const IMAGE = 'supersentaj/argus-review:latest';
const ACTION = 'sang-hv/argus-code-review@main';

// llmSecrets: array of { name } env var names the LLM needs (token / bedrock keys)
function llmEnvLines(llmSecrets, indent, refFn) {
  return llmSecrets.map((s) => `${indent}${s.env}: ${refFn(s.name)}`).join('\n');
}

export function ciIntegration(vcsProvider, llmSecrets) {
  switch (vcsProvider) {
    case 'GITHUB':
      return {
        platform: 'GitHub Actions',
        filename: '.github/workflows/argus-review.yml',
        secrets: [...llmSecrets],
        note: 'GITHUB_TOKEN is provided automatically by GitHub Actions.',
        snippet: `name: ArgusReview
on:
  workflow_dispatch:
    inputs:
      pull-request-number: { required: true }
permissions:
  contents: read
  pull-requests: write
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: ${ACTION}
        with:
          review-command: run
        env:
${llmEnvLines(llmSecrets, '          ', (n) => `\${{ secrets.${n} }}`)}
          VCS__PROVIDER: GITHUB
          VCS__PIPELINE__OWNER: \${{ github.repository_owner }}
          VCS__PIPELINE__REPO: \${{ github.event.repository.name }}
          VCS__PIPELINE__PULL_NUMBER: \${{ inputs.pull-request-number }}
          VCS__HTTP_CLIENT__API_URL: https://api.github.com
          VCS__HTTP_CLIENT__API_TOKEN: \${{ secrets.GITHUB_TOKEN }}`,
      };

    case 'GITLAB':
      return {
        platform: 'GitLab CI',
        filename: '.gitlab-ci.yml',
        secrets: [...llmSecrets],
        note: 'CI_JOB_TOKEN is provided automatically. If posting MR comments returns 401, create a Project Access Token with the "api" scope and use it instead.',
        snippet: `argus-review:
  image:
    name: ${IMAGE}
    entrypoint: [ "" ]
  rules:
    - if: '$CI_MERGE_REQUEST_IID'
      when: manual
  allow_failure: true
  script:
    - argus-review run
  variables:
${llmEnvLines(llmSecrets, '    ', (n) => `"$${n}"`)}
    VCS__PROVIDER: "GITLAB"
    VCS__PIPELINE__PROJECT_ID: "$CI_PROJECT_ID"
    VCS__PIPELINE__MERGE_REQUEST_ID: "$CI_MERGE_REQUEST_IID"
    VCS__HTTP_CLIENT__API_URL: "$CI_SERVER_URL"
    VCS__HTTP_CLIENT__API_TOKEN: "$CI_JOB_TOKEN"`,
      };

    case 'BITBUCKET_CLOUD':
      return {
        platform: 'Bitbucket Pipelines',
        filename: 'bitbucket-pipelines.yml',
        secrets: [...llmSecrets, { name: 'BITBUCKET_TOKEN', env: 'VCS__HTTP_CLIENT__API_TOKEN', desc: 'App password / access token with PR read+write' }],
        note: 'Set the secrets as repository variables (Repository settings → Repository variables).',
        snippet: `pipelines:
  pull-requests:
    '**':
      - step:
          name: ArgusReview
          image: ${IMAGE}
          script:
            - argus-review run
          # Set these as repository variables:
          #   ${llmSecrets.map((s) => s.name).join(', ')}, BITBUCKET_TOKEN
          # Mapped via env in the step, e.g.:
          #   LLM__HTTP_CLIENT__API_TOKEN=$LLM_API_TOKEN
          #   VCS__PROVIDER=BITBUCKET_CLOUD
          #   VCS__PIPELINE__WORKSPACE=$BITBUCKET_WORKSPACE
          #   VCS__PIPELINE__REPO_SLUG=$BITBUCKET_REPO_SLUG
          #   VCS__PIPELINE__PULL_REQUEST_ID=$BITBUCKET_PR_ID
          #   VCS__HTTP_CLIENT__API_URL=https://api.bitbucket.org/2.0
          #   VCS__HTTP_CLIENT__API_TOKEN=$BITBUCKET_TOKEN`,
      };

    default:
      return {
        platform: vcsProvider,
        filename: 'CI pipeline',
        secrets: [...llmSecrets, { name: 'VCS_API_TOKEN', env: 'VCS__HTTP_CLIENT__API_TOKEN', desc: 'Token with PR/MR read+write' }],
        note: 'Run the Docker image in your CI and pass the config via env vars.',
        snippet: `# Run the ArgusReview image and pass config via env vars:
docker run --rm -v "$PWD:/app" \\
${llmSecrets.map((s) => `  -e ${s.env}="$${s.name}" \\`).join('\n')}
  -e VCS__PROVIDER=${vcsProvider} \\
  -e VCS__HTTP_CLIENT__API_TOKEN="$VCS_API_TOKEN" \\
  ${IMAGE} run
# (also set VCS__PIPELINE__* for your provider — see docs/configs)`,
      };
  }
}
