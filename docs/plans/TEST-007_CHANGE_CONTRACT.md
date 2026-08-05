# Change Contract: TEST-007 — Hydration, Cache Mutation, and BFF Boundary

Risk level: L1
Owner: Primary Codex agent
Approval required: No

## Evidence targets

- Persisted user identity rehydrates while no access token enters local storage.
- SWR server-state cache mutates without reload or duplicate transport logic.
- Next BFF forwards path/query, converts the HttpOnly cookie to backend authorization, strips host, and rewrites backend redirects so the origin is not exposed.
