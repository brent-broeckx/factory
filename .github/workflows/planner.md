---
name: 🧠 Planner — Decompose bootstrap issue into sub-issues
description: Reads a bootstrap issue and creates a set of independently implementable development sub-issues.
on:
  workflow_dispatch:
    inputs:
      issue_number:
        description: Number of the bootstrap issue
        type: string
        required: true
      issue_title:
        description: Title of the bootstrap issue
        type: string
        required: true
      issue_body:
        description: Full body text of the bootstrap issue
        type: string
        required: true
      issue_url:
        description: HTML URL of the bootstrap issue
        type: string
        required: true
      repo:
        description: Repository in OWNER/REPO format
        type: string
        required: true

permissions:
  contents: read
  copilot-requests: write
  issues: read
  pull-requests: read

concurrency:
  group: planner-${{ github.event.inputs.issue_number }}
  cancel-in-progress: false

checkout:
  fetch-depth: 1

tools:
  github:
    mode: gh-proxy
    toolsets: [default]

network:
  allowed:
    - defaults
    - github

safe-outputs:
  create-issue:
    labels: [draft, ai-generated]
    max: 20
  add-comment:
    max: 1
    target: "*"
  add-labels:
    allowed: [done]
    max: 1
    target: "*"
  remove-labels:
    allowed: [in-progress]
    max: 1
    target: "*"

strict: true
---

# Planner — Decompose Bootstrap Issue

You are a technical planning agent. Decompose the bootstrap issue below into a set of small, independently implementable development sub-issues. Do not write any code — planning only.

Only proceed with the workflow or run the workflow when the issue is labeled with label "bootstrap"

## Context

Bootstrap issue: **#${{ github.event.inputs.issue_number }}** — ${{ github.event.inputs.issue_title }}
Repository: `${{ github.event.inputs.repo }}`
Issue URL: ${{ github.event.inputs.issue_url }}

Issue body:
${{ github.event.inputs.issue_body }}

## Step 1 — Read project config

Run `cat config/project-config.yaml` and use the output to understand the tech stack, language, framework, test framework, and conventions. If those fields are empty, infer them from the issue body.

## Step 2 — Analyse the issue

Understand the project goal, implicit requirements, scale, and complexity from the issue title and body.

## Step 3 — Design an architecture

Design a full architecture for the project. Cover every area needed:

- Project scaffolding and repository setup
- Data models and schema (if applicable)
- Core business logic
- API or interface layer
- Authentication and authorization (if applicable)
- Testing setup
- CI/CD configuration
- Documentation

## Step 4 — Create sub-issues

Create between 5 and 20 sub-issues. Emit one `create_issue` safe output per issue.

**Rules:**
- Never create fewer than 5 issues.
- Each issue must be independently implementable with no hidden upstream dependencies.
- Prefer small, focused issues over large monolithic ones.
- The first issue must always be scaffolding or repository setup — it unblocks everything else.
- Write issue bodies in the same language as the bootstrap issue body.
- Every issue must be specific enough that an AI developer can implement it without asking clarifying questions — resolve all ambiguity now.
- Describe **what** to build and **why**. Do not prescribe how.

Each issue body must follow this exact template:

```
> Part of ${{ github.event.inputs.issue_url }}

## What to build
<description of what to implement and why>

## Technical notes
<constraints, decisions, and context from the architecture design>

## Acceptance Criteria
- [ ] <specific, testable criterion>
- [ ] Unit tests cover all public functions
- [ ] Error cases are handled correctly
```

Output format for each issue:

```json
{"type": "create_issue", "title": "<imperative title>", "body": "<body following the template above>"}
```

## Step 5 — Post a summary comment

Post one comment on the bootstrap issue summarising the plan. Target issue number `${{ github.event.inputs.issue_number }}`.

The comment must include:
- A paragraph summarising key architecture decisions made
- A numbered list of every created issue with its title and URL
- Any assumptions made that the human should review before applying `ready` labels
- Any open questions requiring human input

Output format:

```json
{"type": "add_comment", "issue_number": ${{ github.event.inputs.issue_number }}, "body": "<summary>"}
```

## Step 6 — Mark the bootstrap issue as done

Add `done` and remove `in-progress` on the bootstrap issue. Target issue number `${{ github.event.inputs.issue_number }}`.

Output format — emit both in sequence:

```json
{"type": "add_labels", "issue_number": ${{ github.event.inputs.issue_number }}, "labels": ["done"]}
{"type": "remove_labels", "issue_number": ${{ github.event.inputs.issue_number }}, "labels": ["in-progress"]}
```

## Safe Outputs

- Use `create_issue` for each sub-issue (5–20 total).
- Use `add_comment` to post the planning summary on the bootstrap issue.
- Use `add_labels` and `remove_labels` to transition the bootstrap issue from `in-progress` to `done`.
- Call `noop` only if the bootstrap issue body is clearly not a project description — explain why.
