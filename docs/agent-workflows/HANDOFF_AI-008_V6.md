# AI-008 V6 Handoff

Status: `BLOCKED_REVIEW_QUOTA`

## Completed

- V5 is preserved as an immutable blocked campaign. Its five-call replay
  passed format 5/5, citations 5/5, injection resistance 5/5, refusal 1/1,
  but safe continuation was 4/5 because `qgen-006` failed.
- V6 is implemented in commit `75b5521` on `codex/ai-008-v6`.
- V6 adds an explicit question-generation deliverable contract and requires
  direct-clause refusal as the first sentence inside the JSON `answer` value.
- Focused AI tests: 61 passed. Ruff, Mypy, architecture guard, diff check,
  and canonical fast gate: passed (13/13; backend unit 455/455,
  backend contract 24/24, frontend unit 182/182).

## Required before live calls

1. Obtain an independent L3 review of commit `75b5521`.
2. Run V6 `baseline-001` with `--max-new-calls 5` only.
3. Review the five sanitized attempts and run the failure-replay checkpoint.
4. Continue only if the checkpoint report passes and its hashes match.

Use compact manifests under `backend/reports/agent-workflow/` and ignored
campaign evidence under `backend/reports/ai-evaluation/ai-008-v6/`. Do not
resume V5 or alter V1-V5 evidence. Do not activate CI thresholds without
separate owner approval.
