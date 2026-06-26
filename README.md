# Software Factory

> An autonomous, AI-driven software development pipeline that lives entirely inside
> a GitHub repository. Describe what you want to build -- Copilot designs, implements,
> reviews, and ships it.

> **Requirements:** GitHub Copilot Enterprise or Copilot Business with the coding agent
> enabled by your org admin. See [SETUP.md](SETUP.md) for org admin instructions.

---

## What Is This?

This is a **GitHub repository template**. When you create a repository from it, you
get a complete autonomous development system powered by GitHub Copilot and GitHub Actions.

You write issues. Copilot writes code.

```
You: "Build me a task management REST API with JWT auth and PostgreSQL"
      |
      v
Planner Agent  ->  Generates architecture + 12 GitHub issues
      |
      v
You:  Review issues, apply 'ready' label to approved ones
      |
      v
Copilot coding agent  ->  Writes code, creates branches, opens PRs
      |
      v
Code quality + QA + Security  ->  Automated review on every PR
      |
      v
Auto-merge when all checks pass
      |
      v
Manual release when you're ready
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

Click **"Use this template"** -> **"Create a new repository"** at the top of this page.

### 2. Enable Copilot coding agent

Go to your repo **Settings** -> **Copilot** -> enable the coding agent.
(Your org admin must first enable this at the org level -- see [SETUP.md](SETUP.md).)

### 3. Run Initial Setup

Go to **Actions** -> **Initial Setup** -> **Run workflow**.

This creates all required labels.

### 4. Set workflow permissions

Go to **Settings** -> **Actions** -> **General** -> **Workflow permissions**:
- Select: **"Read and write permissions"**
- Check: **"Allow GitHub Actions to create and approve pull requests"**

### 5. Configure branch protection (recommended)

Go to **Settings** -> **Branches** -> Add a rule for `main`:
- Require status checks to pass before merging
- Enable auto-merge (also enable in **Settings -> General**)

### 6. Configure your project

Edit [`config/project-config.yaml`](config/project-config.yaml) with your project
details. Copilot reads this file for context about your tech stack and conventions.

---

## The Bootstrap Workflow

For large projects or multi-feature initiatives:

1. Create an issue using the **Bootstrap** template
2. Describe your application in detail
3. Save -- **nothing happens yet**
4. Apply the **`bootstrap`** label
5. Copilot's planner agent generates architecture + sub-issues (labeled `draft`)
6. Review each draft issue
7. Apply **`ready`** to approved issues -> development begins

## The Direct Workflow

For individual, well-defined tasks:

1. Create a new issue (Feature or Bug template)
2. The system automatically labels it `ready`
3. Copilot picks it up immediately

---

## Agents

| Agent | Trigger | What it does |
|-------|---------|-------------|
| **Planner** | `bootstrap` label on issue | Decomposes request into architecture + sub-issues |
| **Developer** | `ready` label on issue | Implements the feature, creates branch + PR |
| **Code Quality** | PR opened/updated | Reviews readability, architecture, correctness |
| **QA** | PR opened/updated | Analyses coverage gaps, requirement correctness |
| **Security** | PR opened/updated | Scans for OWASP issues, secrets, vulnerabilities |
| **Release** | Manual workflow_dispatch | Builds, tags, and releases the project |

Review agent definitions live in [`.github/agents/`](.github/agents/) -- edit them to
customise review behaviour for your project.

---

## Label Reference

| Label | Colour | Meaning |
|-------|--------|---------|
| `bootstrap` | Red | Triggers the Planner Agent |
| `draft` | Grey | AI-generated, awaiting human review |
| `ready` | Green | Approved for AI development |
| `in-progress` | Amber | Copilot is implementing |
| `review` | Blue | PR open, under review |
| `done` | Purple | Merged and complete |
| `ai-generated` | Violet | Created by an AI agent |
| `needs-human` | Red | Requires human intervention |
| `skip-ai-review` | Slate | Skip code quality review for this PR |
| `skip-qa` | Slate | Skip QA for this PR |
| `skip-security` | Slate | Skip security scan for this PR |

---

## Cost

No API keys or external secrets are required. All AI usage is covered by your
**GitHub Copilot Enterprise subscription** (Actions minutes + Copilot AI credits).

---

## Documentation

| Document | Description |
|----------|-------------|
| [SETUP.md](SETUP.md) | Org admin setup guide |
| [docs/GUIDANCE.md](docs/GUIDANCE.md) | Complete setup and operations guide |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and agent architecture |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | End-to-end workflow walkthrough with example |

---

## Repository Structure

```
.github/
  workflows/         5 GitHub Actions workflows
  agents/            4 Copilot agent definition files
  ISSUE_TEMPLATE/    Bootstrap, Feature, Bug templates
  copilot-instructions.md
  pull_request_template.md

prompts/             Migration notes (content moved to .github/agents/)
config/              Project configuration (read by Copilot for context)
docs/                GUIDANCE, ARCHITECTURE, WORKFLOW
templates/           Reference templates for issues and PRs
```

---

## License

MIT -- use this template freely in your own projects.