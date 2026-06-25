# Reference: Pull Request Template

Use this as a reference for writing clear, reviewable pull requests.

---

## Title

Format: `<type>: <short description>`

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `security`

Examples:
- `feat: Add JWT authentication middleware`
- `fix: Handle null due date in task creation`
- `test: Add integration tests for /api/tasks`

---

## Description Template

```markdown
## Summary

One or two sentences describing what this PR does and why.

## Changes

- `src/auth/middleware.ts` — Added JWT validation middleware
- `src/routes/protected.ts` — Applied middleware to protected routes
- `src/auth/middleware.test.ts` — Added unit tests for all auth scenarios
- `src/types/express.d.ts` — Extended Request type to include `user` property

## Testing

- All existing tests pass: `npm test`
- New tests added for: invalid token, expired token, missing token, valid token
- Tested manually with Postman against local environment

## Related Issues

Resolves #42
```

---

## Review Checklist

Before requesting review, ensure:

- [ ] Tests added for all new functionality
- [ ] No hardcoded credentials or secrets
- [ ] Error cases are handled explicitly
- [ ] No console.log left in production code
- [ ] Breaking changes are documented
- [ ] PR title follows the `type: description` format
