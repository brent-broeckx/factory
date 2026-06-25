# Software Factory

> An autonomous, AI-driven software development pipeline that lives entirely inside
> a GitHub repository. Describe what you want to build — the AI designs, implements,
> reviews, and ships it.

---

## What Is This?

This is a **GitHub repository template**. When you create a repository from it, you
get a complete autonomous development system powered by AI agents and GitHub Actions.

You write issues. The AI writes code.

```
You: "Build me a task management REST API with JWT auth and PostgreSQL"
      │
      ▼
🧠 Planner Agent  →  Generates architecture + 12 GitHub issues
      │
      ▼
You:  Review issues, apply 'ready' label to approved ones
      │
      ▼
🛠️ Developer Agent  →  Writes code, creates branches, opens PRs
      │
      ▼
🔍 Reviewer + 🧪 QA + 🔒 Security  →  Automated review on every PR
      │
      ▼
🔄 Developer Agent  →  Fixes review comments automatically (up to 3 attempts)
      │
      ▼
✅ Auto-merge when all checks pass
      │
      ▼
🚀 Manual release when you're ready
```

---

## Human Control Points

The system is **human-gated at every critical decision**:

| Stage | Who controls it |
|-------|----------------|
| Start planning | Human applies `bootstrap` label |
| Start development | Human applies `ready` label to each issue |
| Release | Human triggers manually with version number |
| Pause at any point | Human disables workflows or adds `needs-human` label |

> **Nothing executes automatically after repo creation.**
> No AI runs unless a human explicitly approves it.

---

## Quick Start

### 1. Create your repository

Click **"Use this template"** → **"Create a new repository"** at the top of this page.

### 2. Run Initial Setup

Go to **Actions** → **🔧 Initial Setup** → **Run workflow**.

This creates all required labels and shows you the configuration checklist.

### 3. Configure your API key

Go to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

```
Name:  AI_API_KEY
Value: sk-... (your OpenAI API key, or any compatible provider)
```

### 4. Set workflow permissions

Go to **Settings** → **Actions** → **General** → **Workflow permissions**:
- Select: **"Read and write permissions"**
- Check: **"Allow GitHub Actions to create and approve pull requests"**

### 5. Configure branch protection (recommended)

Go to **Settings** → **Branches** → Add a rule for `main`:
- ✅ Require status checks: `AI Code Review`, `AI QA & Test Analysis`, `AI Security Scan`
- ✅ Allow auto-merge (also enable in **Settings → General**)

### 6. Configure your project

Edit [`config/project-config.yaml`](config/project-config.yaml) with your project
details. This gives the Developer Agent context about your tech stack.

---

## The Bootstrap Workflow

For large projects or multi-feature initiatives:

1. Create an issue using the **Bootstrap** template
2. Describe your application in detail
3. Save — **nothing happens yet**
4. Apply the **`bootstrap`** label
5. The Planner Agent generates architecture + sub-issues (labeled `draft`)
6. Review each draft issue
7. Apply **`ready`** to approved issues → development begins

## The Direct Workflow

For individual, well-defined tasks:

1. Create a new issue (Feature or Bug template)
2. The system automatically labels it `ready`
3. The Developer Agent picks it up immediately

---

## Agents

| Agent | Trigger | What it does |
|-------|---------|-------------|
| 🧠 **Planner** | `bootstrap` label on issue | Decomposes request into architecture + sub-issues |
| 🛠️ **Developer** | `ready` label on issue | Implements the feature, creates branch + PR |
| 🔄 **Developer (fix)** | Reviewer requests changes | Fixes review comments, pushes to same branch |
| 🔍 **Reviewer** | PR opened/updated | Reviews code quality, architecture, correctness |
| 🧪 **QA** | PR opened/updated | Runs tests, analyses coverage gaps |
| 🔒 **Security** | PR opened/updated | Scans for OWASP issues, secrets, vulnerabilities |
| 🚀 **Release** | Manual workflow_dispatch | Builds, tags, and releases the project |

---

## Label Reference

| Label | Colour | Meaning |
|-------|--------|---------|
| `bootstrap` | 🔴 Red | Triggers the Planner Agent |
| `draft` | ⬜ Grey | AI-generated, awaiting human review |
| `ready` | 🟢 Green | Approved for AI development |
| `in-progress` | 🟡 Amber | Developer Agent is implementing |
| `review` | 🔵 Blue | PR open, under review |
| `done` | 🟣 Purple | Merged and complete |
| `ai-generated` | 🟣 Violet | Created by an AI agent |
| `needs-human` | 🔴 Red | Fix loop exhausted — human required |
| `skip-ai-review` | ⬛ Slate | Skip reviewer for this PR |
| `skip-qa` | ⬛ Slate | Skip QA for this PR |
| `skip-security` | ⬛ Slate | Skip security scan for this PR |

---

## Cost Control

The system is designed to minimise unnecessary AI API calls:

- **Nothing runs until you say so** — no idle polling, no background loops
- **Draft buffer** — bootstrap issues stay `draft` with zero cost until you approve
- **Iteration cap** — `MAX_FIX_ITERATIONS` (default: 3) stops infinite fix loops
- **Token limits** — configurable per-call token caps via `AI_MAX_TOKENS`
- **Cancellation** — reviewer/QA/security cancel previous runs when PR updates
- **Skip labels** — bypass any agent on a per-PR basis

**Estimated cost per issue (gpt-4o):** ~$0.10–0.25 depending on complexity.

---

## AI Provider Compatibility

Works with any OpenAI-compatible API:

| Provider | Set `AI_BASE_URL` to |
|----------|---------------------|
| **OpenAI** (default) | `https://api.openai.com/v1` |
| **Azure OpenAI** | `https://<resource>.openai.azure.com/openai/deployments/<deploy>` |
| **Together AI** | `https://api.together.xyz/v1` |
| **Ollama** (local) | `http://localhost:11434/v1` |

Change the model via the `AI_MODEL` repository variable.

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/GUIDANCE.md](docs/GUIDANCE.md) | Complete setup and operations guide |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and agent architecture |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | End-to-end workflow walkthrough with example |

---

## Repository Structure

```
.github/
  workflows/         8 GitHub Actions workflows
  ISSUE_TEMPLATE/    Bootstrap, Feature, Bug templates
  pull_request_template.md

agents/              Python agent scripts (one per agent)
  planner/
  developer/
  reviewer/
  qa/
  security/

prompts/             System prompts loaded by each agent
config/              Agent and project configuration
docs/                GUIDANCE, ARCHITECTURE, WORKFLOW
templates/           Reference templates for issues and PRs
```

---

## License

MIT — use this template freely in your own projects.
