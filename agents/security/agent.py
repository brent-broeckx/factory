#!/usr/bin/env python3
"""
Security Agent
==============
Triggered on every PR open/update.

1. Performs static pattern-matching for hardcoded secrets and credentials.
2. Uses an AI model to scan the diff for OWASP Top 10 vulnerabilities,
   injection risks, authentication flaws, and unsafe patterns.
3. Posts a structured security report as a PR comment.
4. Requests changes (blocks merge) on CRITICAL or HIGH severity findings,
   or if hardcoded secrets are detected.
"""

import os
import json
import sys
import re
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

# ── Secret detection patterns ─────────────────────────────────────────────────
# Each tuple: (regex_pattern, human_readable_description)
SECRET_PATTERNS: list[tuple[str, str]] = [
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\'][^"\']{4,}["\']',         "Hardcoded password"),
    (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\'][^"\']{8,}["\']',          "Hardcoded API key"),
    (r'(?i)(secret|token|auth)\s*[:=]\s*["\'][^"\']{8,}["\']',           "Hardcoded secret/token"),
    (r'(?i)(aws_access_key_id)\s*[:=]\s*["\']?[A-Z0-9]{20}["\']?',       "AWS Access Key ID"),
    (r'(?i)(aws_secret_access_key)\s*[:=]\s*["\']?[A-Za-z0-9/+=]{40}',   "AWS Secret Key"),
    (r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',                "Private key embedded"),
    (r'(?:eyJ[A-Za-z0-9_-]{10,}\.){2}[A-Za-z0-9_-]{10,}',               "JWT token in source"),
    (r'(?i)ghp_[A-Za-z0-9]{36}',                                          "GitHub Personal Access Token"),
    (r'(?i)sk-[A-Za-z0-9]{48}',                                           "OpenAI API key"),
]


def scan_patch_for_secrets(filename: str, patch: str) -> list[str]:
    """Scan added lines in a diff patch for secret patterns."""
    findings: list[str] = []
    added_lines = [
        line[1:]                             # strip leading '+'
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    for line in added_lines:
        for pattern, description in SECRET_PATTERNS:
            if re.search(pattern, line):
                safe_line = line.strip()[:100]
                findings.append(f"`{filename}`: {description} — `{safe_line}`")
                break  # one finding per line is enough
    return findings


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


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    pr = repo.get_pull(PR_NUMBER)
    print(f"🔒 Security Agent — PR #{PR_NUMBER}: {pr.title}")

    # ── Static secret scan ────────────────────────────────────────────────
    files = list(pr.get_files())
    secret_findings: list[str] = []
    diff_sections: list[str] = []

    for f in files[:20]:
        patch = f.patch or ""
        secret_findings.extend(scan_patch_for_secrets(f.filename, patch))
        diff_sections.append(
            f"### `{f.filename}` ({f.status}  +{f.additions}/-{f.deletions})\n"
            f"```diff\n{patch[:2500]}\n```"
        )

    diff_text = "\n\n".join(diff_sections)
    if len(files) > 20:
        diff_text += f"\n\n_… {len(files) - 20} more files not shown_"

    prescan_summary = (
        "\n".join(secret_findings)
        if secret_findings
        else "No obvious secrets detected in automated pre-scan."
    )

    # ── AI security analysis ──────────────────────────────────────────────
    system_prompt = load_prompt("security")
    user_message  = f"""## Security Review Request

**PR #{PR_NUMBER}:** {pr.title}
**Author:** @{pr.user.login}

## Static Pre-scan Results
{prescan_summary}

## Changed Files Diff
{diff_text}

## Instructions
Perform a thorough security review. Check for:
- OWASP Top 10 (injection, broken auth, sensitive data exposure, XXE, broken access control,
  security misconfiguration, XSS, insecure deserialization, known vulnerabilities, logging failures)
- Hardcoded credentials or secrets
- SSRF / CSRF vulnerabilities
- Unsafe use of cryptographic functions
- Input validation gaps
- Insecure direct object references
- Race conditions or time-of-check/time-of-use flaws

Return your response as a JSON object following the schema in your system prompt.
"""

    print("🤖 Calling AI security analyser…")
    raw = call_ai(system_prompt, user_message)

    try:
        result = extract_json(raw)
    except (json.JSONDecodeError, ValueError):
        result = {
            "severity":        "info",
            "summary":         raw[:1000],
            "vulnerabilities": [],
            "recommendations": [],
        }

    severity        = str(result.get("severity", "info")).lower()
    vulnerabilities = result.get("vulnerabilities", [])
    recommendations = result.get("recommendations", [])

    # Merge pre-scan secrets into vulnerabilities
    if secret_findings:
        vulnerabilities = [f"🔑 {f}" for f in secret_findings] + vulnerabilities

    # ── Build comment ─────────────────────────────────────────────────────
    severity_icons = {
        "critical": "🚨 CRITICAL",
        "high":     "❌ HIGH",
        "medium":   "⚠️ MEDIUM",
        "low":      "💡 LOW",
        "info":     "ℹ️ INFO",
        "pass":     "✅ PASS",
    }
    severity_label = severity_icons.get(severity, f"ℹ️ {severity.upper()}")

    vulns_md = "\n".join(f"- {v}" for v in vulnerabilities) or "✅ None found"
    recs_md  = "\n".join(f"- {r}" for r in recommendations) or "_None_"

    comment = f"""## 🔒 Security Review — {severity_label}

### Summary
{result.get('summary', '')}

### Vulnerabilities
{vulns_md}

### Recommendations
{recs_md}

---
*🤖 Generated by Security Agent · model: {AI_MODEL}*
"""

    pr.create_issue_comment(comment)

    # ── Block PR on critical/high or confirmed secrets ────────────────────
    should_block = severity in ("critical", "high") or bool(secret_findings)

    if should_block:
        try:
            pr.create_review(
                body=(
                    f"🚨 **Security issues detected (severity: {severity.upper()})**\n\n"
                    f"Please address all findings before merging."
                ),
                event="REQUEST_CHANGES",
            )
            print(f"  🚨 Security issues found — requested changes (severity: {severity})")
        except GithubException as exc:
            print(f"  ⚠️  Could not submit review: {exc}")
    else:
        print(f"  ✅ Security review complete (severity: {severity})")


if __name__ == "__main__":
    main()
