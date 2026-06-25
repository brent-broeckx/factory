#!/usr/bin/env python3
"""
QA Agent
========
Triggered on every PR open/update.

1. Detects the project type (Node.js, .NET, Python, static).
2. Installs dependencies and runs the existing test suite.
3. Uses AI to analyse test coverage gaps and quality issues.
4. Posts a structured report as a PR comment.
"""

import os
import json
import sys
import re
import subprocess
from pathlib import Path

from github import Github, GithubException
from openai import OpenAI

# ── Configuration ─────────────────────────────────────────────────────────────
GITHUB_TOKEN   = os.environ["GITHUB_TOKEN"]
AI_API_KEY     = os.environ["AI_API_KEY"]
AI_MODEL       = os.environ.get("AI_MODEL", "gpt-4o")
AI_BASE_URL    = os.environ.get("AI_BASE_URL", "https://api.openai.com/v1")
AI_MAX_TOKENS  = int(os.environ.get("AI_MAX_TOKENS", "4096"))
PR_NUMBER      = int(os.environ["PR_NUMBER"])
REPO_FULL_NAME = os.environ["REPO_FULL_NAME"]

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
    return json.loads(text.strip())


def run_command(cmd: str, timeout: int = 120) -> dict:
    """Run a shell command and capture output safely."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "Command timed out"}
    except Exception as exc:
        return {"returncode": -1, "stdout": "", "stderr": str(exc)}


def command_exists(cmd: str) -> bool:
    return run_command(f"which {cmd} 2>/dev/null")["returncode"] == 0


def detect_project() -> dict:
    """Detect project type and available test commands."""
    cwd = Path(".")
    info = {"type": "unknown", "test_commands": [], "has_tests": False}

    if (cwd / "package.json").exists():
        info["type"] = "nodejs"
        try:
            pkg = json.loads((cwd / "package.json").read_text())
            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                info["test_commands"] = [
                    "npm ci --prefer-offline --silent 2>/dev/null || npm install --silent",
                    "npm test -- --passWithNoTests --watchAll=false --forceExit",
                ]
                info["has_tests"] = True
        except Exception:
            pass

    elif list(cwd.glob("**/*.csproj")) or list(cwd.glob("**/*.fsproj")):
        info["type"] = "dotnet"
        if command_exists("dotnet"):
            info["test_commands"] = [
                "dotnet restore --nologo -q",
                "dotnet test --no-restore --verbosity normal",
            ]
            info["has_tests"] = True
        else:
            info["test_commands"] = []
            info["has_tests"] = False

    elif (cwd / "pyproject.toml").exists() or (cwd / "setup.py").exists() or (cwd / "requirements.txt").exists():
        info["type"] = "python"
        test_files = list(cwd.glob("**/test_*.py")) + list(cwd.glob("**/*_test.py"))
        if test_files:
            setup_cmd = ""
            if (cwd / "requirements.txt").exists():
                setup_cmd = "pip install -r requirements.txt -q && "
            info["test_commands"] = [
                f"{setup_cmd}python -m pytest --tb=short -q",
            ]
            info["has_tests"] = True

    elif (cwd / "Dockerfile").exists() or (cwd / "docker-compose.yml").exists():
        info["type"] = "docker"

    elif (cwd / "index.html").exists() or (cwd / "public").is_dir():
        info["type"] = "static"

    return info


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    pr = repo.get_pull(PR_NUMBER)
    print(f"🧪 QA Agent — PR #{PR_NUMBER}: {pr.title}")

    project = detect_project()
    print(f"   Project type: {project['type']}")

    # Run tests
    test_results: list[dict] = []
    overall_pass = True

    if project["has_tests"]:
        for cmd in project["test_commands"]:
            print(f"   Running: {cmd[:80]}…")
            result = run_command(cmd, timeout=180)
            passed = result["returncode"] == 0
            test_results.append({
                "command": cmd.split("&&")[-1].strip(),  # show final command
                "passed":  passed,
                "output":  (result["stdout"] + result["stderr"])[:2000],
            })
            if not passed:
                overall_pass = False
    else:
        print("   No runnable test suite detected")

    # Get changed files
    changed_files = [f.filename for f in pr.get_files()]

    # AI analysis
    system_prompt = load_prompt("qa")
    test_json     = json.dumps(test_results, indent=2) if test_results else "No tests were run."

    user_message = f"""## QA Analysis Request

**PR #{PR_NUMBER}:** {pr.title}
**Project type:** {project['type']}
**Overall test result:** {"PASS" if overall_pass else "FAIL"}

## Changed Files
{chr(10).join(f'- {p}' for p in changed_files[:30])}

## Test Results
```json
{test_json}
```

## Instructions
Analyse the test results and the list of changed files.
Identify: missing test coverage, untested edge cases, quality concerns.
Return your response as a JSON object following the schema in your system prompt.
"""

    print("🤖 Calling AI QA analyser…")
    raw = call_ai(system_prompt, user_message)

    try:
        qa = extract_json(raw)
    except (json.JSONDecodeError, ValueError):
        qa = {
            "passed":         overall_pass,
            "summary":        raw[:1000],
            "missing_tests":  [],
            "issues":         [],
        }

    # Build PR comment
    status_icon = "✅" if overall_pass else "❌"

    test_section_lines = []
    for tr in test_results:
        icon = "✅" if tr["passed"] else "❌"
        test_section_lines.append(
            f"\n**`{tr['command']}`** {icon}\n"
            f"```\n{tr['output'][:1500]}\n```"
        )
    test_section = (
        "".join(test_section_lines)
        if test_section_lines
        else "_No automated tests found or configured._"
    )

    missing_md = "\n".join(f"- {t}" for t in qa.get("missing_tests", [])) or "_None identified_"
    issues_md  = "\n".join(f"- ⚠️ {i}" for i in qa.get("issues",  []))  or "_None identified_"

    comment = f"""## 🧪 QA Report {status_icon}

**Project type:** `{project['type']}`

### Test Results
{test_section}

### AI Coverage Analysis
{qa.get('summary', '')}

### Missing Test Coverage
{missing_md}

### Quality Issues
{issues_md}

---
*🤖 Generated by QA Agent · model: {AI_MODEL}*
"""

    pr.create_issue_comment(comment)
    print(f"   {'✅ Tests passed' if overall_pass else '❌ Tests failed'}")


if __name__ == "__main__":
    main()
