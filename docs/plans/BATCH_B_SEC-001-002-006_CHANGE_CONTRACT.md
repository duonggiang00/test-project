# Change Contract: Batch B — Named Permissions and Ownership Isolation

Risk level: L4 authorization, tenant isolation, additive migration, and an
approved breaking material-file API contract  
Owner: Primary Codex agent  
Independent review: Security and migration/data reviewers required  
Approval required: Yes  
Approval evidence: Project owner approved Batch B with all defaults in
`REMAINING_HIGH_RISK_APPROVAL_PACKET.md` on 2026-08-05. The same approval
explicitly includes the Batch D removal of internal `file_path` exposure and
replacement with an authenticated material download path.

## Scope

In scope:

- `SEC-001`: introduce one typed named-permission policy layer and replace
  authorization decisions in the affected endpoints with that layer.
- `SEC-002`: make teacher-owned content explicitly or unambiguously owned,
  apply owner-scoped SQLAlchemy 2.x queries, and validate same-owner links.
- `SEC-006` and `TEST-004`: cover anonymous, role, owner, non-owner, admin
  override, legacy-null, bulk, and missing-versus-cross-owner cases.
- Isolate AI document processing and retrieval to an explicitly authorized
  material. Remove the global/latest-chunk fallback.
- Block user deletion or demotion while the user owns content. Ownership
  transfer is not introduced.
- Audit successful admin cross-owner mutations in the same transaction as the
  business change.

Out of scope:

- Refresh sessions, active-user state, CSRF, browser role hydration, and route
  redirects (`SEC-003`–`SEC-005`, `SEC-007`).
- Sharing, organizations/workspaces, ownership transfer, and public draft
  links.
- Soft delete, restoration, purge, and redesign of historical educational
  record cascades (`DATA-003`–`DATA-005`). Unsafe destructive operations are
  blocked rather than redesigned in this batch.
- Full audit instrumentation (`DATA-002`). Only the mandatory admin-override
  event is added here.
- AI provider/state/evaluation work except the ownership boundary needed to
  prevent cross-owner retrieval.

Pulled forward from the separately approved `DATA-009` scope:

- Remove anonymous static access to material files and physical `file_path`
  disclosure. Material downloads use an authenticated owner/admin endpoint;
  only the separately approved avatar subtree remains public. This is required
  here because public material URLs would bypass the new ownership boundary.

## Behavior

Before:

- Role strings are compared across dependencies, endpoints, and services.
- Topic and exam drafts can be enumerated anonymously. Teacher queries for
  topics, questions, materials, flashcards, history, and analytics are mostly
  global.
- Bulk exam assignment, AI processing, background topic-kit generation, and
  RAG retrieval do not enforce a common owner boundary.
- `Topic` and standalone `Question` have no owner column. Existing Exam and
  Material owner columns are nullable and unindexed.
- Material AI save flows reuse one global ownerless `AI Workspace Drafts`
  topic. User hard delete can cascade through owned educational content.

After:

- Permission names and temporary role grants are centralized. The approved
  compatibility grant keeps `manage_users` and `manage_system_data` available
  to admin and teacher, while owned-content decisions still distinguish admin
  override from teacher ownership.
- The temporary `manage_users` grant does not allow a teacher to assign or
  modify the `admin` role. Otherwise a teacher could bypass the approved
  owner boundary by self-promotion; admin-role boundary changes require the
  named `admin_override` permission.
- Admin may access all management resources. A teacher may access only records
  owned by that teacher. Students may use only published/assigned learning
  content and self-service submission/progress operations. Anonymous access to
  these application resources is rejected.
- Missing and inaccessible cross-owner identifiers return the same canonical
  resource-specific 404 envelope whenever existence is sensitive.
- New aggregate roots derive immutable ownership from the authenticated actor.
  Request bodies never supply owner IDs. Every new Question records an explicit
  owner, including exam- and material-generated questions.
- Parent/child and cross-resource links are accepted only when effective owners
  match. Bulk authorization uses set-based validation and is all-or-nothing.
- AI process/chat/generation operations require one authorized Material.
  Retrieval filters DocumentChunk by that Material and never falls back to
  global chunks. Background work receives and rechecks an approved owner scope.
- Successful admin cross-owner mutations append `admin.override` with the
  original owner and permission before the enclosing transaction commits.
- Deleting or demoting a user who still owns content is rejected safely. A
  destructive material cascade is rejected when it could erase linked exam,
  answer, progress, or cross-owner records.

Preserved invariants:

- Backend remains authoritative; frontend visibility is not authorization.
- Admin override never transfers ownership.
- Student IDs for self-service operations come from the authenticated actor.
- Submitted answers and retained educational records are not made mutable or
  purgeable by this change.
- No trailing slash and canonical error/audit envelopes remain unchanged.

## Ownership and schema decisions

- Add nullable `topics.owner_id` and `questions.owner_id` UUID columns.
- Add explicit `RESTRICT` foreign keys named `topics_owner_id_fkey` and
  `questions_owner_id_fkey` to `users.id`.
- Add ordinary non-unique B-tree indexes:
  `ix_topics_owner_id`, `ix_questions_owner_id`, `ix_exams_creator_id`,
  `ix_study_materials_uploader_id`, `ix_questions_exam_id`,
  `ix_flashcard_decks_topic_id`, `ix_flashcards_deck_id`,
  `ix_topic_briefs_topic_id`, and `ix_document_chunks_material_id`.
- Execute no ownership backfill. Existing null-owned Topic, Question, Exam, or
  Material roots are admin-only quarantined records. A legacy exam child may
  derive from a non-null Exam creator; other nullable links do not establish a
  legacy Question owner.
- Deck/Card/Brief ownership derives through required Topic/Deck/Topic chains;
  Chunk ownership derives through its required Material.
- The application enforces non-null owner and same-owner links for new writes.
  Cross-table triggers and role checks are not added to the database.

## Expected files and contracts

Files/modules:

- Backend policy/dependency/audit helpers; Topic and Question models; one
  downgradeable Alembic revision; affected schemas, endpoints, and services for
  admin users, topics, exams, questions, materials, flashcards, AI Studio,
  history, analytics, and student self-service.
- Ownership integration/contract/unit tests, migration runner coverage, seed
  fixtures, frontend AI material-selection behavior/tests, generated OpenAPI,
  database-model signature, and project inventory when executable contracts
  change.

API/event/schema impact:

- Existing paths are retained. Previously anonymous teacher-content reads now
  require authentication and visibility permission.
- Approved breaking material-file contract: `MaterialResponse` and
  `MaterialDetailResponse` no longer expose the physical `file_path`, the
  material subtree is no longer served through anonymous `/uploads/**`, and
  authenticated owner/admin clients download through
  `GET /materials/{material_id}/download`. This is the exact DATA-009 access
  change included in the approved Batch D packet; clients that consumed the
  internal path must migrate to the download endpoint.
- AI chat requires `material_id`; this matches the existing frontend payload
  but becomes an enforced backend contract.
- Cross-owner failures change from ad hoc 403/success to canonical 404. The
  strict TEST-004 assertions may change from 403 to 404 only because the
  approved anti-enumeration contract proves the former expectation wrong.
- Add the registered `admin.override` audit action with a narrow payload schema.

Migration/data impact:

- Additive nullable columns, named foreign keys, and indexes only; no data
  updates or destructive migration statements.
- Downgrade removes the new indexes, FKs, and columns and therefore loses owner
  values recorded after upgrade. Downgrade is for isolated verification only.

Security/ownership/tenant impact:

- This is the approved MVP teacher-owner isolation boundary; no organization
  tenant is inferred.
- Owner predicates are applied in database queries before returning sensitive
  resources. List and detail boundaries are equivalent.
- Ownerless legacy data cannot be exposed to non-admin actors.

## Verification contract

Targeted tests:

- Typed permission grant/denial and compatibility mapping unit tests.
- Five-actor PostgreSQL matrices for list/detail/create/update/delete/publish,
  same-owner and cross-owner links, bulk assignment, materials, flashcards,
  history/analytics, AI retrieval, and student-owned records.
- Missing-ID versus cross-owner response equality, legacy-null quarantine,
  admin-override audit atomicity, user deletion/demotion conflict, and
  destructive-cascade protection.
- Query-count ceilings for representative list/detail/bulk checks and a
  negative fixture proving no N+1 authorization query.

Static/type checks:

- Ruff, configured mypy plus explicit changed security modules, architecture
  guard, generated inventory check, OpenAPI check, and changed-line coverage.

Integration/PostgreSQL checks:

- Upgrade -> previous base -> upgrade migration round trip with exact columns,
  FK names/actions, and index definitions.
- Full PostgreSQL integration suite after targeted ownership tests pass.

Build/E2E/visual checks:

- Frontend unit/component tests for the material-required AI flow, production
  build, and real authenticated student E2E. No visual change is intended.
- Playwright starts isolated Next.js servers on configurable ports with
  dedicated `.next-e2e-*` caches and never reuses an unrelated development
  server.

Manual verification:

- Probe owner/non-owner/admin requests with canary identifiers and confirm no
  response, audit payload, or retrieval context leaks inaccessible content.

## Rollback

- Code rollback: revert authorization/application code while retaining the
  additive ownership columns. Do not re-expose ownerless quarantined rows.
- Data rollback: do not downgrade a live database merely to roll back
  application behavior. Isolated downgrade drops the new owner data and then
  re-upgrades with null legacy values.

## Assumptions and drift

Verified assumptions:

- `Exam.creator_id` and `StudyMaterial.uploader_id` are the canonical existing
  owner fields.
- Required parent chains can derive Deck, Card, Brief, and Chunk ownership.
- The frontend already sends `material_id` for AI chat.
- Baseline ownership integration result is `1 passed, 2 xfailed`; both strict
  XFAILs reproduce missing enforcement.

Unresolved assumptions:

- Topic/Flashcard models have no publish/assignment state. Until a later
  contract introduces one, student Topic visibility is limited to Topics that
  contain a published Exam or an available Deck, and study endpoints recheck
  that derived visibility.
- The approved matrix marks Admin as allowed for student submission actions,
  but the current self-service endpoints derive the student identity only from
  the authenticated actor and have no approved "act on behalf of student"
  target contract. This batch retains the safer student-only endpoint behavior
  and leaves SEC-006 in REVIEW until the owner chooses either explicit admin
  impersonation/on-behalf-of semantics or a matrix amendment.

SPEC_DRIFT:

- The temporary approved teacher/admin user-management parity conflicts with
  current admin-only endpoints; this batch implements the central compatibility
  mapping.
- Current hard deletes/cascades conflict with the approved retention direction.
  This batch blocks newly exposed destructive paths but does not claim
  `DATA-003`–`DATA-005` completion.
- `ExamResponse.creator_id` assumes non-null while the database permits legacy
  null owners; response schemas must tolerate quarantined admin-visible rows.
- Existing TEST-004 expects 403 for cross-owner IDs, while the higher-authority
  anti-enumeration contract requires equivalence with missing IDs, implemented
  as canonical 404.
- The target matrix grants Admin access to student submission operations while
  live self-service routes deny non-students. No admin submission mutation is
  introduced without an explicit target-student and audit contract.
