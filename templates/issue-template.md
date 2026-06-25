# Reference: Issue Template

Use this as a reference for writing high-quality issues for the AI Developer Agent.
Well-written issues produce better code.

---

## Title

Use an imperative verb phrase describing the change:
- ✅ `Add rate limiting middleware to Express API`
- ✅ `Fix null pointer error in task assignment handler`
- ❌ `Rate limiting`
- ❌ `Bug fix`

---

## Description

### What

Describe exactly what needs to be built or changed. Be specific about:
- The system component affected
- The API contracts (endpoints, request/response shapes)
- The data model changes needed
- The behaviour expected

### Why

Explain why this is needed. This helps the AI make better architectural decisions.

### Technical Notes (optional)

Any constraints, preferred libraries, existing patterns to follow, or code locations
that are relevant.

---

## Acceptance Criteria

Write each criterion as a testable, specific statement:

```
- [ ] Given a valid JWT token, the endpoint returns HTTP 200 with user data
- [ ] Given an expired token, the endpoint returns HTTP 401 with message "Token expired"
- [ ] Given no token, the endpoint returns HTTP 401 with message "Authentication required"
- [ ] Unit tests cover all three scenarios
- [ ] Token expiry is read from the JWT_EXPIRY_SECONDS environment variable
```

---

## Example Issue

**Title:** Implement JWT authentication middleware

**Description:**

Add JWT-based authentication to the Express API. All protected routes should require
a valid Bearer token in the Authorization header.

The middleware should:
- Extract the token from `Authorization: Bearer <token>`
- Verify the token using the `JWT_SECRET` environment variable
- Reject expired tokens with HTTP 401
- Attach the decoded user payload to `req.user`
- Use the `jsonwebtoken` library (already in package.json)

Protected routes are defined in `src/routes/protected.ts`.

**Acceptance Criteria:**
- [ ] Middleware rejects requests with no Authorization header (401)
- [ ] Middleware rejects invalid tokens (401)
- [ ] Middleware rejects expired tokens (401)
- [ ] Valid tokens set `req.user` to the decoded payload
- [ ] Unit tests cover all rejection scenarios
- [ ] Middleware is applied to all routes in `src/routes/protected.ts`
