# Permission and Ownership Matrix

Status: Approved target policy  
Date: 2026-08-05  
Parent specification: [`CANONICAL_PROJECT_SPEC.md`](CANONICAL_PROJECT_SPEC.md)  
Related ADR: [`../adr/0003-bff-cookie-authentication.md`](../adr/0003-bff-cookie-authentication.md)

## 1. Purpose

Define backend-enforced permissions without scattering direct role comparisons across endpoints and services. The policy supports current admin/teacher parity while providing the approved target state in which teachers manage only owned resources.

## 2. Actors

- **Admin**: System-wide administrative override, subject to audit.
- **Owner teacher**: Teacher whose identifier matches the resource `owner_id`.
- **Non-owner teacher**: Authenticated teacher who does not own the resource.
- **Student owner**: Student whose identifier matches student-owned data such as a submission.
- **Other student**: Authenticated student who does not own the student-scoped record.
- **Anonymous**: Unauthenticated actor.

## 3. Compatibility transition

Current code may grant teachers administrative capabilities. Migration to the target policy must be incremental and tested. New authorization code must use named policies even when the temporary mapping grants both `admin` and `teacher` the same permission.

Temporary compatibility is configured centrally, for example:

```text
manage_users: admin + teacher (temporary)
manage_system_data: admin + teacher (temporary)
```

The target mapping is:

```text
manage_users: admin
manage_system_data: admin
manage_owned_content: owner teacher
```

No endpoint may implement the transition with an ad hoc `admin || teacher` check.

## 4. Named policies

| Policy | Meaning |
|---|---|
| `manage_users` | List, create, update, disable, or change roles for users |
| `manage_system_data` | Manage system-wide configuration or resources without a teacher owner |
| `create_content` | Create a teacher-owned topic, material, exam, question, flashcard, or brief |
| `read_owned_content` | Read a teacher-owned resource |
| `update_owned_content` | Modify a teacher-owned resource |
| `delete_owned_content` | Soft-delete a teacher-owned resource |
| `restore_owned_content` | Restore an eligible teacher-owned resource within retention |
| `publish_owned_content` | Publish or unpublish an owned resource |
| `read_assigned_content` | Read content published or assigned to the student |
| `create_submission` | Start or submit the actor's own submission |
| `read_own_submission` | Read the student's own submission and permitted result |
| `read_owned_exam_submissions` | Read submissions for an exam owned by the teacher |
| `grade_owned_exam_submission` | Grade a submission for an exam owned by the teacher |
| `approve_owned_ai_content` | Approve/reject AI output created under an owned resource |
| `view_audit_log` | Read audit events within the actor's allowed scope |
| `admin_override` | Perform a system-wide operation that normally requires ownership |
| `purge_deleted_data` | Permanently purge records whose retention window has elapsed |

## 5. Resource matrix — target state

Legend: `A` allowed, `O` allowed only when owner/scope matches, `P` allowed only when published/assigned, `—` denied.

| Resource/action | Admin | Owner teacher | Non-owner teacher | Student owner | Other student | Anonymous |
|---|---:|---:|---:|---:|---:|---:|
| List/manage users | A | — | — | — | — | — |
| Read system configuration | A | — | — | — | — | — |
| Create teacher content | A | A | A | — | — | — |
| Read draft teacher content | A | O | — | — | — | — |
| Update teacher content | A | O | — | — | — | — |
| Soft-delete teacher content | A | O | — | — | — | — |
| Restore teacher content | A | O | — | — | — | — |
| Publish teacher content | A | O | — | — | — | — |
| Read published/assigned learning content | A | O | — | P | P | — |
| Start/create submission | — | — | — | O | — | — |
| Read submission | A | O through exam ownership | — | O | — | — |
| Update in-progress submission | — | — | — | O | — | — |
| Update submitted submission answers | — | — | — | — | — | — |
| Grade submission | A | O through exam ownership | — | — | — | — |
| View grade/result | A | O through exam ownership | — | O when released | — | — |
| Generate AI content | A | O | — | — | — | — |
| Approve/reject AI content | A | O | — | — | — | — |
| Publish approved AI content | A | O | — | — | — | — |
| View audit events | A | O for owned resources | — | — | — | — |
| Permanently purge eligible data | A | — | — | — | — | — |

## 6. Ownership rules

### 6.1 Teacher-owned resources

The following resources must have an explicit or derivable teacher owner:

- Topics.
- Materials and uploaded files.
- Exams.
- Questions when not exclusively owned through an exam.
- Flashcard decks/cards.
- Topic briefs.
- AI generation jobs and generated artifacts.

Prefer an explicit immutable `owner_id` on aggregate roots. Child resources may derive ownership only through a required parent relationship when the query and authorization check cannot become ambiguous.

### 6.2 Student-owned resources

- A submission belongs to exactly one student.
- Submission answers inherit the submission owner.
- A student may not supply or override `student_id` for an authenticated self-service operation.
- A submitted submission is immutable except through an explicitly approved correction workflow.
- Result visibility may depend on exam/result release state.
- Student self-service endpoints never allow an Admin to impersonate a
  Student. Admin read and grading operations use their separate management
  contracts and remain audited; an on-behalf-of submission workflow requires
  a future approved contract.

### 6.3 Admin override

- Admin override must be explicit in the policy decision.
- Override actions must create an audit event.
- The audit record must identify the original owner and admin actor.
- Admin override must not silently transfer ownership.

### 6.4 No sharing

Teacher-to-teacher sharing, organization workspaces, and public draft links are not approved. Non-owner teacher access is denied until a future ADR defines a sharing model.

## 7. Authorization evaluation order

For each sensitive operation, evaluate:

1. Authentication and active-user status.
2. Named permission for the requested action.
3. Resource existence using a query scoped to allowed ownership/visibility where practical.
4. Ownership or assignment.
5. Resource state, such as draft, published, submitted, deleted, or retention-expired.
6. Audit requirement.

Prefer ownership-scoped database queries over fetching an arbitrary identifier and checking it later. Responses must not leak whether an inaccessible cross-owner record exists.

## 8. Soft delete and restoration

- Normal delete operations are soft delete where the resource policy supports it.
- Deleted records are excluded from default queries.
- Admin can restore eligible resources.
- Owner teachers can restore eligible owned content only.
- Non-owner teachers and students cannot restore teacher-owned data.
- Permanent purge is admin-only and requires the 30-day retention window to have elapsed.
- Submission, grade, and sensitive AI-log purge remain blocked until their specific retention policy is approved.

## 9. Required test matrix

Every sensitive endpoint must cover applicable cases:

| Case | Expected result |
|---|---|
| Anonymous request | Authentication failure |
| Inactive/disabled actor | Access denied |
| Student attempts teacher mutation | Access denied |
| Owner teacher accesses owned resource | Allowed when state permits |
| Non-owner teacher probes identifier | Not found or policy-safe denial without existence leak |
| Admin performs override | Allowed and audited |
| Student accesses own submission | Allowed when state permits |
| Student accesses another submission | Not found or policy-safe denial |
| Actor accesses soft-deleted record through normal endpoint | Not found |
| Restore after 30-day eligibility window | Denied or unavailable |

## 10. Implementation constraints

- Backend authorization is mandatory; frontend checks do not satisfy this policy.
- Policy names must be centralized and typed where possible.
- New endpoints must declare the policy they enforce.
- List queries must apply the same ownership boundary as detail queries.
- Bulk operations must validate authorization for every target without creating N+1 queries.
- Background jobs must re-evaluate authorization context or operate from an approved immutable job scope; request sessions cannot be reused.
