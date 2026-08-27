# Change Contract: AI-006 Simple Golden Dataset Approval

Risk level: L3 AI evaluation data and approval workflow

Owner: Project owner

Implementation owner: Primary coding agent

Independent review: Required before completion

Decision date: 2026-08-28

## Goal

Complete the AI-006 golden-dataset preparation with a review workflow that is
practical during development: the agent drafts and validates all 40 cases, and
the project owner approves one exact SHA-256 fingerprint for the complete
dataset.

## Scope

- Replace per-case Ed25519 signatures and the trusted-key store with a strict,
  dataset-level approval manifest bound to the canonical dataset fingerprint.
- Keep strict schema validation, deterministic fingerprints, source-reference
  validation, duplicate detection, distribution checks, and secret scanning.
- Create a Vietnamese-first draft containing exactly 40 cases:
  16 RAG/chat, 12 question-generation, 6 flashcard-generation, and 6
  topic-brief-generation cases.
- Provide a compact owner review document and an approval-manifest template.
- Update AI-006 documentation, tests, tracker state, and handoff evidence.

## Out of scope

- AI-007 evaluation execution, AI-008 quality thresholds, semantic retrieval,
  provider calls, application API changes, database changes, migrations,
  authentication, authorization, or product behavior.
- Treating agent-authored content as owner-approved without an explicit owner
  decision on the exact fingerprint.
- Cryptographic proof of approver identity or non-repudiation in the development
  workflow.

## Constraints

- Code, schemas, CLI output, documentation, and handoff records remain English.
- The approval manifest is accepted only when its lowercase SHA-256 value
  exactly matches the validator's canonical dataset fingerprint.
- Dataset content is canonicalized independently of JSONL line order so a
  reorder alone does not invalidate approval.
- A content change, case addition/removal, or case-field change invalidates the
  existing approval manifest.
- Validation failures must not print raw case content, secrets, or absolute
  local paths.
- The Git and review history records who approved the manifest. The manifest is
  an integrity binding, not a cryptographic identity credential.

## Acceptance

- The draft has exactly 40 valid cases in the approved distribution.
- Structure-only validation works without an approval manifest and clearly
  reports that the dataset is not approved.
- Final validation fails for a missing, malformed, stale, or mismatched approval
  manifest and succeeds only for an exact fingerprint match.
- Tests cover deterministic output, tampering, validation errors, safe failure
  messages, secret rejection, and CLI behavior.
- The owner receives the exact fingerprint and a short review checklist.
- AI-006 remains pending owner approval until the owner explicitly approves that
  fingerprint; downstream AI-007/AI-008 work remains blocked until then.

## Verification

- Focused golden-dataset unit and CLI tests.
- Ruff and mypy for changed backend Python files.
- Structure validation of the complete 40-case draft.
- Canonical affected backend gate and `git diff --check`.
- Independent L3 AI/security review confirms that validation was not weakened
  beyond the explicitly accepted identity-proof tradeoff.

## Approval boundary and tradeoff

The owner explicitly requested this simplified development workflow on
2026-08-28. Ed25519 key generation, private-key custody, public-key pinning, and
per-case signatures are removed from AI-006. The accepted tradeoff is that the
repository records approval through the owner's explicit decision and Git/PR
history, while the manifest proves only that the reviewed dataset bytes have not
changed semantically after approval.

## Rollback

Revert the scoped AI-006 commit. No database, migration, application API, or
production data rollback is required.

## Completion evidence

The project owner explicitly approved the complete dataset fingerprint
`4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51` on
2026-08-28. `v1.approval.json` records that decision, and final validation
reports 40 cases with `approval_record_matched=true`.
