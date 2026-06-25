#!/usr/bin/env python3
"""
Planner Agent
=============
Triggered when the 'bootstrap' label is applied to a GitHub issue.
Reads the issue, calls an AI model to decompose it into architecture,
epics, and sub-issues, then creates all sub-issues labeled 'draft'.

The human must manually change 'draft' → 'ready' to start development.
"""

import os
import json
import sys
import re
from pathlib import Path

from github import Github, GithubException
from openai import OpenAI

# ── Configuration from environment (set by the workflow) ─────────────────────
GITHUB_TOKEN   = os.environ["GITHUB_TOKEN"]
AI_API_KEY     = os.environ["AI_API_KEY"]
AI_MODEL       = os.environ.get("AI_MODEL", "gpt-4o")
AI_BASE_URL    = os.environ.get("AI_BASE_URL", "https://api.openai.com/v1")
AI_MAX_TOKENS  = int(os.environ.get("AI_MAX_TOKENS", "4096"))
ISSUE_NUMBER   = int(os.environ["ISSUE_NUMBER"])
REPO_FULL_NAME = os.environ["REPO_FULL_NAME"]

# ── Clients ───────────────────────────────────────────────────────────────────
g    = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_FULL_NAME)
ai   = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_prompt(name: str) -> str:
    """Load a prompt file from the prompts/ directory."""
    path = Path(f"prompts/{name}.prompt.md")
    if path.exists():
        return path.read_text(encoding="utf-8")
    print(f"⚠️  Prompt file not found: {path}. Using empty prompt.")
    return ""


def call_ai(system_prompt: str, user_message: str) -> str:
    """Call the configured AI model and return the response text."""
    response = ai.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        max_tokens=AI_MAX_TOKENS,
        temperature=0.1,
    )
    return response.choices[0].message.content


def extract_json(text: str) -> dict:
    """Extract a JSON object from an AI response that may contain markdown."""
    # Try fenced code block first
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        return json.loads(match.group(1))
    # Fallback: try the whole text as JSON
    return json.loads(text.strip())


def ensure_labels(label_names: list[str]) -> None:
    """Ensure each label exists in the repository, creating it if needed."""
    colors = {
        "bootstrap":      "e11d48",
        "draft":          "94a3b8",
        "ready":          "22c55e",
        "in-progress":    "f59e0b",
        "review":         "3b82f6",
        "done":           "6366f1",
        "ai-generated":   "8b5cf6",
        "needs-human":    "ef4444",
        "skip-ai-review": "64748b",
        "skip-qa":        "64748b",
        "skip-security":  "64748b",
    }
    existing = {lbl.name for lbl in repo.get_labels()}
    for name in label_names:
        if name not in existing:
            try:
                repo.create_label(name=name, color=colors.get(name, "cccccc"))
                print(f"  Created label: {name}")
            except GithubException:
                pass  # Race condition — another run created it first


def get_project_context() -> str:
    """Build a brief description of the repository's current structure."""
    try:
        contents = repo.get_contents("")
        if not isinstance(contents, list):
            contents = [contents]
        files = [c.name for c in contents if c.type == "file"]
        dirs  = [c.name for c in contents if c.type == "dir"]
        return (
            f"Root files      : {', '.join(files) or 'none'}\n"
            f"Root directories: {', '.join(dirs)  or 'none'}\n"
            f"Repository      : {REPO_FULL_NAME}\n"
            f"Default branch  : {repo.default_branch}"
        )
    except Exception:
        return f"Repository: {REPO_FULL_NAME}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"🧠 Planner Agent — issue #{ISSUE_NUMBER} in {REPO_FULL_NAME}")

    issue = repo.get_issue(ISSUE_NUMBER)
    print(f"   Title: {issue.title}")

    # Ensure all system labels exist
    ensure_labels([
        "bootstrap", "draft", "ready", "in-progress",
        "review", "done", "ai-generated", "needs-human",
    ])

    # Gather context
    project_context = get_project_context()

    system_prompt = load_prompt("planner")
    user_message  = f"""## Bootstrap Issue

**Title:** {issue.title}

**Description:**
{issue.body or '(no description provided)'}

## Current Repository Context
{project_context}

## Task
Analyse this request. Produce a structured development plan following the JSON schema
in your system prompt. Be specific and actionable. Each issue must be implementable
independently by an AI developer agent.
"""

    print("🤖 Calling AI planner…")
    raw = call_ai(system_prompt, user_message)

    try:
        plan = extract_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        error_msg = (
            f"⚠️ **Planner Agent Error**\n\n"
            f"Failed to parse the AI planning response.\n\n"
            f"```\n{exc}\n```\n\n"
            f"Please re-apply the `bootstrap` label to retry, or check the workflow logs."
        )
        issue.create_comment(error_msg)
        print(f"❌ JSON parse error: {exc}")
        sys.exit(1)

    # Create sub-issues
    created_issues: list = []
    epics = plan.get("epics", [])

    for epic in epics:
        epic_title = epic.get("title", "Untitled Epic")
        print(f"\n  📦 Epic: {epic_title}")

        for issue_def in epic.get("issues", []):
            title  = issue_def.get("title", "Untitled Issue")
            body   = issue_def.get("description", "")
            labels = list(set(issue_def.get("labels", []) + ["draft", "ai-generated"]))
            priority = issue_def.get("priority", "medium")
            acceptance = issue_def.get("acceptance_criteria", [])

            ensure_labels(labels)

            full_body = (
                f"{body}\n\n"
                f"---\n"
                f"**Epic:** {epic_title}  \n"
                f"**Priority:** {priority}  \n"
            )
            if acceptance:
                criteria = "\n".join(f"- [ ] {c}" for c in acceptance)
                full_body += f"\n**Acceptance Criteria:**\n{criteria}\n"
            full_body += f"\n*🤖 Auto-generated by Planner Agent from #{ISSUE_NUMBER}*"

            try:
                new_issue = repo.create_issue(
                    title=title,
                    body=full_body,
                    labels=labels,
                )
                created_issues.append(new_issue)
                print(f"    ✅ #{new_issue.number}: {title}")
            except GithubException as exc:
                print(f"    ❌ Failed to create '{title}': {exc}")

    # Post summary on bootstrap issue
    issue_links = "\n".join(
        f"- #{i.number} {i.title}" for i in created_issues
    )
    summary = f"""## 🧠 Planning Complete

{plan.get('summary', '')}

### Architecture Overview
{plan.get('architecture', '')}

### Generated Issues ({len(created_issues)} total)
{issue_links or '_No issues generated_'}

---

All issues have been created with the **`draft`** label and will **not** start development automatically.

**To begin development on any issue:**
1. Open the issue and review the description
2. Add the **`ready`** label when you approve it
3. The Developer Agent will automatically pick it up

*🤖 Generated by Planner Agent*
"""
    issue.create_comment(summary)
    issue.edit(state="closed")

    print(f"\n✅ Planning complete — {len(created_issues)} issues created.")


if __name__ == "__main__":
    main()
