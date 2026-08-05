# ADR-0004: Frontend State and Data-Fetching Boundaries

Status: Accepted  
Date: 2026-08-05

## Context

Scattered request logic and duplicated server state make caching, hydration, mutation, and error handling inconsistent.

## Decision

- Server Components fetch data needed for server-rendered output.
- SWR owns client-side server state, revalidation, and cache coordination.
- Zustand owns only client/UI state.
- `useEffect` is allowed for genuine effects but not ordinary API data fetching.
- A service layer owns BFF transport operations.
- SWR hooks coordinate service calls, cache keys, mutation, and revalidation.
- Components may not bypass these boundaries with direct Axios/API calls.

## Consequences

- Existing fetching patterns may be migrated incrementally by feature.
- Mutation tests must verify cache updates or revalidation without full-page reloads.
- Server Component fetches are not incorrectly prohibited by a blanket SWR rule.

## Supersession

This ADR supersedes rules stating that SWR is the only valid data-fetching mechanism in all frontend contexts.

