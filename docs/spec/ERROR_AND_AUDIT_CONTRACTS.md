# Error and Audit Contracts

Status: Approved  
Date: 2026-08-05  
Parent specification: [`CANONICAL_PROJECT_SPEC.md`](CANONICAL_PROJECT_SPEC.md)

## 1. API error contract

All expected application errors use a stable machine-readable code and structured details. The backend does not own user-facing localization.

### 1.1 Response shape

```json
{
  "error_code": "EXAM_NOT_FOUND",
  "details": {
    "exam_id": "8f37b4ca-2014-4cec-aa2d-3f967c27eb8e"
  },
  "request_id": "01J5Y2Q4NQ3K2V7K6D4B0MPH14"
}
```

Fields:

| Field | Required | Contract |
|---|---:|---|
| `error_code` | Yes | Stable uppercase `SCREAMING_SNAKE_CASE` identifier |
| `details` | Yes | JSON object containing safe structured context; use `{}` when empty |
| `request_id` | Yes | Correlation identifier usable in logs and support workflows |

The response must not expose stack traces, SQL, provider secrets, tokens, internal filesystem paths, or sensitive cross-owner identifiers.

### 1.2 Error-code ownership

- Backend defines and emits error codes.
- Frontend maps codes to English user-facing messages.
- Frontend must provide a safe generic fallback for unknown codes.
- Code meaning must not change after release. Introduce a new code when semantics differ.
- `details` may support interpolation but must not contain the final localized sentence.

### 1.3 HTTP status guidance

| Status | Use |
|---:|---|
| 400 | Malformed operation not represented by field validation |
| 401 | Missing, expired, revoked, or invalid authentication |
| 403 | Authenticated actor is categorically forbidden and existence disclosure is safe |
| 404 | Resource absent or ownership-safe non-disclosure response |
| 409 | State/version/uniqueness conflict |
| 413 | Upload exceeds the 50 MB limit |
| 415 | Unsupported or invalid file media type |
| 422 | Structured request validation failure |
| 429 | Rate limit exceeded |
| 500 | Sanitized unexpected server failure |
| 502/503 | Sanitized dependency/provider failure when applicable |

Cross-owner identifier probing should normally use a not-found response when returning `403` would reveal the existence of a private resource.

### 1.4 Validation errors

Normalize request validation failures to the same top-level contract:

```json
{
  "error_code": "VALIDATION_ERROR",
  "details": {
    "fields": [
      {
        "path": "password",
        "rule": "min_length",
        "context": { "minimum": 8 }
      }
    ]
  },
  "request_id": "01J5Y2Q4NQ3K2V7K6D4B0MPH14"
}
```

Do not expose framework-specific exception serialization as a public contract without normalization.

### 1.5 AI/provider errors

Provider failures are reported immediately with stable application codes such as:

- `AI_PROVIDER_UNAVAILABLE`.
- `AI_REQUEST_TIMEOUT`.
- `AI_OUTPUT_INVALID`.
- `AI_CONTENT_REQUIRES_REVIEW`.

Provider-specific raw messages are logged only after sanitization and are not sent directly to users.

## 2. Audit event contract

Audit events are append-only records of security-sensitive or business-significant actions. They are not general application debug logs.

### 2.1 Event shape

```json
{
  "event_id": "01J5Y2Q4NQ3K2V7K6D4B0MPH14",
  "occurred_at": "2026-08-05T10:15:30.000Z",
  "request_id": "01J5Y2PY6GPH3XEBKAMJPCY4V4",
  "actor": {
    "user_id": "fdb64326-13ec-4ea0-a40d-504038601992",
    "role": "teacher"
  },
  "action": "exam.publish",
  "entity": {
    "type": "exam",
    "id": "8f37b4ca-2014-4cec-aa2d-3f967c27eb8e",
    "owner_id": "fdb64326-13ec-4ea0-a40d-504038601992"
  },
  "outcome": "success",
  "changes": {
    "is_published": { "before": false, "after": true }
  },
  "metadata": {}
}
```

### 2.2 Required fields

| Field | Contract |
|---|---|
| `event_id` | Immutable unique identifier |
| `occurred_at` | UTC timezone-aware timestamp |
| `request_id` | Request/job correlation identifier |
| `actor` | Actor ID and role; support an explicit system actor for jobs |
| `action` | Stable dotted action name such as `exam.publish` |
| `entity` | Entity type, ID, and owner when applicable |
| `outcome` | `success`, `denied`, or `failure` |
| `changes` | Safe structured before/after fields or `{}` |
| `metadata` | Safe action-specific context or `{}` |

### 2.3 Required events

- User creation, disablement, role change, and administrative update.
- Authentication revocation, suspicious refresh replay, and sensitive logout events.
- Topic, material, exam, question, flashcard, and brief create/update/delete/restore.
- Publish and unpublish.
- Submission grading and grade override.
- AI generation request, completion, failure, approval, rejection, and publication.
- File upload, rejection, delete, restore, and purge.
- Admin ownership override.
- Soft-delete restoration and permanent purge.

High-volume read events are not automatically audited. Sensitive audit-log access and cross-owner admin access should be audited.

### 2.4 AI metadata

AI audit events may include:

```json
{
  "prompt_version": "exam-generation-v3",
  "provider": "configured-provider",
  "model": "configured-model",
  "input_tokens": 1200,
  "output_tokens": 450,
  "estimated_cost": "0.0123",
  "latency_ms": 1840,
  "context_source_ids": ["material-id"],
  "reviewer_id": "user-id",
  "review_outcome": "approved"
}
```

Raw prompts and retrieved content are sensitive payloads. If stored, they must use restricted storage, redaction, access control, and a separately approved retention policy. The core audit record should prefer prompt version and safe references over duplicating raw sensitive content.

### 2.5 Data minimization

Never store in audit fields:

- Passwords or password hashes.
- Access/refresh tokens or cookie values.
- Secret keys or provider credentials.
- Full uploaded document contents.
- Unredacted sensitive prompts unless an approved restricted-log policy requires them.
- Arbitrary request/response bodies.

IP address and user-agent collection, if introduced, must have a documented purpose and retention rule.

### 2.6 Transaction behavior

- A successful business action and its required audit event must be atomic when stored in the same database.
- A denied action may be recorded outside the rejected business transaction through a safe audit path.
- Audit write failure for a required successful action must not silently produce an unaudited success.
- Background/system actions use an explicit system actor and job/request correlation ID.

### 2.7 Immutability and access

- Application workflows do not update or delete individual audit events.
- Only authorized admins may read the complete audit log.
- Teachers may read audit events for owned resources only when that feature is implemented.
- Audit queries enforce the same ownership isolation as business-resource queries.
- Permanent audit retention is not yet approved; purge must remain disabled until a retention ADR is accepted.

## 3. Required contract tests

- Every expected error returns `error_code`, object `details`, and `request_id`.
- Unknown frontend error codes render a safe English fallback.
- Cross-owner failures do not leak resource existence or sensitive identifiers.
- Unexpected exceptions are sanitized while retaining the request ID.
- Required successful mutations create one corresponding audit event.
- Failed transactions do not leave a false success audit event.
- Admin overrides record both actor and original owner.
- Secrets and tokens do not appear in serialized audit data.
- AI audit records contain the approved metadata without leaking sensitive raw provider errors.

