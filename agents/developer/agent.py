#!/usr/bin/env python3
"""
Developer Agent
===============
Uses an agentic tool-calling loop (same model as GitHub Copilot agent mode).

Before writing a single line of code the agent explores the repository using
three read-only tools:

  search_files(pattern)   → find files by path/name fragment
  read_file(path)         → read a file's full content from the repo
  list_directory(path)    → list items inside a directory

Once it understands the existing code it calls the terminal tool:

  write_implementation(…) → create/update files and open a PR

The loop is capped at MAX_TOOL_CALLS per run to control costs.

Triggers:
  issues event (label=ready)        → implement a new issue
  pull_request_review event         → fix reviewer/QA/security comments
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
GITHUB_TOKEN       = os.environ["GITHUB_TOKEN"]
AI_API_KEY         = os.environ["AI_API_KEY"]
AI_MODEL           = os.environ.get("AI_MODEL", "gpt-4o")
AI_BASE_URL        = os.environ.get("AI_BASE_URL", "https://api.openai.com/v1")
AI_MAX_TOKENS      = int(os.environ.get("AI_MAX_TOKENS", "8192"))
TRIGGER_EVENT      = os.environ.get("TRIGGER_EVENT", "issues")
ISSUE_NUMBER       = os.environ.get("ISSUE_NUMBER", "")
PR_NUMBER          = os.environ.get("PR_NUMBER", "")
REPO_FULL_NAME     = os.environ["REPO_FULL_NAME"]
MAX_FIX_ITERATIONS = int(os.environ.get("MAX_FIX_ITERATIONS", "3"))

# Max tool calls per agent run — prevents runaway costs
# Each read_file / search_files call counts toward this limit
MAX_TOOL_CALLS = int(os.environ.get("MAX_TOOL_CALLS", "20"))

# ── Clients ───────────────────────────────────────────────────────────────────
g    = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_FULL_NAME)
ai   = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)


# ── Tool schema (OpenAI function-calling format) ──────────────────────────────

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": (
                "Search for files in the repository whose path contains a given substring. "
                "Use this to locate relevant files before reading them. "
                "Returns a list of matching paths."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Case-insensitive substring to match against file paths "
                                       "(e.g. 'index.html', 'auth', 'routes').",
                    }
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the full content of a file from the repository. "
                "Always read a file before modifying it so you understand its current state. "
                "Returns the file content as plain text."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to the repository root (e.g. 'src/index.html').",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": (
                "List files and subdirectories inside a directory. "
                "Use '' (empty string) to list the repository root."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to repository root. Empty string for root.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_implementation",
            "description": (
                "Write the complete implementation. Call this ONLY after you have finished "
                "reading all relevant files and are certain what needs to be created or changed. "
                "This creates/updates files on a branch and opens a pull request."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "branch_name": {
                        "type": "string",
                        "description": "Branch name e.g. feature/issue-42-add-auth",
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Git commit message",
                    },
                    "pr_title": {
                        "type": "string",
                        "description": "Pull request title",
                    },
                    "pr_body": {
                        "type": "string",
                        "description": "Pull request body. Must end with 'Resolves #N'.",
                    },
                    "files": {
                        "type": "array",
                        "description": "Complete list of files to create or update.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "File path relative to repository root",
                                },
                                "content": {
                                    "type": "string",
                                    "description": "Complete file content",
                                },
                            },
                            "required": ["path", "content"],
                        },
                    },
                },
                "required": ["branch_name", "commit_message", "pr_title", "pr_body", "files"],
            },
        },
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_prompt(name: str) -> str:
    path = Path(f"prompts/{name}.prompt.md")
    return path.read_text(encoding="utf-8") if path.exists() else ""


def ensure_label(name: str, color: str = "cccccc") -> None:
    try:
        repo.get_label(name)
    except GithubException:
        try:
            repo.create_label(name=name, color=color)
        except GithubException:
            pass


def get_file_from_branch(path: str, branch: str) -> str | None:
    """Return decoded file content from a branch, or None."""
    try:
        obj = repo.get_contents(path, ref=branch)
        if isinstance(obj, list):
            return None
        return base64.b64decode(obj.content).decode("utf-8", errors="replace")
    except Exception:
        return None


def write_file_to_branch(path: str, content: str, message: str, branch: str) -> bool:
    """Create or update a file on a branch via the GitHub contents API."""
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


# Directories excluded from the file tree shown to the developer AI
_SKIP_DIRS = {
    ".github", "agents", "prompts", "docs", "templates",
    "node_modules", ".git", "dist", "build", "out",
    "__pycache__", ".venv", "venv", ".next", ".nuxt",
    "bin", "obj", ".mypy_cache", ".pytest_cache",
}


def get_repo_file_tree() -> list[str]:
    """Return a flat list of every file path in the repository (excluding noise dirs)."""
    paths: list[str] = []

    def walk(path: str = "", depth: int = 0) -> None:
        if depth > 6:
            return
        try:
            items = repo.get_contents(path)
            if not isinstance(items, list):
                items = [items]
            for item in items:
                if item.type == "dir":
                    if item.name.lower() not in _SKIP_DIRS and not item.name.startswith("."):
                        walk(item.path, depth + 1)
                else:
                    paths.append(item.path)
        except Exception:
            pass

    walk()
    return paths


# ── Tool execution ────────────────────────────────────────────────────────────

def tool_search_files(pattern: str, file_tree: list[str]) -> str:
    pat = pattern.lower()
    matches = [p for p in file_tree if pat in p.lower()]
    if not matches:
        return f"No files found matching '{pattern}'."
    return "\n".join(matches[:50])


def tool_read_file(path: str, branch: str) -> str:
    content = get_file_from_branch(path, branch)
    if content is None:
        return f"File not found or could not be read: {path}"
    # Cap per-file content to stay within token budget
    if len(content) > 8000:
        return content[:8000] + f"\n\n… (file truncated at 8000 chars; full length: {len(content)})"
    return content


def tool_list_directory(path: str) -> str:
    try:
        items = repo.get_contents(path if path else "")
        if not isinstance(items, list):
            items = [items]
        lines = []
        for item in sorted(items, key=lambda x: (x.type == "file", x.name)):
            icon = "📁 " if item.type == "dir" else "📄 "
            lines.append(f"{icon}{item.name}")
        return "\n".join(lines) if lines else "(empty directory)"
    except Exception as exc:
        return f"Could not list '{path}': {exc}"


def dispatch_tool(tool_name: str, args: dict, branch: str, file_tree: list[str]) -> str:
    """Run a read-only tool and return its output as a string."""
    if tool_name == "search_files":
        return tool_search_files(args.get("pattern", ""), file_tree)
    elif tool_name == "read_file":
        return tool_read_file(args.get("path", ""), branch)
    elif tool_name == "list_directory":
        return tool_list_directory(args.get("path", ""))
    else:
        return f"Unknown tool: {tool_name}"


# ── Agentic tool-calling loop ─────────────────────────────────────────────────

def run_agent_loop(
    system_prompt: str,
    initial_user_message: str,
    branch: str,
    file_tree: list[str],
) -> dict | None:
    """
    Run the OpenAI tool-calling loop.

    The AI freely calls search_files / read_file / list_directory to explore
    the repository, building up its understanding of the codebase.  When ready
    it calls write_implementation, which terminates the loop.

    Returns the write_implementation args dict, or None on error.
    """
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": initial_user_message},
    ]
    tool_calls_made = 0

    while tool_calls_made < MAX_TOOL_CALLS:
        response = ai.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=AI_MAX_TOKENS,
            temperature=0.1,
        )

        choice  = response.choices[0]
        message = choice.message

        # Persist assistant turn
        msg_dict: dict = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ]
        messages.append(msg_dict)

        # No tool calls — AI finished without writing
        if not message.tool_calls or choice.finish_reason == "stop":
            print("  ℹ️  Agent finished without calling write_implementation")
            return None

        # Process each tool call in this turn
        terminal_result: dict | None = None

        for tc in message.tool_calls:
            tool_name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            tool_calls_made += 1
            print(f"  🔧 [{tool_calls_made}/{MAX_TOOL_CALLS}] {tool_name}({list(args.keys())})")

            if tool_name == "write_implementation":
                terminal_result = args
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      "Implementation accepted.",
                })
            else:
                result = dispatch_tool(tool_name, args, branch, file_tree)
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      result,
                })

        if terminal_result is not None:
            return terminal_result

    print(f"  ⚠️  Tool call limit reached ({MAX_TOOL_CALLS})")
    return None


# ── Linked issue helpers ──────────────────────────────────────────────────────

def count_fix_attempts(pr) -> int:
    return sum(1 for c in pr.get_issue_comments() if "[AI Fix Attempt" in c.body)


def extract_linked_issue(pr) -> int | None:
    if not pr.body:
        return None
    m = re.search(r"(?:Resolves|Closes|Fixes)\s+#(\d+)", pr.body, re.IGNORECASE)
    return int(m.group(1)) if m else None


# ── Implement from issue ──────────────────────────────────────────────────────

def implement_from_issue() -> None:
    issue_num = int(ISSUE_NUMBER)
    issue     = repo.get_issue(issue_num)
    print(f"🛠️  Implementing issue #{issue_num}: {issue.title}")

    ensure_label("in-progress", "f59e0b")
    ensure_label("review",      "3b82f6")
    ensure_label("ai-generated","8b5cf6")
    try:
        issue.remove_from_labels("ready")
    except GithubException:
        pass
    issue.add_to_labels("in-progress")

    print("  📂 Building repository file tree…")
    file_tree      = get_repo_file_tree()
    tree_text      = "\n".join(file_tree) if file_tree else "(empty repository)"
    config_content = get_file_from_branch("config/project-config.yaml", repo.default_branch) or ""

    system_prompt   = load_prompt("developer")
    initial_message = f"""## Issue to Implement

**Issue #{issue_num}:** {issue.title}

**Description:**
{issue.body or '(no description)'}

## Repository File Tree
```
{tree_text}
```

## project-config.yaml
```yaml
{config_content}
```

## Instructions
You are working on a real codebase. Use the available tools to explore it before writing anything:

1. Call `list_directory` on relevant directories to understand the structure
2. Call `search_files` to find files related to this feature (e.g. search 'index', 'main', 'app', or the feature name)
3. Call `read_file` on every file you need to understand or modify — especially existing files your new code must integrate with (HTML files that need a new script tag, config files, entry points, etc.)
4. When you fully understand the existing code, call `write_implementation` with the complete set of files to create or update

Rules:
- Use branch name: feature/issue-{issue_num}-<short-slug>
- The pr_body must end with: Resolves #{issue_num}
- When updating an existing file, include its COMPLETE new content
- When adding a JS file that an HTML page loads, you MUST read that HTML file first and return the updated HTML with the correct script tag
"""

    print("🤖 Starting agentic implementation loop…")
    impl = run_agent_loop(
        system_prompt=system_prompt,
        initial_user_message=initial_message,
        branch=repo.default_branch,
        file_tree=file_tree,
    )

    if not impl:
        issue.create_comment(
            "❌ **Developer Agent Error**\n\n"
            "The agent did not produce an implementation. "
            "Check the workflow logs for details."
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

    # Create branch from default branch HEAD
    base_sha = repo.get_branch(repo.default_branch).commit.sha
    try:
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
        print(f"  ✅ Created branch: {branch_name}")
    except GithubException as exc:
        if "Reference already exists" not in str(exc):
            print(f"  ❌ Could not create branch: {exc}")
            sys.exit(1)

    written = 0
    for fdef in files:
        fpath    = fdef.get("path", "")
        fcontent = fdef.get("content", "")
        if not fpath or not fcontent:
            continue
        if write_file_to_branch(fpath, fcontent, commit_message, branch_name):
            written += 1
            print(f"  ✅ {fpath}")

    print(f"  Written {written}/{len(files)} files")

    if written == 0:
        issue.create_comment("❌ **Developer Agent Error**\n\nNo files were written successfully.")
        sys.exit(1)

    try:
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=repo.default_branch,
        )
        print(f"  ✅ Created PR #{pr.number}: {pr_title}")
        repo.get_issue(pr.number).add_to_labels("ai-generated")
    except GithubException as exc:
        print(f"  ❌ Could not create PR: {exc}")
        sys.exit(1)

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

    fix_count = count_fix_attempts(pr)
    if fix_count >= MAX_FIX_ITERATIONS:
        pr.create_issue_comment(
            f"⚠️ **Maximum fix attempts reached ({fix_count}/{MAX_FIX_ITERATIONS})**\n\n"
            f"Human review is required to proceed."
        )
        ensure_label("needs-human", "ef4444")
        issue_num = extract_linked_issue(pr)
        if issue_num:
            try:
                repo.get_issue(issue_num).add_to_labels("needs-human")
            except GithubException:
                pass
        return

    cr_reviews = [r for r in pr.get_reviews() if r.state == "CHANGES_REQUESTED"]
    if not cr_reviews:
        print("  No changes_requested reviews found — skipping")
        return

    review_feedback = "\n\n".join(
        f"**Review by @{r.user.login}:**\n{r.body}" for r in cr_reviews if r.body
    )
    inline_comments = "\n\n".join(
        f"**`{c.path}` line {c.position}:** {c.body}"
        for c in pr.get_review_comments()
    )

    branch    = pr.head.ref
    file_tree = [f.filename for f in pr.get_files()]

    system_prompt   = load_prompt("developer")
    initial_message = f"""## Fix Review Comments

**PR #{pr_num}:** {pr.title}
**Branch:** {branch}
**Fix attempt:** {fix_count + 1} of {MAX_FIX_ITERATIONS}

## Review Feedback
{review_feedback or '(no summary review body)'}

## Inline Review Comments
{inline_comments or '(no inline comments)'}

## Files Changed in This PR
```
{chr(10).join(file_tree)}
```

## Instructions
1. Use `read_file` to read every file that has review comments or needs to change
2. Use `search_files` or `list_directory` if you need surrounding context
3. When you understand all the fixes, call `write_implementation` with ONLY the files that changed
4. Use branch_name: {branch}
5. Leave pr_body as an empty string (no new PR is opened for fix pushes)
"""

    print("🤖 Starting agentic fix loop…")
    fix = run_agent_loop(
        system_prompt=system_prompt,
        initial_user_message=initial_message,
        branch=branch,
        file_tree=file_tree,
    )

    if not fix:
        pr.create_issue_comment(
            "❌ **Developer Agent Error**\n\nAgent did not produce any fixes. Check workflow logs."
        )
        return

    files   = fix.get("files", [])
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
