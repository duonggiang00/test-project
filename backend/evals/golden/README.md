# AI Golden Dataset v1

This directory is reserved for the owner/admin-approved AI evaluation dataset.
No agent-authored case may be committed here as approved reference content.

Each UTF-8 JSONL line must satisfy `app.ai.evaluation.dataset.GoldenDatasetCase`:

- `schema_version`: `"1.0"`.
- `case_id`: stable lowercase identifier.
- `use_case`: `rag_chat`, `question_generation`, `flashcard_generation`, or
  `topic_brief_generation`.
- `language`: explicit BCP-47-like language code; the approved initial dataset
  is Vietnamese-first.
- `input`: safe evaluation input with no raw secrets.
- `reference_context`: zero or more `{source_id, content}` records.
- `expected_answer` or `rubric`: at least one approved reference signal.
- `required_source_ids`: citations that must refer to `reference_context` IDs.
- `injection_label`: `none`, `direct`, or `indirect`.
- `sensitivity`: `public`, `internal`, `personal`, or `sensitive`.
- `approval`: human `owner` or `admin` identity, timezone-aware approval time,
  approval version, trusted `key_id`, and an Ed25519 signature over the
  canonical case payload.

The trust store is a separate owner-controlled JSON file:

```json
{
  "schema_version": "1.0",
  "approvers": [
    {
      "key_id": "owner-key-2026",
      "approval_source": "owner",
      "approved_by": "project-owner-001",
      "public_key_base64": "<owner-provided-32-byte-ed25519-public-key>"
    }
  ]
}
```

The matching private key must never enter the repository, agent context,
command output, or CI secrets available to pull requests. Adding or rotating a
trusted public key is an owner-controlled governance change. The owner/admin
must also pin the canonical trust-store fingerprint in the protected
`AI_GOLDEN_DATASET_TRUST_ROOT_SHA256` environment setting. A caller-supplied
trust store cannot produce an approved result unless its canonical SHA-256
matches that external trust root. Local agent-selected environment values are
not authoritative completion evidence.

The complete dataset must contain exactly 40 cases using the approved current
mix: 16 RAG/chat, 12 question-generation, 6 flashcard-generation, and 6
topic-brief-generation cases. The validator deliberately does not infer whether
Vietnamese prose is correct; human approval is the authority for reference
content.

Validate a complete dataset from `backend/`:

```text
$env:AI_GOLDEN_DATASET_TRUST_ROOT_SHA256='<owner-approved-trust-store-sha256>'
uv run --frozen python -m scripts.validate_ai_golden_dataset evals/golden/v1.jsonl --trust-store <owner-controlled-trust-store.json>
```

During owner/admin review, `--allow-partial` validates signed cases without
claiming that AI-006 is complete. `--structure-only` can check unsigned drafts,
but it emits `AI_GOLDEN_DATASET_STRUCTURE_OK` and
`approvals_verified=false`, never the approved success status. The command
reports only counts and a canonical SHA-256 fingerprint; it never prints case
content or filesystem paths in validation failures. Approved output also prints
the trust-root fingerprint so evidence can be matched to the owner-pinned
protected setting.
