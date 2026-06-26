# Copilot Instructions

This repository is an **autonomous AI-driven software development pipeline template**.
When this template is used to create a new repository, GitHub Copilot acts as the
primary developer — picking up issues, writing code, opening PRs, and responding to
review feedback.

These instructions apply to every task Copilot performs in this repository.

---

## Before writing any code

1. **Read `config/project-config.yaml`** — it contains the project's language,
   framework, test framework, linter, branch prefix, and deployment target.
   Treat it as the source of truth for all tech-stack decisions.

2. **Read existing files in the relevant area** before creating new ones.
   Match the existing code style, naming conventions, and file structure exactly.
   Do not impose external conventions that aren't already present in the codebase.

3. **Read the full linked issue** including every acceptance criteria checkbox.
   Every checkbox must be satisfied before the PR is ready for review.

---

## Branch naming

Always create branches with this pattern:

```
feat/issue-{number}-{short-slug}
```

Examples:
- `feat/issue-12-user-authentication`
- `feat/issue-34-add-pagination`

The `{short-slug}` must be lowercase, hyphen-separated, and derived from the issue title.
The branch prefix `feat` can be overridden by the `conventions.branch_prefix` field in
`config/project-config.yaml`.

---

## Pull request format

Every PR body must:
1. Start with a `## Summary` section (2–3 sentences describing what was built and why)
2. Include a `## Changes` section listing the files modified and the reason for each change
3. Include a `## Testing` section describing how the changes were tested
4. End with `Closes #N` where `N` is the issue number — this auto-closes the issue on merge

PRs must be opened as **drafts** until all tests pass in CI.

---

## Testing requirements

- Write tests for **every new function, method, and class**
- Test file location and naming must follow the pattern in `config/project-config.yaml`
  (`testing.pattern` field)
- Aim for the coverage threshold set in `testing.min_coverage_percent`
- Tests must cover:
  - The happy path
  - At least one error/edge case per function
  - Boundary values where applicable
- Do **not** use `time.sleep()`, hardcoded timestamps, or live network calls in tests —
  mock them

---

## Code quality requirements

- Handle all errors explicitly — never silently swallow exceptions
- Never hardcode secrets, API keys, tokens, or environment-specific values
- Use parameterised queries — never concatenate user input into SQL strings
- Validate inputs at system boundaries (API handlers, CLI entry points)
- Keep functions under ~50 lines; extract helpers if they grow beyond that
- Do not leave TODO comments or commented-out code blocks in the final commit

---

## Review agents

When Copilot opens a PR, three review agents will run automatically via
`.github/agents/`:

| Agent | File | Focus |
|-------|------|-------|
| Security | `.github/agents/security.agent.md` | OWASP Top 10, secrets, injection |
| QA | `.github/agents/qa.agent.md` | Test coverage, correctness vs requirements |
| Code quality | `.github/agents/code-quality.agent.md` | Readability, architecture, docs |

**Proactively avoid common findings:**
- No hardcoded secrets or credentials (security)
- No SQL string concatenation (security)
- No missing error handling (security + quality)
- No new public functions without tests (QA)
- No functions without docstrings/JSDoc when the rest of the file has them (quality)
- No stack traces or internal error details returned to the client (security + quality)

---

## Label behaviour

The workflow uses these labels — do not remove or rename them:

| Label | Meaning |
|-------|---------|
| `bootstrap` | Human trigger: start the Planner agent |
| `draft` | AI-generated issue awaiting human review |
| `ready` | Human trigger: start the Developer agent |
| `in-progress` | Copilot is implementing this issue |
| `review` | PR is open and under agent review |
| `done` | Issue is complete and merged |
| `ai-generated` | Created by a Copilot agent |
| `needs-human` | Requires human intervention |

---

## Agent architecture

This repository uses three different AI execution mechanisms. Understanding the
separation prevents you from trying to do things outside your scope.

**GitHub Agentic Workflows (gh-aw)** — used for the bootstrap/planning step.
Triggered by the `bootstrap` label. Runs `.github/agents/planner.agent.md` via
`gh aw run`. This agent creates sub-issues using the `gh` CLI and has full GitHub
API access. You (Copilot coding agent) are **not** involved in this step.

**Copilot coding agent** — that is you. Triggered when the `ready` label is applied
to an issue. You implement the feature described in the issue, create a branch,
write code, and open a PR. You do **not** create other issues or call the GitHub API.
You read `.github/copilot-instructions.md` (this file) for project conventions.

**Copilot code review** — triggered automatically on every PR. When you are requested
as a reviewer, you read `.github/agents/*.agent.md` files as review personas:
`security.agent.md`, `qa.agent.md`, and `code-quality.agent.md`. These files give
you a specific review focus for each dimension. This is separate from your role as
the coding agent.

---

## What NOT to do

- Do not modify files under `.github/` (workflows, agents, templates) unless the issue
  explicitly asks for it
- Do not modify `config/` or `docs/` unless the issue explicitly asks for it
- Do not add new dependencies without listing them in the PR and explaining why
- Do not use `--force` on any git operation
- Do not open PRs targeting branches other than `main` unless the issue specifies otherwise
