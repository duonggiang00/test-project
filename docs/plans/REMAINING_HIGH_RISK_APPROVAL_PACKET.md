# Remaining High-Risk Implementation Approval Packet

Status: Batches A–E/defaults and Batch A FK-name amendment approved
Prepared: 2026-08-05  
Parent tracker: `AGENT_WORKFLOW_OPTIMIZATION_PLAN.md`

Approval recorded: 2026-08-05. The project owner approved A–E with every
default in this packet and will supply golden-dataset content later. The narrow
amendment to name four foreign keys in revisions `73f523515ba5` and
`e598471b8b6d`, discovered only by the required PostgreSQL round trip, was
explicitly approved by the project owner on 2026-08-06.

The approval includes the DATA-001 response-contract transition documented in
the linked migration/data change contract. This implements the earlier explicit
canonical-spec decision that the backend returns `error_code` and structured
`details`, while the frontend localizes those codes; the target envelope is
`{error_code, details, request_id}` and does not serialize legacy `message`
values.

## 1. Why approval is required now

The remaining implementation changes authentication, authorization/tenant
isolation, migration history, persistent lifecycle rules, or the AI
architecture. The target specifications are approved, but workspace rules
require a separate approval before these high-risk changes are implemented.

Approval is limited to the batches below. A newly discovered breaking API,
destructive operation against non-test data, new architectural dependency, or
material scope expansion returns to the owner for approval.

## 2. Required order

`A -> D1 -> B -> C -> D2 -> E`

- A restores trustworthy fresh-database migration testing.
- D1 adds the DATA-001 audit core needed by admin override and revocation.
- B establishes the ownership boundary used by data and AI work.
- C replaces the temporary bearer/session behavior.
- D2 completes instrumentation, soft delete, retention, purge, and file lifecycle.
- E builds governed AI behavior on the security and audit foundations.

Each batch receives its own commit(s), test evidence, and independent review
where required. No batch runs a migration against shared or non-test data.

Executable file/test contracts:

- [`CI-004_DATA-001-006-009_CHANGE_CONTRACT.md`](CI-004_DATA-001-006-009_CHANGE_CONTRACT.md)
- [`SEC-001-007_CHANGE_CONTRACT.md`](SEC-001-007_CHANGE_CONTRACT.md)
- [`AI-001-009_CHANGE_CONTRACT.md`](AI-001-009_CHANGE_CONTRACT.md)

## 3. Batch A — Repair the legacy initial migration

Tasks: CI-004  
Risk: migration history (approval required)

Approved scope if authorized:

- Correct revision `27f1dff6a48f` so a fresh PostgreSQL database does not try to
  drop indexes from a nonexistent legacy `user` table.
- Inspect for the legacy table and drop the table conditionally; do not issue
  separate unconditional index drops.
- Preserve downgrade creation of the legacy table so fresh
  upgrade/downgrade/upgrade remains reversible at the schema level.
- Run only through the guarded disposable `_test` database lifecycle.

Non-goals: changing current application models, stamping a shared database,
restoring historical row data on downgrade, or rewriting later revisions.

Required evidence: fresh upgrade, downgrade, second upgrade, Alembic head,
model-drift guard, and confirmed test-database cleanup.

## 4. Batch B — Named authorization and ownership isolation

Tasks: SEC-001, SEC-002, SEC-006, TEST-004; ownership prerequisite for DATA-009
and AI-005  
Risk: authorization, tenant isolation, and likely additive migrations

Approved scope if authorized:

- Introduce typed named policies from
  `docs/spec/PERMISSION_AND_OWNERSHIP_MATRIX.md`.
- Preserve the explicit temporary admin/teacher compatibility mapping only for
  system administration; teacher content access moves to owner scope.
- Use existing `creator_id`/`uploader_id` ownership where unambiguous and add an
  owner column only to aggregate roots that cannot derive ownership safely.
- Apply scoped SQLAlchemy 2.x queries to list, detail, bulk, background, and
  export paths without leaking cross-owner existence.
- Keep admin override explicit and prepare it for audit instrumentation in D.
- Convert the two strict ownership XFAIL cases into passing denial tests and
  expand the anonymous/student/owner/non-owner/admin IDOR matrix.
- Keep ambiguous legacy Topic/standalone Question ownership nullable and
  admin-only; do not guess a teacher during migration.

Non-goals: teacher-to-teacher sharing, organization workspaces, ownership
transfer, public drafts, or frontend-only authorization.

Required evidence: migration round trip for any owner fields, five-actor
negative matrix, PostgreSQL integration, query budgets for bulk/list paths,
OpenAPI review, and independent security review.

## 5. Batch C — Access/refresh cookie session lifecycle

Tasks: SEC-003, SEC-004, SEC-005, SEC-007  
Risk: authentication and session contract

Proposed defaults requiring approval:

- Access token TTL: 15 minutes.
- Refresh token TTL: 7 days normally; 30 days only when `rememberMe` is true.
- Rotate the refresh token on every use; revoke the token family when replay is
  detected.
- BFF stores both tokens in `HttpOnly` cookies; `Secure` in production,
  `SameSite=Lax`, and no token in browser-readable storage.
- Remove the client-readable role cookie; hydrate role from the authenticated
  user contract.
- Current-session logout is the default; a separate logout-all operation
  revokes every active session for the user.
- Require a CSRF token/header on cookie-authenticated mutations in addition to
  origin checks and SameSite cookies.
- Strip browser-supplied authorization and raw cookie credentials before the
  BFF injects its own backend credential.
- Keep password reset as the approved mock/local flow.

Implementation may add a hashed refresh-session table and additive migration.
Raw refresh tokens are never stored. Backend remains authoritative; frontend
redirects remain `/dashboard`, `/student/home`, and `/login`.

For parallel refresh requests, the proposed rule is: reuse inside a five-second
rotation race is rejected without revoking the family; later reuse revokes the
family. The BFF also serializes refresh within each process.

Non-goals: OAuth/social login, email delivery, bearer tokens in local storage,
or automatic compatibility with unapproved third-party clients.

Required evidence: expiry, rotation, replay, current/all-session logout, CSRF,
BFF-only, cookie attributes, role redirects, sanitized errors, migration round
trip, and independent authentication review.

## 6. Batch D — Audit, soft delete, retention, and file lifecycle

Tasks: DATA-001–006 and DATA-009  
Risk: additive migrations, destructive lifecycle behavior, authorization

Approved baseline scope if authorized:

- Add the canonical append-only audit event and instrument required
  admin/teacher, exam, grading, AI, restore/purge, and auth events.
- Add reusable timezone-aware soft-delete fields and default query exclusion.
- Allow admin/owner restoration during the approved 30-day recovery window.
- Implement admin-only purge with dry-run and audit, but only for resource
  classes whose permanent retention policy is approved.
- Apply owner/admin access and the approved lifecycle to material files through
  the existing storage boundary.
- Replace public material-file mounting/internal `file_path` exposure with an
  authenticated owner/admin download path; keep only separately approved avatar
  assets public. This material access-contract change is included in D approval.

Proposed DATA-006 retention decision requiring approval:

- Submissions and grades: no permanent purge in the MVP; soft-deleted records
  remain retained until a later educational-record retention ADR.
- Raw AI prompts and retrieved context: purge 30 days after generation job
  completion.
- Redacted AI audit metadata, context-source identifiers/citations, reviewer,
  and outcome: retain while the parent business record exists; no automated
  purge in the MVP.
- Extracted document chunks inherit the parent material lifecycle. Audit events
  themselves have no approved purge policy and are not automatically purged.

Purge remains disabled for any unclassified record. Every purge has a dry run,
bounded batch, owner, audit event, and rollback/recovery evidence appropriate
to the storage layer.

Purge is allowlisted rather than generic. User, Exam, Question, and unsafe Topic
purge remains blocked in the MVP because current cascades can destroy retained
submissions, grades, or flashcard progress.

Non-goals: legal-policy claims, production scheduling, hard deletion of active
records, or retroactive collection of data that does not exist.

Required evidence: migration round trip, time-boundary tests, default-read
exclusion, restore authorization, dry-run vs purge, redaction, file cleanup,
and independent migration/security review.

## 7. Batch E — Governed AI provider, review states, and evaluation

Tasks: AI-001–009  
Risk: major architecture, sensitive data, tenant isolation, AI grading

Approved scope if authorized:

- Replace direct OpenAI/OpenRouter clients with a provider protocol and
  configuration-driven model policy per use case; no automatic fallback.
- Add explicit generation/review/approval/rejection/publication states so AI
  output cannot publish itself.
- Version prompts and record provider/model, token usage, cost, latency,
  context sources, reviewer, and outcome through D's audit boundary.
- Redact and authorize sensitive logs; enforce B's owner scope before retrieval
  so cross-owner material never enters context.
- Add a versioned golden-dataset schema and runner for correctness,
  groundedness/citation, context relevance, prompt injection, latency, and
  cost, then add regression thresholds after the dataset is approved.
- Keep AI grading advisory until teacher/admin approval.

Admin input is still required for 30–50 reviewed golden cases. Authorization of
E permits implementation of the dataset format and tooling; it does not permit
an agent to invent approved answers or mark synthetic cases as admin-approved.

Non-goals: automatic publishing, final autonomous grading, silent provider
fallback, cross-tenant retrieval, or storing unrestricted raw sensitive logs.

Required evidence: provider contract tests, state-transition/authorization
tests, redaction and cross-owner retrieval tests, traceable audit metadata,
repeatable evaluation report, threshold failure probe, latency/cost report, and
independent AI/security review.

## 8. Owner response format

The owner may approve incrementally. A complete response can be:

```text
Approve A, B, C with the proposed defaults, D with the proposed DATA-006
retention policy, legacy owner-null admin quarantine, and E. Golden dataset
content will be supplied later. The temporary teacher/admin system-management
compatibility mapping is approved.
```

Any exception should name the batch and replacement decision. Silence or a
general request to continue is not treated as approval for these high-risk
batches.
