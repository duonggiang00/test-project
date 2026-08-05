# Change Contract: SEC-001–007 — Authorization and Session Security

Risk level: L4 authentication replacement; L3 authorization and tenant isolation  
Owner: Primary implementation agent after approval  
Independent review: Security reviewer required  
Approval required: Yes  
Approval evidence: Pending in `REMAINING_HIGH_RISK_APPROVAL_PACKET.md`

## Scope

In scope:

- Typed named permissions and owner-scoped policy decisions.
- Teacher ownership as the approved MVP isolation boundary; no organization or
  workspace tenant is introduced.
- Additive ownership and active-user fields where current models cannot express
  the approved policy.
- Access/refresh sessions, rotation, replay handling, revocation, current/all
  session logout, and password-change revocation.
- CSRF and origin enforcement at the cookie-authenticated Next.js BFF boundary.
- Canonical role redirects and removal of browser-authoritative role state.
- TEST-004 conversion from strict expected failures to passing negative tests,
  plus SEC-006 IDOR coverage.

Out of scope:

- Teacher sharing, organizations, ownership transfer, OAuth/social login,
  production password-reset delivery, and automatic compatibility with direct
  browser-to-backend clients.
- Shipping an unaudited admin override or claiming completion before the audit
  core from DATA-001 exists.

## Verified current behavior and drift

- `backend/app/api/deps.py` authenticates one bearer token and uses scattered
  string-role checks; `get_current_active_user` does not test an active field.
- `backend/app/core/security.py` issues one access token with a seven-day
  default. There is no refresh session, rotation, replay detection, or
  revocation store.
- `backend/app/services/auth_service.py` returns the bearer token; backend
  logout and refresh endpoints do not exist.
- The BFF login route stores a `token` HttpOnly cookie plus a browser-readable
  `role` cookie. Logout only deletes cookies, so the backend token remains valid.
- The generic BFF proxy clones browser headers before injecting credentials;
  incoming `Authorization` and `Cookie` must be removed explicitly.
- `frontend/src/proxy.ts`, the admin layout, and the student layout trust cookie
  role state and do not consistently use `/login`.
- Named policies do not exist. Exam bulk assignment, material operations,
  question/topic services, teacher history, and teacher analytics contain
  confirmed missing owner scopes.
- `Exam.creator_id` and `StudyMaterial.uploader_id` are nullable. `Topic` has no
  owner and a standalone `Question` has no unambiguous owner. Decks, briefs, and
  chunks can derive ownership only through a valid parent chain.

`SPEC_DRIFT`: the owner-confirmed compatibility behavior says teacher and admin
currently share user/system administration, while live admin endpoints are
admin-only. The proposed compatibility mapping follows the confirmed behavior
until the future separation switch; approval of this contract explicitly
authorizes that temporary mapping.

## Target behavior and invariants

- Evaluate authentication, active state, named permission, scoped existence,
  ownership/assignment, resource state, then audit requirement.
- Cross-owner and missing identifiers use the same policy-safe not-found shape
  where existence is sensitive.
- Actor-derived owner IDs are not writable request fields. Bulk authorization
  is set-based and query-count bounded.
- Existing ownerless Topic/standalone Question rows remain nullable and become
  admin-only quarantined records. No migration guesses an owner. New
  teacher-created aggregate roots always receive the authenticated teacher ID.
- Admin override is explicit, does not transfer ownership, and emits an audit
  event atomically with the business action.
- Access TTL is 15 minutes. Refresh TTL is seven days normally and 30 days for
  `rememberMe`. Refresh secrets are stored only as hashes and rotate atomically.
- Reuse outside a five-second concurrency window revokes the token family and
  emits a suspicious-replay audit event. An old token reused inside the window
  is rejected without family revocation; it never receives the replacement
  secret. The BFF uses a single-flight refresh path per process.
- Current-session logout revokes one session; logout-all and password change
  revoke every session. Disabled actors are rejected and their sessions revoked.
- Access and refresh values exist only in Secure-in-production, HttpOnly,
  SameSite=Lax cookies owned by the BFF. Browser code, Zustand, and local storage
  never receive either value. Role is hydrated from `/auth/me`.
- BFF mutations require an allowed Origin and matching CSRF cookie/header. The
  proxy strips browser-supplied `Authorization`, backend-origin, hop-by-hop, and
  raw cookie credentials before creating the backend request.

## Expected files and contracts

Backend modules:

- `app/core/security.py`, `app/api/deps.py`, a new typed policy module, and
  request/audit correlation helpers.
- `app/models/user.py`, new refresh-session model, ownership-capable aggregate
  roots, `app/models/__init__.py`, Pydantic token/auth schemas, and reversible
  Alembic revisions.
- Auth service/endpoints and every sensitive topic/exam/question/material/
  flashcard/history/analytics/student service and router.

Frontend modules:

- BFF login/logout/refresh/logout-all/CSRF routes, generic proxy route,
  `frontend/src/proxy.ts`, authenticated layouts, user store/hydration, services,
  hooks, and tests.

API impact:

- Add `/auth/refresh`, `/auth/logout`, and `/auth/logout-all` server contracts.
- Preserve the current login form input for the BFF. Add a refresh token to the
  server-to-server login response; neither token is serialized to the browser.
- Normalize all expected failures to `error_code`, object `details`, and
  `request_id`. Review and approve the OpenAPI diff before regeneration.

Migration impact:

- Add active-user state, hashed refresh sessions/token families, and minimal
  owner columns. Revisions are additive and downgradeable; ambiguous legacy
  ownership remains null/admin-only.

## Implementation checkpoints

1. After CI-004, add DATA-001 audit core before enabling admin override or
   claiming revocation audit completeness.
2. SEC-001 typed policy layer with explicit compatibility mapping.
3. SEC-002 ownership schema/scoped SQLAlchemy 2.x queries.
4. TEST-004 and SEC-006 negative/IDOR matrix.
5. SEC-003/004 refresh sessions, rotation, replay, active state, and logout.
6. SEC-005 BFF credential stripping, Origin, and CSRF enforcement.
7. SEC-007 hydration and canonical redirect UX.
8. Independent security review, full affected regression, and evidence handoff.

## Verification contract

- PostgreSQL five-actor matrix for list/detail/create/update/delete/publish/bulk,
  history, analytics, material, and student-owned submission operations.
- Missing-ID versus cross-owner-ID response equivalence and no identifier leaks.
- Access/refresh expiry, 7/30-day TTL, atomic rotation, within-window race,
  sequential replay, current/all-session logout, disabled actor, and password
  change.
- BFF cookie flags, credential stripping, refresh single-flight, missing/mismatched
  CSRF, disallowed Origin, and structured proxy failures.
- Redirect tests for `/login`, `/dashboard`, and `/student/home` with missing,
  stale, and tampered client state.
- Chromium, Firefox, WebKit, and mobile login-refresh-logout flow.
- Migration round trip, OpenAPI review, query budgets, architecture guard,
  changed-code coverage, fast/integration gates, and independent security review.

## Rollback

- Revert policy/auth application code while retaining additive columns.
- Revoke all refresh sessions and force re-login when rolling back auth behavior.
- Do not downgrade a live database merely to roll back application code.
- Ownership enforcement rollback must not expose quarantined legacy rows to
  non-admin actors.

