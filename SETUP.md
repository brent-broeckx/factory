# Setup

After creating a repo from this template, complete these steps once.

---

## 1. Run the setup workflow

Go to **[Actions → Initial Setup → Run workflow](../../actions/workflows/setup.yml)** and run it.

This creates all labels required by the pipeline.

---

## 2. Set workflow permissions

Go to **[Settings → Actions → General → Workflow permissions](../../settings/actions)**

- Select **Read and write permissions**
- Check **Allow GitHub Actions to create and approve pull requests**

---

## 3. Enable auto-merge

Go to **[Settings → General → Pull Requests](../../settings)**

- Check **Allow auto-merge**
- Check **Automatically delete head branches**

---

## 4. Configure branch protection for `main`

Go to **[Settings → Branches → Add rule](../../settings/branches)**

- Branch name pattern: `main`
- ✅ Require a pull request before merging
- ✅ Require approvals — set to **1**
- ✅ Require linear history
- ✅ Do not allow bypassing the above settings

---

## 5. Enable the Copilot coding agent

Go to **[Settings → Copilot](../../settings/copilot)** and enable the coding agent.

> If the option is missing, ask your org admin to allow it at **[Org → Settings → Copilot → Policies](https://github.com/organizations/_your_org_/settings/copilot/policies)**.

---

## 6. Configure your project

Edit `config/project-config.yaml` and fill in your tech stack, framework, and conventions. Copilot reads this before writing any code.

---

## Start building

Create an issue, describe what you want to build, and apply the `bootstrap` label to kick off the planner agent.

Once issues are generated and you apply `ready` to one, assign **`copilot-swe-agent[bot]`** to it in the GitHub UI — that starts the developer agent.

