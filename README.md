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
Planner Agent  ->  Generates architecture + GitHub issues (labeled 'draft')
      |
      v
You:  Review issues, apply 'ready' label, assign copilot-swe-agent[bot]
      |
      v
Copilot coding agent  ->  Writes code, creates branch, opens PR as draft
      |
      v
You:  Mark PR ready for review
      |
      v
PR Audit Agent  ->  Single automated review: security, quality, tests, correctness
      |
      v
Audit passes  ->  Merge when ready
```

---

## Human Control Points

The system is **human-gated at every critical decision**:

| Stage | Who controls it |
|-------|----------------|
| Start planning | Human applies `bootstrap` label |
| Start development | Human applies `ready` label + assigns `copilot-swe-agent[bot]` |
| Trigger PR audit | Human marks PR ready for review |
| Merge | Human merges (or enables auto-merge) |
| Pause at any point | Human disables workflows or adds `needs-human` label |

> **Nothing executes automatically after repo creation.**
> No AI runs unless a human explicitly approves it.

---

## Quick Start

### 1. Create your repository

Click **"Use this template"** -> **"Create a new repository"** at the top of this page.

### 2. Run initial setup

Go to **Actions** -> **Initial Setup** -> **Run workflow**.

This creates all required labels.

### 3. Set workflow permissions

Go to **Settings** -> **Actions** -> **General** -> **Workflow permissions**:
- Select: **"Read and write permissions"**
- Check: **"Allow GitHub Actions to create and approve pull requests"**

### 4. Enable auto-merge (recommended)

Go to **Settings** -> **General** -> enable **Allow auto-merge** and **Automatically delete head branches**.

### 5. Configure branch protection (recommended)

Go to **Settings** -> **Branches** -> Add a rule for `main`:
- Require status checks to pass before merging
- Require at least 1 approval
- Require linear history

### 6. Enable the Copilot coding agent

Go to **Settings** -> **Copilot** -> enable the coding agent.
(Your org admin must first enable this at the org level.)

### 7. Configure your project

Edit [`config/project-config.yaml`](config/project-config.yaml) with your project
details. Copilot reads this file for context about your tech stack and conventions.

---

## The Bootstrap Workflow

For large projects or multi-feature initiatives:

1. Create an issue using the **Bootstrap** template
2. Describe your application in detail
3. Save -- **nothing happens yet**
4. Apply the **`bootstrap`** label
5. The planner agent generates architecture + sub-issues (labeled `draft`)
6. Review each draft issue
7. Apply **`ready`** to approved issues
8. Assign **`copilot-swe-agent[bot]`** to each ready issue — development begins

## The Direct Workflow

For individual, well-defined tasks:

1. Create a new issue (Feature or Bug template)
2. Apply the **`ready`** label
3. Assign **`copilot-swe-agent[bot]`** — Copilot picks it up immediately

---

## Agents

| Agent | Type | Trigger | What it does |
|-------|------|---------|-------------|
| **Planner** | gh-aw | `bootstrap` label on issue | Decomposes request into architecture + sub-issues |
| **Developer** | Copilot coding agent | `copilot-swe-agent[bot]` assigned to issue | Implements the feature, creates branch + PR |
| **PR Audit** | gh-aw | PR marked ready for review | Single comprehensive review: security, code quality, test coverage, correctness vs issue requirements |

Skip the PR audit on a specific PR by applying the `skip-ai-review` label.

---

## Label Reference

| Label | Colour | Meaning |
|-------|--------|---------|
| `bootstrap` | Red | Triggers the Planner agent |
| `draft` | Grey | AI-generated issue, awaiting human review |
| `ready` | Green | Approved for AI development |
| `in-progress` | Amber | Copilot is implementing |
| `review` | Blue | PR open, under audit |
| `done` | Purple | Merged and complete |
| `ai-generated` | Violet | Created by an AI agent |
| `needs-human` | Red | Requires human intervention |
| `skip-ai-review` | Slate | Skip PR audit for this PR |
| `audit-passed` | Green | PR audit found no issues |
| `audit-needs-fix` | Amber | PR audit found issues to address |
| `audit-blocked` | Red | PR audit found critical issues |
| `blocked` | Red | PR blocked — critical issues must be resolved |

---

## Cost

No API keys or external secrets are required. All AI usage is covered by your
**GitHub Copilot Enterprise subscription** (Actions minutes + Copilot AI credits).

---

## Documentation

| Document | Description |
|----------|-------------|
| [SETUP.md](SETUP.md) | One-time repo setup guide |
| [docs/GUIDANCE.md](docs/GUIDANCE.md) | Complete setup and operations guide |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and agent architecture |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | End-to-end workflow walkthrough with example |

---

## Repository Structure

```
.github/
  workflows/         GitHub Actions workflows + gh-aw agent markdown files
    setup.yml          Creates all required labels
    developer.yml      Syncs labels when Copilot is assigned to an issue
    label-manager.yml  Marks issues done when a PR is merged
    pr-audit.md        PR audit agent (security, quality, tests, correctness)
    pr-audit.lock.yml  Compiled gh-aw workflow
  agents/
    agentic-workflows.md  VS Code agent for authoring gh-aw workflows
  skills/
    cgk-coding-conventions/   Mandatory coding conventions for the Copilot agent
    cgk-code-quality-review/  Code quality review checklist used in PR audit
  ISSUE_TEMPLATE/    Bootstrap, Feature, Bug templates
  copilot-instructions.md
  pull_request_template.md

config/              Project configuration (read by Copilot for context)
docs/                GUIDANCE, ARCHITECTURE, WORKFLOW
templates/           Reference templates for issues and PRs
```

---

## License

MIT -- use this template freely in your own projects.