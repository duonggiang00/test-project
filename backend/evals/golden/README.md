# AI Golden Dataset v1

AI-006 uses a deliberately simple development approval workflow:

1. An agent or contributor drafts the complete JSONL dataset.
2. The validator checks the schema, case distribution, references, rubric
   weights, duplicate IDs, and secret-like content, then prints a canonical
   SHA-256 fingerprint.
3. The project owner reviews the draft and explicitly approves that exact
   fingerprint.
4. An approval manifest records the owner decision. Final validation succeeds
   only while its `dataset_sha256` exactly matches the current dataset.

The manifest binds approval to content integrity. Approver identity comes from
the owner's recorded Git/PR decision; this development workflow does not claim
cryptographic non-repudiation.

## Case contract

Each UTF-8 JSONL line satisfies
`app.ai.evaluation.dataset.GoldenDatasetCase` and contains:

- `schema_version`, stable `case_id`, `use_case`, and `language`;
- safe `input` and `reference_context` records;
- either `expected_answer` or a weighted `rubric`;
- `required_source_ids` that resolve inside the case;
- `injection_label` and `sensitivity` classifications.

The complete dataset contains exactly 40 cases: 16 RAG/chat, 12
question-generation, 6 flashcard-generation, and 6 topic-brief-generation.
The initial draft is Vietnamese-first.

## Commands

From `backend/`, validate a future draft and obtain its review fingerprint:

```text
uv run --frozen python -m scripts.validate_ai_golden_dataset evals/golden/<version>.draft.jsonl --structure-only
```

This emits `AI_GOLDEN_DATASET_STRUCTURE_OK` and
`approval_record_matched=false`; it never claims owner approval.
Use `--allow-partial` only together with `--structure-only` while assembling a
draft. Partial datasets can never produce the approved success status.

After the owner approves the exact fingerprint, create the matching approval
manifest:

```json
{
  "schema_version": "1.0",
  "dataset_sha256": "<exact-lowercase-sha256-from-structure-validation>",
  "approval_source": "owner",
  "approved_by": "project-owner",
  "approved_at": "<timezone-aware-ISO-8601-time>",
  "approval_version": "ai-006-v1"
}
```

The current approved v1 dataset is validated with:

```text
uv run --frozen python -m scripts.validate_ai_golden_dataset evals/golden/v1.jsonl --approval-manifest evals/golden/v1.approval.json
```

Final success emits `AI_GOLDEN_DATASET_OK` and
`approval_record_matched=true`. Any semantic case change invalidates the old
manifest. JSONL line reordering alone does not change the fingerprint. Failures
report safe metadata only and do not print raw case content or local paths.
