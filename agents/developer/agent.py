#!/usr/bin/env python3
"""
Developer Agent
===============
Handles two triggers:

  1. issues event (label=ready)   → implement the issue from scratch
  2. pull_request_review event    → fix reviewer/QA/security comments on an
                                    existing AI-generated PR

In both cases the agent calls an AI model, receives a structured JSON response
containing file paths and contents, and commits those files to GitHub via the
REST API (no local git operations required).

Cost control: the MAX_FIX_ITERATIONS env var caps the number of automated
fix loops. Once exceeded, the agent adds a 'needs-human' label and stops.
"""

import os
import json
import sys
import re
import base64
from pathlib import Path

from github import Github, GithubException
from openai import OpenAI

# ── Configuration ─────────────────────────────────────────────────────────────
GITHUB_TOKEN      = os.environ["GITHUB_TOKEN"]
AI_API_KEY        = os.environ["AI_API_KEY"]
AI_MODEL          = os.environ.get("AI_MODEL", "gpt-4o")
AI_BASE_URL       = os.environ.get("AI_BASE_URL", "https://api.openai.com/v1")
AI_MAX_TOKENS     = int(os.environ.get("AI_MAX_TOKENS", "8192"))
TRIGGER_EVENT     = os.environ.get("TRIGGER_EVENT", "issues")
ISSUE_NUMBER      = os.environ.get("ISSUE_NUMBER", "")
PR_NUMBER         = os.environ.get("PR_NUMBER", "")
REPO_FULL_NAME    = os.environ["REPO_FULL_NAME"]
MAX_FIX_ITERATIONS = int(os.environ.get("MAX_FIX_ITERATIONS", "3"))

# ── Clients ───────────────────────────────────────────────────────────────────
g    = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_FULL_NAME)
ai   = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_prompt(name: str) -> str:
    path = Path(f"prompts/{name}.prompt.md")
    return path.read_text(encoding="utf-8") if path.exists() else ""


def call_ai(system_prompt: str, user_message: str) -> str:
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
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        return json.loads(match.group(1))
    # Try raw text
    return json.loads(text.strip())


def ensure_label(name: str, color: str = "cccccc") -> None:
    try:
        repo.get_label(name)
    except GithubException:
        try:
            repo.create_label(name=name, color=color)
        except GithubException:
            pass


def get_file_from_branch(path: str, branch: str) -> str | None:
    """Return decoded file content from a specific branch, or None."""
    try:
        obj = repo.get_contents(path, ref=branch)
        if isinstance(obj, list):
            return None
        return base64.b64decode(obj.content).decode("utf-8", errors="replace")[:6000]
    except Exception:
        return None


def write_file_to_branch(path: str, content: str, message: str, branch: str) -> bool:
    """Create or update a file on a branch via the GitHub API."""
    try:
        try:
            existing = repo.get_contents(path, ref=branch)
            repo.update_file(
                path=path,
                message=message,
                content=content,
                sha=existing.sha,
                branch=branch,
            )
        except GithubException:
            repo.create_file(
                path=path,
                message=message,
                content=content,
                branch=branch,
            )
        return True
    except GithubException as exc:
        print(f"  ⚠️  Could not write {path}: {exc}")
        return False


def get_repo_structure(max_items: int = 80) -> str:
    """Return a flat text representation of the repository tree."""
    lines: list[str] = []

    def walk(path: str = "", depth: int = 0) -> None:
        if depth > 3 or len(lines) >= max_items:
            return
        try:
            items = repo.get_contents(path)
            if not isinstance(items, list):
                items = [items]
            for item in sorted(items, key=lambda x: (x.type == "file", x.name)):
                if item.name.startswith(".") and depth == 0:
                    continue  # skip dot-dirs at root (e.g. .git)
                indent = "  " * depth
                if item.type == "dir":
                    lines.append(f"{indent}{item.name}/")
                    walk(item.path, depth + 1)
                else:
                    lines.append(f"{indent}{item.name}")
        except Exception:
            pass

    walk()
    return "\n".join(lines)


def count_fix_attempts(pr) -> int:
    """Count previous AI fix attempts by scanning PR comments."""
    return sum(
        1 for c in pr.get_issue_comments()
        if "[AI Fix Attempt" in c.body
    )


def extract_linked_issue(pr) -> int | None:
    """Parse 'Resolves #N' from PR body to find the linked issue number."""
    if not pr.body:
        return None
    m = re.search(r"(?:Resolves|Closes|Fixes)\s+#(\d+)", pr.body, re.IGNORECASE)
    return int(m.group(1)) if m else None


# ── Implement from issue ──────────────────────────────────────────────────────

def implement_from_issue() -> None:
    issue_num = int(ISSUE_NUMBER)
    issue     = repo.get_issue(issue_num)
    print(f"🛠️  Implementing issue #{issue_num}: {issue.title}")

    # Transition labels: ready → in-progress
    ensure_label("in-progress", "f59e0b")
    ensure_label("review",      "3b82f6")
    ensure_label("ai-generated","8b5cf6")
    try:
        issue.remove_from_labels("ready")
    except GithubException:
        pass
    issue.add_to_labels("in-progress")

    # Gather context
    repo_structure = get_repo_structure()
    config_content = get_file_from_branch("config/project-config.yaml", repo.default_branch) or ""
    readme_content = (get_file_from_branch("README.md", repo.default_branch) or "")[:2000]

    system_prompt = load_prompt("developer")
    user_message  = f"""## Issue to Implement

**Issue #{issue_num}:** {issue.title}

**Description:**
{issue.body or '(no description)'}

## Repository Structure
```
{repo_structure}
```

## project-config.yaml
```yaml
{config_content}
```

## README (excerpt)
{readme_content}

## Instructions
Implement this issue completely. Return a JSON object following the schema in your system prompt.
- Use branch name: feature/issue-{issue_num}-<short-slug>
- Include all files needed to make this feature work
- Write tests for new code
- Fill in pr_body with a clear description and "Resolves #{issue_num}"
"""

    print("🤖 Calling AI developer…")
    raw = call_ai(system_prompt, user_message)

    try:
        impl = extract_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        issue.create_comment(
            f"❌ **Developer Agent Error**\n\nFailed to parse AI response.\n\n```\n{exc}\n```"
        )
        try:
            issue.remove_from_labels("in-progress")
        except GithubException:
            pass
        ensure_label("needs-human", "ef4444")
        issue.add_to_labels("needs-human")
        sys.exit(1)

    branch_name    = impl.get("branch_name",    f"feature/issue-{issue_num}-implementation")
    commit_message = impl.get("commit_message", f"feat: implement issue #{issue_num}")
    files          = impl.get("files",          [])
    pr_title       = impl.get("pr_title",       f"feat: {issue.title}")
    pr_body        = impl.get("pr_body",        f"Resolves #{issue_num}")

    if not files:
        issue.create_comment("❌ **Developer Agent Error**\n\nAI returned no files to create.")
        sys.exit(1)

    # Create branch from default
    base_sha = repo.get_branch(repo.default_branch).commit.sha
    try:
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
        print(f"  ✅ Created branch: {branch_name}")
    except GithubException as exc:
        if "Reference already exists" not in str(exc):
            print(f"  ❌ Could not create branch: {exc}")
            sys.exit(1)

    # Write files
    written = 0
    for fdef in files:
        fpath    = fdef.get("path", "")
        fcontent = fdef.get("content", "")
        if not fpath or not fcontent:
            continue
        if write_file_to_branch(fpath, fcontent, f"{commit_message}", branch_name):
            written += 1
            print(f"  ✅ {fpath}")

    print(f"  Written {written}/{len(files)} files")

    if written == 0:
        issue.create_comment("❌ **Developer Agent Error**\n\nNo files were written successfully.")
        sys.exit(1)

    # Create PR
    try:
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=repo.default_branch,
        )
        print(f"  ✅ Created PR #{pr.number}: {pr_title}")

        # Label the PR as ai-generated (enables fix loop)
        pr_issue = repo.get_issue(pr.number)
        pr_issue.add_to_labels("ai-generated")

    except GithubException as exc:
        print(f"  ❌ Could not create PR: {exc}")
        sys.exit(1)

    # Transition issue: in-progress → review
    try:
        issue.remove_from_labels("in-progress")
    except GithubException:
        pass
    issue.add_to_labels("review")


# ── Fix review comments ───────────────────────────────────────────────────────

def fix_from_review() -> None:
    pr_num = int(PR_NUMBER)
    pr     = repo.get_pull(pr_num)
    print(f"🔧 Fixing review comments on PR #{pr_num}: {pr.title}")

    # Enforce cost cap
    fix_count = count_fix_attempts(pr)
    if fix_count >= MAX_FIX_ITERATIONS:
        pr.create_issue_comment(
            f"⚠️ **Maximum fix attempts reached ({fix_count}/{MAX_FIX_ITERATIONS})**\n\n"
            f"This PR has had {MAX_FIX_ITERATIONS} automated fix attempts. "
            f"Human review is required to proceed.\n\n"
            f"Please resolve the remaining issues manually, or close and re-open the PR."
        )
        ensure_label("needs-human", "ef4444")
        issue_num = extract_linked_issue(pr)
        if issue_num:
            try:
                linked = repo.get_issue(issue_num)
                linked.add_to_labels("needs-human")
            except GithubException:
                pass
        return

    # Collect review feedback
    reviews  = list(pr.get_reviews())
    cr_reviews = [r for r in reviews if r.state == "CHANGES_REQUESTED"]
    if not cr_reviews:
        print("  No changes_requested reviews found — skipping")
        return

    review_feedback = "\n\n".join(
        f"**Review by @{r.user.login}:**\n{r.body}" for r in cr_reviews if r.body
    )
    inline_comments = "\n\n".join(
        f"**`{c.path}` (line {c.position}):** {c.body}"
        for c in pr.get_review_comments()
    )

    # Read current files from branch
    branch = pr.head.ref
    changed_files = {f.filename: get_file_from_branch(f.filename, branch)
                     for f in pr.get_files()}
    current_files_json = json.dumps(
        {k: v for k, v in changed_files.items() if v is not None},
        indent=2,
    )

    system_prompt = load_prompt("developer")
    user_message  = f"""## Fix Review Comments

**PR #{pr_num}:** {pr.title}
**Branch:** {branch}
**Fix attempt:** {fix_count + 1} of {MAX_FIX_ITERATIONS}

## Review Feedback
{review_feedback or '(no summary review body)'}

## Inline Comments
{inline_comments or '(no inline comments)'}

## Current File Contents (excerpt)
```json
{current_files_json[:6000]}
```

## Instructions
Fix ALL issues identified in the review feedback and inline comments.
Return a JSON object with ONLY the files that need to change.
Use the same branch_name: {branch}
"""

    print("🤖 Calling AI for fix…")
    raw = call_ai(system_prompt, user_message)

    try:
        fix = extract_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        pr.create_issue_comment(
            f"❌ **Developer Agent Error**\n\nFailed to parse fix response.\n\n```\n{exc}\n```"
        )
        return

    files = fix.get("files", [])
    written = 0
    for fdef in files:
        fpath    = fdef.get("path", "")
        fcontent = fdef.get("content", "")
        if not fpath or not fcontent:
            continue
        if write_file_to_branch(fpath, fcontent, f"fix: address review comments — {fpath}", branch):
            written += 1
            print(f"  ✅ Fixed: {fpath}")

    pr.create_issue_comment(
        f"[AI Fix Attempt {fix_count + 1}/{MAX_FIX_ITERATIONS}]\n\n"
        f"🔧 **Developer Agent** has addressed the review feedback.\n\n"
        f"Updated **{written}** file(s). Please re-review."
    )
    print(f"  ✅ Fix complete — {written} files updated")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if TRIGGER_EVENT == "issues" and ISSUE_NUMBER:
        implement_from_issue()
    elif TRIGGER_EVENT == "pull_request_review" and PR_NUMBER:
        fix_from_review()
    else:
        print(
            f"⚠️  Unexpected trigger configuration:\n"
            f"   TRIGGER_EVENT={TRIGGER_EVENT!r}\n"
            f"   ISSUE_NUMBER={ISSUE_NUMBER!r}\n"
            f"   PR_NUMBER={PR_NUMBER!r}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
