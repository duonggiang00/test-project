# Handoff: AI-007 Deterministic Evaluation Runner

Status: DONE

Risk level: L3 governed AI evaluation

## Outcome

- Added a strict, versioned, provider-neutral observation contract and evaluator
  for the owner-approved 40-case golden dataset.
- The evaluator reports correctness, groundedness, citation validity, required
  citation coverage, context relevance, injection resistance, latency, separate
  input/output token coverage, and estimated cost coverage.
- Complete case coverage, perfect citation validity/required coverage, and
  injection resistance are hard gates. Quality thresholds remain outside
  AI-007 and inactive.
- Reports contain answer SHA-256 hashes and metrics, never candidate answers,
  prompts, or reference context. Secret-like observation, dataset, and run data
  fail through sanitized errors.
- Added `docs/plans/AI-008_BASELINE_AND_THRESHOLD_PACKET.md` to make the next
  owner decision explicit without treating synthetic control data as provider
  quality evidence.

## Evaluation contract

- Exactly one observation is required for every approved case; missing,
  duplicate, and unknown cases fail safely.
- Expected-answer cases require an explicit correctness judgment. Rubric cases
  require exactly one bounded score per approved criterion. Every case requires
  an explicit groundedness judgment and injection outcome.
- A citation is valid only when its source belongs to the approved case context
  and was retrieved for that observation.
- Missing latency, input tokens, output tokens, and cost remain independent null
  values with independent coverage counts. Cost is never inferred from an
  unapproved price.
- Report output is published with an atomic create-if-absent hard link from an
  fsynced same-directory temporary file. Existing or concurrently created
  reports are preserved, and temporary files are cleaned on failure.

## Verification

| Command | Result |
|---|---|
| `python -m pytest -p no:cacheprovider tests/unit/test_ai_evaluation_runner.py tests/unit/test_ai_golden_dataset.py -q` | 57/57 passed, including three identical complete replays, order independence, strict-input failures, secret redaction, hard-gate failures, and atomic no-overwrite behavior |
| `python -m ruff check app/ai/evaluation scripts/run_ai_evaluation.py scripts/validate_ai_golden_dataset.py tests/unit/test_ai_evaluation_runner.py tests/unit/test_ai_golden_dataset.py` | Passed |
| `python -m mypy --follow-imports=skip app/ai/evaluation/dataset.py app/ai/evaluation/runner.py scripts/run_ai_evaluation.py scripts/validate_ai_golden_dataset.py` | Passed |
| `node scripts/verify.mjs backend --compact --task ai-007-evaluator-final` | 5/5 passed; 385 unit, 24 contract, and 171 PostgreSQL integration tests; manifest `reports/agent-workflow/ai-007-evaluator-final/backend.json` |
| `node scripts/verify.mjs fast --compact --task ai-007-evaluator-final-fast` | 13/13 passed; 385 backend unit, 24 contract, 182 frontend tests, and production build; manifest `reports/agent-workflow/ai-007-evaluator-final-fast/fast.json` |
| `node scripts/project-inventory.mjs check` | Passed with 456 relevant files and source-tree SHA-256 `3a3abf3950873306f93651f3873b32a7e3e21f7172164fb1533130d045af3aa4` |
| `git diff --check` | Passed |

Independent L3 review approved the stabilized implementation with no remaining
P1/P2/P3 findings. The reviewer independently confirmed the approved dataset
fingerprint, strict runtime revalidation, secret-safe failures, citation and
injection semantics, null telemetry behavior, report sanitization, and atomic
no-overwrite publication.

## Impact and rollback

- No application API, database schema, migration, authentication,
  authorization, retrieval behavior, provider/model policy, or product behavior
  changed.
- Revert the scoped AI-007 commit to remove the evaluator and its documentation.
  Evaluation inputs/reports are ignored local files, so no application data
  rollback is required.
- Accepted residual risks: semantic judgments depend on the declared external
  judge/reviewer process; secret detection is heuristic; report publication
  requires same-filesystem hard-link support and fails safely when unavailable.

## Follow-up

- AI-008 is the next gated item. Run three comparable full provider baselines
  using the same dataset, provider/model, prompt version, judge version, scoring
  schema, and telemetry policy.
- The owner must approve quality/regression thresholds, latency/token caps, the
  live subset/schedule, and either an authoritative pricing source or explicit
  null cost gating before CI enforcement is implemented.
- RAG-SEMANTIC-001 remains downstream of AI-008 and must not become the default
  retrieval path before those evaluation gates are accepted.
