# Architecture — Software Factory

## System Overview

The Software Factory is a self-contained, event-driven AI development pipeline
that lives entirely inside a GitHub repository. It uses GitHub Issues, Labels,
Pull Requests, and Actions as its sole state storage and execution engine.

No external database, message queue, or orchestration service is required.

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Repository                        │
│                                                                 │
│  Issues ──────► Labels ──────► Actions ──────► Pull Requests   │
│  (state)        (transitions)  (agents)        (state)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## GitHub as a State Machine

### Issue State Machine

```
[bootstrap] ──► Planner Agent ──► [draft]
                                       │
                                  Human Review
                                       │
                                   [ready] ──► Developer Agent ──► [in-progress]
                                                                         │
                                                                    PR Created
                                                                         │
                                                                    [review]
                                                                         │
                                                                  PR Merged
                                                                         │
                                                                    [done]
```

### PR State Machine

```
[open] ──► Reviewer + QA + Security Agents
               │
      ┌────────┴────────┐
      │                 │
  [approved]    [changes_requested]
      │                 │
      │         Developer Fix Agent
      │                 │
      │         push to branch ──► loop back to Reviewer
      │
  Auto-merge (when all checks pass + branch protection satisfied)
      │
  [merged]
```

### Label Lifecycle

| Label | Colour | Meaning |
|-------|--------|---------|
| `bootstrap` | Red | Applied by human to trigger planning |
| `draft` | Grey | AI-generated issue, not yet approved |
| `ready` | Green | Approved by human, queued for development |
| `in-progress` | Amber | Developer Agent is working on this |
| `review` | Blue | PR is open, under review |
| `done` | Purple | Merged and complete |
| `ai-generated` | Violet | Created by an AI agent |
| `needs-human` | Red | Fix loop exhausted, human required |
| `skip-ai-review` | Slate | Bypass AI reviewer for this PR |
| `skip-qa` | Slate | Bypass AI QA for this PR |
| `skip-security` | Slate | Bypass AI security scan for this PR |

---

## Agent Architecture

### Design Principles

All agents are:
- **Stateless** — each run reads all needed context from GitHub
- **Event-driven** — triggered by GitHub webhook events, never polled
- **Idempotent** — safe to re-run without causing duplicate side effects
- **Isolated** — each agent runs in its own fresh GitHub Actions runner
- **Cost-bounded** — every agent has explicit token and iteration limits

### Agent Inventory

```
agents/
├── planner/        Decomposes a bootstrap issue into a plan
├── developer/      Implements issues and fixes review comments
├── reviewer/       Reviews PR code quality and correctness
├── qa/             Analyses test coverage and runs test suites
└── security/       Scans for vulnerabilities and secrets
```

### Planner Agent

**Trigger:** `issues: labeled` where label = `bootstrap`

**Inputs:**
- Issue title and body
- Repository root structure (for context)
- `prompts/planner.prompt.md`

**Outputs:**
- N new GitHub issues labeled `draft` + `ai-generated`
- Summary comment on the bootstrap issue
- Bootstrap issue closed

**Side effects:** None (no code changes, no branch creation)

### Developer Agent

**Trigger (implement):** `issues: labeled` where label = `ready`

**Trigger (fix):** `pull_request_review: submitted` where state = `changes_requested`
and PR is labeled `ai-generated`

**Inputs (implement):**
- Issue title, body, acceptance criteria
- Repository structure
- `config/project-config.yaml`
- `prompts/developer.prompt.md`

**Inputs (fix):**
- PR review feedback (review body + inline comments)
- Current file contents from the PR branch
- `prompts/developer.prompt.md`

**Outputs:**
- New branch with committed files
- Pull Request linking back to the issue
- Issue label updated: `ready` → `in-progress` → `review`

**Cost cap:** `MAX_FIX_ITERATIONS` (default 3) fix attempts before adding `needs-human`

### Reviewer Agent

**Trigger:** `pull_request: opened | synchronize | reopened`

**Inputs:**
- PR title, description, author
- Diff of all changed files (up to 20 files, 3KB per patch)
- Linked issue description (if found)
- `prompts/reviewer.prompt.md`

**Outputs:**
- GitHub PR Review: APPROVE, REQUEST_CHANGES, or COMMENT
- Triggers Developer fix loop if REQUEST_CHANGES

**Skippable:** Label PR with `skip-ai-review`

### QA Agent

**Trigger:** `pull_request: opened | synchronize | reopened`

**Inputs:**
- Changed file list
- Detected project type
- Actual test suite output (if tests exist)
- `prompts/qa.prompt.md`

**Outputs:**
- PR comment with test results + AI coverage analysis
- Does NOT submit a blocking review (advisory only)

**Skippable:** Label PR with `skip-qa`

### Security Agent

**Trigger:** `pull_request: opened | synchronize | reopened`

**Inputs:**
- Diff of changed files
- Pre-scan results (regex-based secret detection)
- `prompts/security.prompt.md`

**Outputs:**
- PR comment with security findings
- If `critical` or `high` severity: submits REQUEST_CHANGES review (blocks merge)

**Skippable:** Label PR with `skip-security`

---

## Repository Structure

```
.github/
  workflows/
    planner.yml        Planner Agent workflow
    developer.yml      Developer Agent workflow (implement + fix)
    reviewer.yml       Reviewer Agent workflow
    qa.yml             QA Agent workflow
    security.yml       Security Agent workflow
    release.yml        Manual release workflow (always manual)
    label-manager.yml  Auto-labeling and issue lifecycle
    setup.yml          One-time setup: creates labels

agents/
  planner/
    agent.py           Planner Agent implementation
    requirements.txt
  developer/
    agent.py           Developer Agent implementation
    requirements.txt
  reviewer/
    agent.py           Reviewer Agent implementation
    requirements.txt
  qa/
    agent.py           QA Agent implementation
    requirements.txt
  security/
    agent.py           Security Agent implementation
    requirements.txt

prompts/
  planner.prompt.md    System prompt for the Planner
  developer.prompt.md  System prompt for the Developer
  reviewer.prompt.md   System prompt for the Reviewer
  qa.prompt.md         System prompt for QA
  security.prompt.md   System prompt for Security

config/
  agent-config.yaml    AI model and cost configuration
  project-config.yaml  Project-specific settings for the Developer Agent

docs/
  GUIDANCE.md          User guide (this file's companion)
  ARCHITECTURE.md      This file
  WORKFLOW.md          End-to-end workflow walkthrough

templates/
  issue-template.md    Reference issue template
  pr-template.md       Reference PR template
```

---

## AI Integration

The system uses a single OpenAI-compatible API interface. Any provider that
implements the `/v1/chat/completions` endpoint works (OpenAI, Azure OpenAI,
Together AI, Ollama, etc.).

Each agent:
1. Loads its system prompt from `prompts/<name>.prompt.md`
2. Constructs a user message from GitHub context
3. Calls the AI with `temperature=0.1` for consistency
4. Parses the structured JSON response
5. Executes the resulting GitHub API operations

All prompts explicitly require JSON output. The agents parse JSON from markdown
code fences for robustness.

---

## Security Model

- `GITHUB_TOKEN` is the only credential used for GitHub API calls
- Each workflow requests only the minimum permissions it needs
- `AI_API_KEY` is stored as a GitHub Secret (never logged or exposed)
- Security Agent detects hardcoded credentials in PRs before they merge
- All agents are read-only except the Developer (which has `contents: write`)
- No external network calls beyond the configured AI API endpoint
