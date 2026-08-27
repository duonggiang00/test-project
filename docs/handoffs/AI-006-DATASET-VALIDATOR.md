# Handoff: AI-006 Golden Dataset Owner Review

Status: DONE
Risk level: L3

## Outcome

- Replaced the development-only Ed25519 key ceremony with a strict,
  dataset-level approval manifest at the owner's request.
- Authored a complete Vietnamese-first draft with 40 cases in the required
  16 RAG/chat, 12 question-generation, 6 flashcard-generation, and 6
  topic-brief-generation distribution.
- Canonical draft SHA-256:
  `4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51`.
- The owner explicitly approved that exact fingerprint on 2026-08-28. The
  dataset is promoted to `v1.jsonl`, the matching `v1.approval.json` is present,
  and final validation reports `approval_record_matched=true`.

## Approval workflow

1. The owner reviewed `backend/evals/golden/v1.draft.jsonl` using
   `backend/evals/golden/OWNER_REVIEW.md`.
2. The owner explicitly approved the complete fingerprint above.
3. The implementation owner promoted the draft to `v1.jsonl`, created
   `v1.approval.json`, and ran final validation.
4. Final success reports `AI_GOLDEN_DATASET_OK`,
   `approval_record_matched=true`, and the same fingerprint. AI-006 is `DONE`.

The manifest provides content-integrity binding, not cryptographic proof of
identity. Approver identity is established by the owner's recorded decision and
Git/PR history. This tradeoff is explicitly accepted for the development phase
in `docs/plans/AI-006_SIMPLE_APPROVAL_CHANGE_CONTRACT.md`.

## Verification

| Command | Result |
|---|---|
| `python -m pytest -p no:cacheprovider tests/unit/test_ai_golden_dataset.py -q` | 29/29 passed after closing the partial-approval review finding |
| `python -m ruff check app/ai/evaluation scripts/validate_ai_golden_dataset.py tests/unit/test_ai_golden_dataset.py` | Passed |
| `python -m mypy --follow-imports=skip app/ai/evaluation/dataset.py scripts/validate_ai_golden_dataset.py` | Passed |
| `python scripts/validate_ai_golden_dataset.py evals/golden/v1.draft.jsonl --structure-only` | 40 cases valid; exact distribution and fingerprint confirmed |
| `python scripts/validate_ai_golden_dataset.py evals/golden/v1.jsonl --approval-manifest evals/golden/v1.approval.json` | `AI_GOLDEN_DATASET_OK`; 40 cases; `approval_record_matched=true`; approved fingerprint matched |
| `node scripts/verify.mjs backend --compact --task ai-006-simple-approval-final` | 5/5 steps passed; backend 357 unit + 24 contract + 171 PostgreSQL integration tests passed |
| `node scripts/verify.mjs fast --compact --task ai-006-simple-approval-final-fast` | 13/13 steps passed; backend 357 unit + 24 contract, frontend 182 tests, production build passed |
| `node scripts/project-inventory.mjs check` | Current inventory passed with 453 files |
| `git diff --check` | Passed |

The first direct draft-validation attempt from the repository root failed with
`ModuleNotFoundError: app` because `PYTHONPATH` was scoped to the root. The
canonical command from `backend/` then passed; this was a command-environment
error, not a dataset or application failure.

## Impact and rollback

- No application API, database, migration, authentication, authorization,
  provider, or product behavior changed.
- Validation still rejects malformed cases, wrong distributions, duplicate or
  unknown references, invalid rubric weights, secret-like content, unsafe file
  reads, missing manifests, and stale or mismatched fingerprints.
- Approved validation rejects partial datasets at both the library and CLI
  layers; `--allow-partial` is valid only with `--structure-only`.
- Revert the scoped AI-006 changes to restore the former validator. No data
  rollback is required.

## Follow-up

- AI-007 is now unblocked. AI-008 remains dependent on accepted baselines, and
  RAG-SEMANTIC-001 remains dependent on AI-007 and AI-008.
- Independent L3 review found and rejected a path that could mark a partial
  dataset approved. The implementation and two negative tests closed that
  finding. Final review is approved with no remaining P1/P2/P3 code or security
  findings. Owner approval and matching-manifest validation are now complete.
