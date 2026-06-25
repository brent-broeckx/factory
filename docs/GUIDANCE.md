# Guidance — Software Factory Template

This document explains how to set up, configure, and operate the Software Factory
after creating a repository from this template.

---

## 1. Create Your Repository

1. Navigate to the template on GitHub
2. Click **"Use this template"** → **"Create a new repository"**
3. Give it a name, choose visibility, click **Create repository**

> ⚠️ Do **not** clone or fork — use the template feature so you get a clean history.

---

## 2. Run Initial Setup

After your repo is created:

1. Go to **Actions** → **🔧 Initial Setup** → **Run workflow**
2. This creates all required labels in the correct colours
3. Read the workflow summary for the complete post-setup checklist

---

## 3. Configure Secrets and Variables

Navigate to **Settings → Secrets and variables → Actions**.

### Required Secrets

| Secret | Description |
|--------|-------------|
| `AI_API_KEY` | Your AI provider API key (OpenAI, Azure OpenAI, or any OpenAI-compatible API) |
| `DEPLOY_TOKEN` | *(Optional)* Credentials used by your custom deploy script |

### Optional Repository Variables

Override these to tune the system (Settings → Secrets and variables → Variables):

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_MODEL` | `gpt-4o` | AI model name. Use any OpenAI-compatible model name |
| `AI_BASE_URL` | `https://api.openai.com/v1` | API base URL. Change for Azure OpenAI or local models |
| `AI_MAX_TOKENS` | `4096` | Max tokens per AI call (developer agent uses 8192) |
| `MAX_FIX_ITERATIONS` | `3` | Max automated fix loops before requiring human review |
| `DEPLOY_ENABLED` | `false` | Set to `true` to enable automated deployment on release |

---

## 4. Configure Branch Protection

Navigate to **Settings → Branches → Add rule** for your default branch (`main`).

Enable:
- ✅ **Require a pull request before merging**
- ✅ **Require status checks to pass before merging**
  - Add: `AI Code Review`, `AI QA & Test Analysis`, `AI Security Scan`
- ✅ **Require branches to be up to date before merging**
- ✅ **Do not allow bypassing the above settings** *(recommended)*

### Enable Auto-Merge

Go to **Settings → General → Pull Requests** and enable:
- ✅ **Allow auto-merge**
- ✅ **Automatically delete head branches**

When all required status checks pass and the reviewer approves, GitHub will
automatically merge the PR without any further human action.

---

## 5. Set Workflow Permissions

Go to **Settings → Actions → General → Workflow permissions**:

- Select **"Read and write permissions"**
- Enable **"Allow GitHub Actions to create and approve pull requests"**

---

## 6. The Bootstrap Issue

The bootstrap issue is your first and only manual entry point into the AI planning system.

**How to use it:**

1. Create a new issue using the **Bootstrap** template
2. Describe your feature, application, or project in detail
3. Save the issue — nothing happens yet
4. Apply the **`bootstrap`** label to the issue
5. The Planner Agent triggers immediately

**What happens next:**

- The Planner Agent reads your issue
- Calls the AI to generate an architecture + epics + sub-issues
- Creates all sub-issues with the **`draft`** label
- Posts a summary comment on your bootstrap issue
- Closes the bootstrap issue

> 🔑 **Key design principle:** Generating `draft` issues does NOT start any development.
> Development only begins when YOU apply the `ready` label.

---

## 7. Reviewing and Approving Issues

After the Planner runs:

1. Go to the Issues tab — you'll see all generated issues with the `draft` label
2. Open each issue and review its description and acceptance criteria
3. If you're happy with it → add the **`ready`** label
4. If you want to modify it → edit the issue body first, then add `ready`
5. If you don't want it implemented → leave it as `draft` or close it

> 💡 You can approve multiple issues at once. Each will be picked up by a separate
> Developer Agent run.

---

## 8. How Agents are Triggered

| Event | Trigger | Agent |
|-------|---------|-------|
| Issue labeled `bootstrap` | issues: labeled | Planner |
| Issue labeled `ready` | issues: labeled | Developer |
| Human creates a new issue | issues: opened (not a bot, no `draft` label) | Auto-labeled `ready` → Developer |
| PR opened or updated | pull_request: opened, synchronize | Reviewer + QA + Security (in parallel) |
| Reviewer requests changes on AI PR | pull_request_review: submitted | Developer (fix loop) |
| PR merged | pull_request: closed + merged | Label manager marks issue as `done` |
| Release triggered | workflow_dispatch (manual) | Release workflow |

---

## 9. The Fix Loop

When the Reviewer, QA, or Security agent requests changes:

1. The Developer Agent automatically triggers
2. Reads all review feedback and inline comments
3. Fixes the issues and pushes to the same branch
4. Posts a `[AI Fix Attempt N/MAX]` comment
5. The reviewer agents trigger again on the new push

**Stop conditions:**
- All agents approve → auto-merge fires
- Fix attempts reach `MAX_FIX_ITERATIONS` → PR gets `needs-human` label, loop stops
- Human manually intervenes at any point

---

## 10. Direct Issues (No Bootstrap)

If you create a GitHub issue yourself (not through bootstrap):

- The label manager automatically applies the `ready` label
- The Developer Agent picks it up and implements it
- This is the fast path for single, well-defined tasks

> The bootstrap path is for large, multi-issue projects. The direct path is for
> individual, clearly-scoped tasks.

---

## 11. Cost Control Strategy

The system is designed to minimise unnecessary AI API calls:

| Safeguard | How it works |
|-----------|-------------|
| Human-gated start | Nothing runs until `ready` is applied |
| Draft buffer | Bootstrap issues stay `draft` — no cost until approved |
| Concurrency cancellation | Reviewer/QA/Security cancel previous runs on new pushes |
| Fix iteration cap | `MAX_FIX_ITERATIONS` prevents infinite loops |
| Token limits | `AI_MAX_TOKENS` caps spend per call |
| Skip labels | `skip-ai-review`, `skip-qa`, `skip-security` bypass agents on a PR |
| No polling | All agents are event-driven — zero cost when idle |

**Estimated token budget per issue (gpt-4o pricing):**
- Planner: ~4K tokens → ~$0.02
- Developer (implementation): ~8K tokens → ~$0.04
- Reviewer + QA + Security: ~3×4K = ~12K tokens → ~$0.06
- Developer fix (×MAX): up to 3×8K = ~24K tokens → ~$0.12
- **Total per issue: ~$0.24 worst case**

---

## 12. Pausing or Disabling the System

**Pause all agents:** Go to Actions tab → disable each workflow individually.

**Skip agents on a specific PR:** Add labels:
- `skip-ai-review` — bypass the Reviewer
- `skip-qa` — bypass QA
- `skip-security` — bypass Security

**Stop the fix loop on a PR:** Add `needs-human` label manually.

**Disable auto-ready for human issues:** Disable the `label-manager.yml` workflow.

---

## 13. Using Your Own AI Provider

The system uses any OpenAI-compatible API. Configure via repository variables:

| Provider | `AI_BASE_URL` | `AI_MODEL` |
|----------|--------------|-----------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| Azure OpenAI | `https://<resource>.openai.azure.com/openai/deployments/<deployment>` | `gpt-4o` |
| Ollama (local) | `http://localhost:11434/v1` | `llama3.1` |
| Together AI | `https://api.together.xyz/v1` | `meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo` |
| Anthropic (via proxy) | proxy URL | model name |

---

## 14. Release Process

Releases are **always manual**. To release:

1. Go to **Actions → 🚀 Release → Run workflow**
2. Enter the version (e.g. `1.2.3`)
3. Choose environment (`production` or `staging`)
4. Optionally enable **Dry Run** to validate without releasing
5. Click **Run workflow**

The release workflow auto-detects your project type and runs the appropriate build
pipeline. To add custom deployment, create `.github/deploy.sh` in your repo:

```bash
#!/bin/bash
VERSION=$1
ENVIRONMENT=$2
# your deploy commands here
```
