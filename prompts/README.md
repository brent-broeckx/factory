# Prompts → Migrated to `.github/agents/`

The system prompts that previously lived in this folder have been migrated to
the `.github/agents/` directory as native GitHub Copilot agent definition files.

| Old file | New location |
|----------|-------------|
| `planner.prompt.md` | `.github/agents/planner.agent.md` |
| `developer.prompt.md` | Merged into `.github/copilot-instructions.md` |
| `reviewer.prompt.md` | `.github/agents/code-quality.agent.md` |
| `qa.prompt.md` | `.github/agents/qa.agent.md` |
| `security.prompt.md` | `.github/agents/security.agent.md` |

The `.agent.md` format is natively understood by GitHub Copilot Enterprise and does
not require any Python runtime, external API key, or custom agent runner.
