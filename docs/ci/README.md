# 📘 ArgusReview CI/CD Integration

This folder contains **ready-to-use CI/CD templates** for running ArgusReview automatically on **Pull Requests** (GitHub,
Bitbucket, Jenkins, Bitbucket, Azure DevOps) or **Merge Requests** (GitLab).

Each example shows how to:

- Install and configure ArgusReview
- Pass LLM and VCS credentials securely via environment variables
- Trigger agent review commands (`run-agent`, `run-agent-inline`, `run-agent-summary`)

---

## ⚙️ Supported CI/CD Providers

| Provider     | Template                                 | Description                                                                          |
|--------------|------------------------------------------|--------------------------------------------------------------------------------------|
| GitHub       | [github.yaml](./github.yaml)             | Manual workflow dispatch from Actions tab                                            |
| GitLab       | [gitlab.yaml](./gitlab.yaml)             | Manual job trigger in Merge Request pipelines                                        |
| Jenkins      | [Jenkinsfile](./Jenkinsfile)             | Declarative pipeline running the **run-agent** review stage                         |
| Bitbucket    | [bitbucket.yaml](./bitbucket.yaml)       | Manual custom pipeline trigger per Pull Request (supports all ArgusReview modes)     |
| Azure DevOps | [azure-devops.yaml](./azure-devops.yaml) | Manual or PR-triggered pipeline in **Azure Pipelines**                               |

---

👉 Choose the template matching your CI system, copy it into your repository, and adjust environment
variables (`OPENAI_API_KEY`, `GITHUB_TOKEN`, `CI_JOB_TOKEN`, `BITBUCKET_TOKEN`, etc.) as needed.
