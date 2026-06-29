---
name: cgk-code-quality-review
description: "Run a deep, periodic code-quality review of any codebase (TypeScript, C#, Python, Java, Go, etc.): find dead code, duplication clusters, god functions, split/scattered processes, magic numbers, SOLID/DRY violations, and OWASP-style security risks. USE FOR: 'deep code review', 'quality audit', 'find dead/duplicated code', 'should this be refactored', 'technical debt review', periodic health check. NOT for routine small edits (cgk-coding-conventions already covers those)."
user-invocable: true
---

# Code Quality Review

On-demand deep-review playbook for any language or technology stack. This is intentionally **not** an always-on instruction — load it only when doing a deliberate quality pass, so it costs no day-to-day context.

## Scope & Output

Produce findings, not silent edits. For each finding report: **location**, **category**, **why it matters**, **proposed fix**, **risk/effort**. Only implement fixes when the user asks, and respect in-progress (dirty/untracked) work — never bundle unrelated changes.

## Review Checklist

Walk the codebase against each category. Cluster related findings instead of listing every instance.

### 1. Dead code
- Files never imported (only self-references), unused exports, unreachable branches, commented-out blocks.
- Verify with a usage search before deleting; confirm no dynamic/string-based references.

### 2. Duplication clusters
- The same logic implemented in 2+ places. Extract a shared helper **only when used by ≥2 call sites**.
- Common offenders: recursive directory walkers, HTTP auth-header blocks, input sanitization/escaping, configuration reads, encoding/decoding utilities, error-mapping blocks.

### 3. God functions & scattered processes
- Functions doing many jobs (>~80 lines, multiple responsibilities, deep nesting). Extract named sub-steps.
- A single logical process split across files/handlers with no clear owner — consolidate behind one entry point.

### 4. Magic numbers & strings
- Inline literals (intervals, limits, config keys) that should be named constants or read through a single helper.

### 5. SOLID / DRY / abstractions
- Weak or leaky abstractions, near-duplicate types/shapes (prefer one named type), parameters that beg for a shared function (e.g. user vs admin variants).
- Prefer composition over inheritance where a class hierarchy exists only to share a few methods.

### 6. Security (OWASP Top 10)
- **Injection** (SQL, command, LDAP, template): every external input must be parameterized or properly escaped before use in a query, command, or template.
- **Broken access control**: verify authorization checks are present at every entry point, not just at the UI layer.
- **Sensitive data exposure**: no secrets, tokens, or PII written to logs, error messages, or version control.
- **Insecure deserialization**: untrusted payloads must be validated against a schema or type guard before use — never blindly cast or deserialize.
- **Security misconfiguration**: default credentials, debug endpoints, verbose error messages, or permissive CORS left in production code.
- **Vulnerable dependencies**: flag direct use of known-vulnerable library versions or patterns (e.g. `eval`, `dangerouslySetInnerHTML`, `Process.Start` with user input).

### 7. Tests & validation
- Logic changes covered by focused tests; no empty/always-pass tests; flag broken or stale test mocks.

## Procedure

1. Map entry points and module graph; flag files with no inbound imports or callers.
2. Search for repeated patterns (auth headers, config reads, input-sanitization blocks, encoding utilities, error mappers).
3. Rank findings by value: correctness/security > duplication that will drift > readability. Be token/agentic-aware — surface what truly matters, not nitpicks.
4. Report clustered findings with proposed fixes; implement only on request.
5. After any implemented fix, validate by running the project's standard build and test commands (check repo memory or `README` for the exact commands).

## Tracking the Refactor Backlog

Deferred findings (refactors not done during a scoped pass to avoid colliding with in-progress work) belong in **repository memory** (`/memories/repo/`), not in this skill — that keeps the skill reusable across projects while preserving project-specific context.

- At the start of a review, read repo memory for an existing refactor backlog and fold it into your findings.
- When you defer a refactor, append it to the repo's backlog note with: location, the duplication/complexity cluster, and the proposed fix.
- Remove items from the backlog once they are done.
