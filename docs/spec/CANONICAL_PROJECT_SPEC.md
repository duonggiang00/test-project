# Canonical Project Specification

Status: Approved  
Approved date: 2026-08-05  
Product stage: MVP with real users  
Primary development environment: Windows

## 1. Purpose and authority

This document records the product and architecture decisions confirmed by the project owner. It is the canonical specification for future implementation and agent work.

The source-of-truth order is:

1. Executable application behavior and contracts in the current codebase.
2. Accepted Architecture Decision Records (ADRs).
3. This approved specification.
4. Scoped `AGENTS.md` instructions and task workflows.
5. Generated project inventory.
6. Historical PRDs, plans, handoffs, and snapshots.

Current code wins when it differs from a historical PRD. This rule does not convert an implementation defect into an approved requirement. An agent that finds a material conflict must record `SPEC_DRIFT`, determine whether the current behavior is intentional, and request approval before changing authentication, authorization, data contracts, migrations, or other breaking behavior.

## 2. Product scope

All existing product modules are official scope and remain under active development:

- Authentication and user management.
- Topic and material management.
- Exam and question management.
- Student exam flow.
- Flashcards and spaced repetition.
- AI Studio, retrieval-augmented generation, and chatbot functionality.
- AI-assisted grading.
- Analytics and reporting.
- Password reset.
- File upload and content extraction.

No module is considered feature-frozen. Changes must preserve existing user-visible behavior unless an approved task explicitly changes its contract.

## 3. Roles, permissions, and ownership

The official roles are `admin`, `teacher`, and `student`.

### 3.1 Current behavior

- `admin` and `teacher` currently have equivalent system-management permissions.
- `student` may only access data intended for the student and submissions owned by that student.

### 3.2 Target authorization model

The architecture must support future separation without widespread role-condition rewrites:

- `admin` may manage all users and all system data.
- `teacher` may manage only resources owned by that teacher.
- A teacher who is not the owner has no access to another teacher's resource.
- `student` may access only published/assigned learning data and submissions owned by that student.
- No teacher-to-teacher sharing model is currently approved.
- Administrative override must be explicit and auditable.

Authorization must be expressed through named permission and ownership policies instead of scattered direct role comparisons.

### 3.3 Enforcement

- The backend is the security enforcement point.
- Frontend route guards, redirects, and hidden controls are user-experience measures only.
- Every sensitive read and every mutation must enforce role, ownership, and tenant boundaries on the backend.
- Negative authorization tests must cover anonymous, student, owner teacher, non-owner teacher, and admin access.

### 3.4 Canonical redirects

| Actor | Destination |
|---|---|
| Admin or teacher | `/dashboard` |
| Student | `/student/home` |
| Unauthenticated user | `/login` |

## 4. Backend and data architecture

### 4.1 Database and ORM

- PostgreSQL is the official database.
- SQLite may be used for isolated unit tests when PostgreSQL-specific behavior is not involved.
- Query, migration, and integration tests must run against PostgreSQL.
- New and migrated data-access code must use SQLAlchemy 2.x `select()` syntax.
- New code must not introduce legacy `Session.query()` usage.

### 4.2 Transaction boundaries

- For a simple use case, the application/use-case layer controls commit and rollback.
- For a use case involving multiple aggregates, use an explicit Unit of Work.
- Routers must not contain transaction-heavy business logic.
- Individual repository operations must not perform uncoordinated commits.

### 4.3 API conventions

- API version prefixes such as `/api/v1` are not required at this stage.
- Collection and resource endpoints must not use trailing slashes.
- Trailing-slash policy must be enforced with tests or static checks.
- A standardized error response contains `error_code` and structured `details`.
- The frontend owns user-facing localization of error codes.
- Breaking OpenAPI changes require explicit approval.

Example error shape:

```json
{
  "error_code": "RESOURCE_NOT_FOUND",
  "details": {
    "resource": "exam"
  }
}
```

### 4.4 Migrations

- Schema changes require Alembic migrations.
- Every migration must support downgrade.
- Verification must cover upgrade, downgrade, and upgrade again.
- Destructive or lossy changes require a documented rollback and data-preservation plan.
- Agents may create and run migrations against isolated local test databases.
- Running migrations against a shared or production-like database requires separate authorization.

## 5. Authentication and application boundary

- Authentication uses access and refresh tokens stored in HttpOnly cookies.
- The Next.js BFF/proxy is the only frontend-to-backend access path.
- Browser code must not call the backend origin directly.
- Backend authorization remains mandatory even when BFF and frontend route protection are present.
- The auth design must cover refresh rotation, revocation, logout, CSRF protection, and replay protection.
- Password reset is a mock/local flow for the current MVP and does not require a production email provider.

Canonical auth routes must redirect users according to Section 3.4.

## 6. Audit, deletion, and retention

### 6.1 Audit log

Audit logging is required for:

- Admin and teacher administrative actions.
- User and role changes.
- Exam and question changes.
- Publishing and unpublishing.
- Grading and grade changes.
- AI generation and approval.
- Restore and permanent purge actions.
- Security-sensitive authentication events.

An audit event must capture the actor, action, entity type and identifier, timestamp, correlation/request identifier, and a structured change description. Sensitive tokens and secrets must never be logged.

### 6.2 Soft delete

- Applicable business data must use soft delete.
- Soft-deleted records remain recoverable for 30 days.
- Records are eligible for permanent purge after 30 days.
- Default queries must exclude soft-deleted records.
- Admin may restore any eligible record.
- A teacher may restore only an owned record when the resource policy allows restoration.
- Purge operations must be auditable and support a dry-run mode.

Educational records such as submissions and grades may require a stricter retention rule. Their final purge policy must be approved before permanent deletion is implemented.

## 7. File upload

- Supported formats: PDF, DOCX, PPTX, and TXT.
- Maximum size: 50 MB per file.
- Storage: local filesystem for the current MVP.
- Storage access must be wrapped behind an interface so object storage can be introduced later.
- Validation must check extension, declared MIME type, and file signature/magic bytes where applicable.
- Generated storage names must not trust the user-provided filename.
- Path traversal and unsafe archive/content processing must be prevented.
- Access must enforce owner/admin authorization and tenant isolation.
- Soft-deleted file metadata and physical files follow the approved 30-day recovery window.

## 8. Frontend architecture and design

### 8.1 Data and state ownership

- Server Components fetch data needed for server-rendered output.
- SWR owns client-side server state and cache coordination.
- Zustand owns only client/UI state, not server state or authentication tokens.
- `useEffect` is allowed for genuine side effects, but not for ordinary API data fetching.
- Transport operations live in a service layer.
- SWR hooks coordinate caching, revalidation, and mutations.
- Browser requests must go through the Next.js BFF/proxy.

### 8.2 Components

- Reuse existing components when semantics and behavior match.
- Domain-specific components are allowed when standard Shadcn behavior or styling does not match the approved brutalist design.
- Component reuse must not force incorrect semantics.

### 8.3 Visual design

- The official visual language is strict black-and-white brutalism.
- Colored success, warning, and error states are not allowed.
- State must be communicated using text, symbols, icons, border weight/style, layout, and accessible labels.
- Fonts must be local and loaded through the Next.js font API.
- Remote font dependencies are not allowed.
- Visual regression tests should protect the approved design language.

### 8.4 Browser coverage

Critical UI flows must support:

- Chromium.
- Firefox.
- WebKit.
- Mobile viewport coverage.

There is no formal WCAG conformance target at this stage, but semantic HTML, keyboard operability, visible focus, and accessible names remain expected engineering quality.

## 9. AI and RAG

### 9.1 Provider and model selection

- AI access must use a provider abstraction.
- The model may be selected by use case through configuration or policy.
- Provider/model identifiers must not be hardcoded in UI components or endpoint business logic.
- Provider failure is reported immediately to the user; automatic fallback is not currently required.

### 9.2 Human approval

Human approval is required before publishing:

- Generated questions and exams.
- Generated flashcards.
- AI grading suggestions.
- Generated topic briefs.

AI grading produces a suggestion only. A teacher or admin makes the final grading decision.

The required lifecycle is:

```text
requested -> processing -> generated -> awaiting_review
          -> approved | rejected -> published
```

No direct `generated -> published` transition is allowed.

### 9.3 AI audit and privacy

The system must record, subject to privacy controls:

- Prompt and prompt version.
- Provider and model.
- Token usage and estimated cost.
- Latency.
- Retrieved context sources.
- Reviewer and approval outcome.

The system processes personal or sensitive content. Logs and retrieval must enforce tenant isolation, access control, redaction where required, and an explicit retention policy.

### 9.4 Evaluation

AI regression evaluation must measure:

- Answer correctness.
- Groundedness and citation validity.
- Context relevance.
- Prompt-injection resistance.
- Latency.
- Token usage and cost.

No golden dataset currently exists. An admin is responsible for approving the reference answers. The initial target is a small, high-quality dataset before expanding coverage.

## 10. Testing and CI

### 10.1 Coverage policy

- Establish the current backend and frontend coverage baseline.
- CI must prevent coverage from decreasing.
- New or materially changed code should target approximately 80% meaningful coverage.
- Coverage percentage does not replace behavior, contract, security, or integration testing.

### 10.2 Test environments

- SQLite is permitted for suitable unit tests.
- PostgreSQL is mandatory for query, migration, and integration tests.
- Fast mocked E2E tests run on pull requests.
- Real-backend/PostgreSQL smoke E2E tests run on `main` and may run nightly.
- Visual regression testing is approved.

### 10.3 Critical E2E flows

1. Login, refresh, logout, and role redirect.
2. Teacher creates and publishes an exam.
3. Student takes and submits an exam.
4. Teacher views and grades the result.
5. Material upload and AI content generation with review.

### 10.4 CI triggers and performance

- GitHub Actions is the CI/CD platform.
- `main` is the primary branch.
- CI runs for pull requests and pushes to `main`.
- Fast pull-request gates should complete within five minutes.
- Integration/E2E gates should complete within ten minutes.
- A flaky test may retry once to collect diagnostics, but remains a tracked failure with an owner.
- Tests must not be weakened or have assertions changed merely to make CI pass. A test change requires evidence that the specification or test is wrong.

## 11. Agent operating policy

- Agents may plan, implement, and verify ordinary scoped tasks autonomously.
- Prior approval is required for authentication changes, migrations, breaking API changes, and large architectural changes.
- Subagents are reserved for large or high-risk tasks.
- Small, common dependencies that do not change architecture may be added within task scope; architectural dependencies require approval.
- Agents may create branches, commits, and pull requests.
- Project memory is updated only when a capability, contract, architectural decision, or blocker changes.
- Technical inventory must be generated rather than maintained manually.
- Code, comments, docstrings, technical documentation, UI text, error translations, and agent engineering reports use English.

Every completed implementation task must report:

- Test commands and exact relevant results.
- Files changed.
- Contract and migration impact.
- Known risks and unverified items.
- Manual verification.
- Screenshot or trace for UI changes.
- Rollback instructions when applicable.

## 12. Toolchain direction

- Frontend package manager: npm with `package-lock.json`.
- Python dependency management target: uv with `pyproject.toml` and `uv.lock`.
- Windows is the primary local environment.
- Docker is not required for current daily development, but the repository should retain a clean path to later containerization.
- Separate dev, staging, and production environments are not yet established and must not be assumed by agents.

## 13. Deferred decisions

The following decisions require future approval before implementation:

- Permanent retention policy for submissions, grades, and sensitive AI audit records.
- Teacher-to-teacher or workspace-based sharing.
- Production password-reset email provider.
- Production object storage provider.
- Formal accessibility conformance target.
- Deployment topology for dev, staging, and production.

