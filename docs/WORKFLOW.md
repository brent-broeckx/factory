# Workflow — End-to-End Example

This document walks through the complete lifecycle of a feature from idea to
production, using a concrete example: **building a task management REST API**.

---

## Phase 0: Repository Setup

```
Human creates repo from template
         │
         ▼
Run "Initial Setup" workflow
         │
         ▼
Labels created, checklist displayed
         │
         ▼
Human configures secrets:
  AI_API_KEY = sk-...
  (optional) DEPLOY_TOKEN = ...

Human configures branch protection:
  - Require: AI Code Review, AI QA, AI Security Scan
  - Enable auto-merge
```

---

## Phase 1: Bootstrap — Planning

### Step 1: Human creates a bootstrap issue

> **Title:** Build a Task Management REST API
>
> **Body:**
> I need a REST API for managing tasks. Features needed:
> - CRUD operations for tasks (title, description, status, due date)
> - User authentication with JWT
> - Task assignment to users
> - Filtering and pagination
> - Built with Node.js / Express + PostgreSQL
> - Unit and integration tests

Human saves the issue. **Nothing happens yet.**

### Step 2: Human applies the `bootstrap` label

```
Issue #1 labeled: bootstrap
         │
         ▼
planner.yml triggers
         │
         ▼
Planner Agent runs:
  - Reads issue #1
  - Reads repo structure
  - Calls AI (planner.prompt.md)
  - AI returns JSON plan
```

### Step 3: Planner creates sub-issues

The agent creates ~12 issues across 4 epics:

**Epic: Infrastructure**
- #2 `Set up Express + TypeScript project structure` → `draft`
- #3 `Configure PostgreSQL with Prisma ORM` → `draft`
- #4 `Set up Jest testing framework` → `draft`

**Epic: Authentication**
- #5 `Implement JWT authentication middleware` → `draft`
- #6 `Create user registration and login endpoints` → `draft`

**Epic: Tasks API**
- #7 `Create task data model and migrations` → `draft`
- #8 `Implement CRUD endpoints for tasks` → `draft`
- #9 `Add task filtering, sorting, and pagination` → `draft`
- #10 `Implement task assignment to users` → `draft`

**Epic: Quality & Deployment**
- #11 `Write integration tests for all API endpoints` → `draft`
- #12 `Add input validation and error handling middleware` → `draft`
- #13 `Configure Docker and docker-compose` → `draft`

Planner posts a summary comment on issue #1 and closes it.

---

## Phase 2: Human Review

The human reviews each draft issue:

```
Human opens issue #2 → reads description → adds 'ready' label
Human opens issue #3 → reads description → adds 'ready' label
Human opens issue #5 → edits the body to add a specific JWT library → adds 'ready'
...
Human opens issue #13 → decides not to implement Docker yet → leaves as 'draft'
```

---

## Phase 3: Development

Each `ready` label triggers a Developer Agent run.

### Issue #2: Project Structure

```
Issue #2 labeled: ready
         │
         ▼
developer.yml triggers
         │
         ▼
Developer Agent:
  - Labels issue #2: in-progress
  - Reads issue description + repo structure
  - Calls AI (developer.prompt.md)
  - AI returns JSON with files:
      package.json, tsconfig.json, src/index.ts,
      src/app.ts, src/routes/index.ts, etc.
  - Creates branch: feature/issue-2-project-structure
  - Commits all files via GitHub API
  - Opens PR #14: "feat: Set up Express + TypeScript project structure"
  - Labels PR: ai-generated
  - Labels issue #2: review
```

### PR #14: Automated Review

Three agents run in parallel:

```
PR #14 opened
         │
    ┌────┼────┐
    │    │    │
  Reviewer  QA  Security
    │    │    │
    └────┼────┘
         │
Reviewer: "APPROVE — clean project structure, good TypeScript config"
QA: "No tests yet (expected for setup issue). Coverage will come in #11."
Security: "PASS — no vulnerabilities detected"
         │
         ▼
All checks pass → GitHub auto-merge fires
         │
         ▼
PR #14 merged
         │
         ▼
label-manager.yml: issue #2 labeled 'done', closed
```

### Issue #5: JWT Auth (with fix loop)

```
Issue #5 labeled: ready
         │
         ▼
Developer Agent implements JWT middleware
Creates branch: feature/issue-5-jwt-auth
Opens PR #17
         │
         ▼
Reviewer: "REQUEST_CHANGES
  - Token expiry not validated
  - Missing refresh token support (see acceptance criteria)"
         │
         ▼
developer.yml triggers (fix mode)
Developer Agent:
  - Reads review feedback
  - Reads current files from branch
  - Calls AI with fix instructions
  - Updates: src/auth/middleware.ts, src/auth/auth.service.ts
  - Posts: "[AI Fix Attempt 1/3] Updated 2 files. Please re-review."
         │
         ▼
Reviewer: "APPROVE — token validation now correct, refresh token implemented"
QA: "Tests pass ✅"
Security: "PASS"
         │
         ▼
Auto-merge → issue #5 done
```

---

## Phase 4: Release

After all desired issues are `done`:

```
Human: Actions → 🚀 Release → Run workflow
  version: 1.0.0
  environment: production
  dry_run: false
         │
         ▼
Release workflow:
  1. Validates version format (semver)
  2. Checks tag v1.0.0 doesn't exist
  3. Detects project type: nodejs
  4. npm ci && npm run build && npm test
  5. Creates git tag: v1.0.0
  6. Creates GitHub Release with changelog
  7. Runs .github/deploy.sh (if configured)
         │
         ▼
✅ Release v1.0.0 published
```

---

## State Transitions Summary

```
Issue lifecycle:
  Created manually → [ready] → [in-progress] → [review] → [done]
  Created by Planner → [draft] → (human approves) → [ready] → ...

PR lifecycle:
  [open]
    → [review comments] → Developer fixes → back to [open]
    → [approved by all agents] → auto-merge
    → [merged]
```

---

## Parallel Execution

Multiple issues can be implemented simultaneously. Each Developer Agent run
creates its own branch and PR, and the review agents process each PR independently.

There is no serialization requirement — the system scales horizontally with
GitHub Actions' concurrent job limit.

---

## Human Intervention Points

| Point | Action Required |
|-------|----------------|
| After bootstrap | Review `draft` issues, apply `ready` to approved ones |
| `needs-human` label | Fix loop exhausted — resolve PR manually |
| Release | Always manual via workflow_dispatch |
| Skip agents | Add `skip-ai-review`, `skip-qa`, or `skip-security` labels |
| Pause system | Disable workflows in Actions tab |
