# Handoff: AI-006 Golden Dataset Validator

Status: BLOCKED
Risk level: L3

## Outcome

- Summary: Implemented the versioned AI golden-dataset schema and read-only
  validator without creating or self-approving reference content.
- Requirements/task IDs: AI-006 technical foundation.
- Blocker: No owner-controlled trusted public key, protected trust-root
  fingerprint, or signed owner/admin-approved reference cases are configured.
  AI-006 requires all three before it can become `DONE`.

## Files changed

- `backend/app/ai/evaluation/dataset.py` — strict v1 models, Ed25519 approval
  verification, secret screening, safe file handling, reference checks,
  distribution enforcement, and canonical fingerprint.
- `backend/app/ai/evaluation/__init__.py` — evaluation package exports.
- `backend/scripts/validate_ai_golden_dataset.py` — safe read-only CLI.
- `backend/evals/golden/README.md` — authoring and approval boundary.
- `backend/tests/unit/test_ai_golden_dataset.py` — deterministic positive and
  negative coverage using test-only synthetic data.
- `docs/plans/AI-001-009_CHANGE_CONTRACT.md` and optimization tracker — current
  evidence and blocker.

## Verification

| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `uv run --frozen pytest -q -p no:cacheprovider tests/unit/test_ai_golden_dataset.py` | 0 | 28 | 28 | 0 | 0 | Schema, distribution, external trust-root pin, signed trust, forgery/identity rejection, recursive common-secret screening, safe file errors, fingerprint, rubric, and CLI modes pass. |
| `uv run --frozen ruff check app/ai/evaluation scripts/validate_ai_golden_dataset.py tests/unit/test_ai_golden_dataset.py` | 0 | — | — | — | — | All checks passed. |
| `uv run --frozen mypy --follow-imports=skip app/ai/evaluation/dataset.py scripts/validate_ai_golden_dataset.py` | 0 | — | — | — | — | No issues in the two new typed source files. |
| `node scripts/verify.mjs fast --compact --task ai-006-validator-trust-root` | 0 | 562 | 562 | 0 | 0 | All 13 canonical steps pass after trust-root remediation: backend unit 356, backend contract 24, frontend Jest 182, and production build. |

## Impact

- API/event/schema contract: No application API or event change. The JSONL
  evaluation format is new and versioned as `1.0`.
- Migration/data: No database access, schema change, migration, or approved
  dataset data added.
- Security/ownership/tenant: Approval claims must match an Ed25519 trust-store
  identity/signature and its canonical SHA-256 must match an externally pinned
  owner-controlled setting. All string fields are screened for common
  provider/PAT/JWT/database secret formats; failures do not echo payloads or
  paths.
- Dependency/toolchain: No dependency or lockfile change.

## Manual evidence

- Scenario: Validate a partial, test-only approved-shape case through the CLI.
- Result: The command reports only schema version, counts, distribution, and a
  SHA-256 fingerprint; it does not print case content.
- Screenshot/trace: Not applicable to this backend-only tooling change.

## Risks and follow-up

- Known risks: A valid signature proves which trusted key approved an exact
  payload; it cannot prove the educational correctness of Vietnamese reference
  prose. Human review remains authoritative, and private keys stay external.
- Unverified items: No real reference content, provider output, quality metric,
  live latency, token usage, or cost baseline was evaluated.
- Independent review: APPROVED with no remaining P1/P2/P3. The first review
  rejected self-declared approval, incomplete secret patterns, and unsafe file
  errors. The second review required an external trust-root anchor and recursive
  identifier scanning. Ed25519 payload signatures, protected root fingerprint
  matching, expanded recursive secret screening, sanitized errors, and their
  regression tests closed every finding.
- Follow-up tasks: Owner/admin supplies the trusted public key, pins its
  canonical fingerprint in protected configuration, retains the private key
  outside repository/agent/PR context, reviews and signs the 40 JSONL cases,
  and reruns the complete validator. Then implement AI-007, establish three
  accepted baselines for AI-008, and only then begin RAG-SEMANTIC-001.

## Rollback

- Code: Revert the AI-006 validator commit.
- Data: None; no approved dataset or database data was created.
