# Setup Guide for Org Admins

This guide covers the one-time configuration an org admin must perform before teams
can use this template. No API keys or external secrets are required.

---

## Prerequisites

- GitHub Copilot Enterprise or Copilot Business subscription
- Org admin access to GitHub organization settings
- The coding agent feature enabled in your Copilot plan

---

## Step 1: Enable the Copilot coding agent at org level

1. Go to your **GitHub organization settings**
2. Navigate to **Copilot** → **Policies**
3. Under **Coding agent**, set the policy to **Allowed** (or **Allowed for specific repositories**)
4. Save changes

> Without this step, assigning issues to `copilot` will have no effect.

---

## Step 2: Enable the coding agent in the repository

After creating a repository from this template:

1. Go to the **repository Settings**
2. Navigate to **Copilot**
3. Enable **Copilot coding agent** for this repository

---

## Step 3: Set workflow permissions

1. Go to **Settings** → **Actions** → **General**
2. Under **Workflow permissions**, select **Read and write permissions**
3. Check **Allow GitHub Actions to create and approve pull requests**
4. Save

This allows the bootstrap and developer workflows to add labels, create assignees,
and the auto-merge workflow to merge PRs using `GITHUB_TOKEN`.

---

## Step 4: Enable auto-merge

1. Go to **Settings** → **General**
2. Scroll to **Pull Requests**
3. Check **Allow auto-merge**

The auto-merge workflow merges PRs automatically once all reviews are approved.

---

## Step 5: Configure branch protection for `main`

1. Go to **Settings** → **Branches** → **Add branch protection rule**
2. Branch name pattern: `main`
3. Recommended settings:
   - ✅ **Require a pull request before merging**
   - ✅ **Require approvals** (set to 1 — Copilot review counts)
   - ✅ **Require status checks to pass before merging**
   - ✅ **Do not allow bypassing the above settings**
4. Save changes

> With branch protection in place, the auto-merge workflow only fires after the
> Copilot review agents have approved the PR.

---

## Step 6: Run Initial Setup

1. Go to **Actions** → **Initial Setup** → **Run workflow**

This creates all required labels in the repository. Run it once after creating
the repository from the template.

---

## No secrets required

This template uses only the built-in `GITHUB_TOKEN`. There are no external API keys,
model endpoints, or third-party secrets to configure.

| Old variable | Status |
|--------------|--------|
| `AI_API_KEY` | Not needed — removed |
| `AI_MODEL` | Not needed — removed |
| `AI_BASE_URL` | Not needed — removed |
| `AI_MAX_TOKENS` | Not needed — removed |

---

## Customising the review agents

The three review agents are defined in `.github/agents/`:

| File | Agent | What it reviews |
|------|-------|----------------|
| `security.agent.md` | Security reviewer | OWASP Top 10, secrets, injection |
| `qa.agent.md` | QA reviewer | Test coverage, requirement correctness |
| `code-quality.agent.md` | Code quality reviewer | Readability, architecture, docs |

To customise an agent:
1. Open the relevant `.agent.md` file
2. Edit the review criteria or output format sections
3. Commit to `main` — the changes take effect on the next PR

---

## Configuring a new project

After creating a repository from this template, the team should fill in
`config/project-config.yaml` with their project's specifics:

```yaml
project:
  name: "My App"
  description: "A REST API for task management"

tech_stack:
  language: "TypeScript"
  framework: "Express"
  database: "PostgreSQL"
  runtime: "Node.js 20"
  package_manager: "npm"

conventions:
  branch_prefix: "feat"
  test_framework: "Jest"
  lint_tool: "ESLint"
```

Copilot reads this file before implementing any issue to ensure it follows the
correct stack and conventions.

---

## Troubleshooting

**Issue assigned to Copilot but nothing happens**
- Confirm the coding agent policy is enabled at org level (Step 1)
- Confirm the coding agent is enabled in the repository (Step 2)
- Check the repository's Copilot settings page for any error messages

**Workflow fails with permission error**
- Check Step 3 — workflow permissions must be set to read and write

**Auto-merge not firing**
- Check Step 4 — auto-merge must be enabled in repo settings
- Confirm branch protection requires at least one approval (Step 5)
- Check that the Copilot review has submitted an APPROVED verdict
