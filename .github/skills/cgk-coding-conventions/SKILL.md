---
name: cgk-coding-conventions
description: 'MANDATORY — Load and apply before writing, editing, planning, or reviewing any code. Defines structure, architecture, naming, error handling, quality, testing, git workflow, and modification rules. Must be loaded for every code-producing task without exception, including small changes, refactors, bug fixes, and scaffolding.'
---

# Coding Conventions

Shared coding principles for agents that produce code. Load and apply this checklist before writing production code.

## Mandatory Coding Principles

### 1. Structure and Architecture
- Use a consistent, predictable project layout with simple entry points.
- Group code by feature/screen; limit shared utilities to those used by at least two features.
- Prefer flat, explicit code over clever abstractions, metaprogramming, or deep hierarchies.
- Before scaffolding multiple files, identify shared structure and use framework-native composition patterns for repeated page or application elements.

### 2. Functions and Modules
- Keep control flow linear and easy to follow.
- Use small-to-medium functions with descriptive names.
- Pass state explicitly and avoid globals.
- Preserve the file's existing whitespace conventions; do not introduce mixed indentation within a block.
- Prefer reusing an existing named type over duplicating the same inline object shape in multiple places.

### 3. Errors, Logging, and Configuration
- Make errors explicit and informative.
- Emit structured logs at key boundaries.
- Prefer clear, declarative configuration such as JSON or YAML.

### 4. Modifications
- Follow existing patterns when extending or refactoring.
- Use precise edits for existing files to avoid overwriting unrelated work.
- Keep the change within the assigned phase unless correctness requires a narrow, explicit scope expansion.

### 5. Quality and Testing
- Favor deterministic, testable behavior with focused tests that verify observable outcomes.
- Do not leave empty, stub, or always-passing tests; remove template-generated test files after scaffolding.
- Add an integration-level check when changing startup, dependency injection, configuration loading, routing, or application composition.
- Use real or representative data when testing features that depend on manifests, copied assets, generated files, or production-like artifacts.
- **Quality over quantity.** Every test must justify its existence. Do not add tests just to increase count.
- Cosmetic or configuration-only changes (label text, button color, spacing) do not require new tests.
- Logic, state, or process changes require focused tests covering the observable outcome.
- Complex multi-step processes require multiple tests covering distinct paths and edge cases.
- Prefer one well-structured test that proves behavior over three shallow tests that prove nothing new.

### 6. Scaffolding Cleanup
- After using project templates, remove sample pages, sample models, default empty classes, default empty tests, and navigation references to deleted samples.
- Leave only framework infrastructure and empty-but-correct structure ready for feature development.

## Git Workflow Convention

All coding tasks follow a start/end commit pattern for clean diff boundaries:

1. **Start commit** — Before any code changes, create an empty marker commit: `chore: start <short-task-label>` (e.g., `chore: start fix-asset-card-overflow`).
2. **Code and validate** — Implement the change with iterative validation.
3. **End commit** — After all validation passes, create a summary commit. The message must be imperative mood, max 150 characters, describing what was done (e.g., `fix: prevent asset card text overflow on narrow viewports`).

Agents that manage branches or PRs extend this convention with their own branching and PR rules.

## Affected-Area Validation

After coding is complete, validate the areas affected by the change.

Rules:
- Build the affected app(s) and verify the build succeeds.
- Run the tests for the affected area(s) and verify they all pass.
- Do not run validation for untouched areas — efficiency matters.
- If changes span multiple areas, validate each affected area.
- All validation must pass before the end commit.

## Stack-Specific Conventions

These conventions are language-agnostic by default. When working on a specific project, also load the relevant stack-specific skill for deeper guidance.