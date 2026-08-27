# AI-006 Owner Approval Record

Status: APPROVED

Approval date: 2026-08-28

Approval source: Project owner in the active Codex task

Approved target: `v1.jsonl`

Schema: `1.0`

Cases: 40

Canonical SHA-256:
`4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51`

## Distribution

| Case range | Use case | Count |
|---|---|---:|
| `rag-001`–`rag-016` | RAG/chat | 16 |
| `qgen-001`–`qgen-012` | Question generation | 12 |
| `flash-001`–`flash-006` | Flashcard generation | 6 |
| `brief-001`–`brief-006` | Topic brief generation | 6 |

The draft is Vietnamese-first and covers mathematics, Python foundations,
academic reading, and academic writing. Safety coverage includes direct and
indirect prompt-injection cases across retrieval and generation workloads.

## Owner checklist

- Reference facts and expected answers are educationally correct.
- Rubrics express the intended output quality without requiring facts outside
  the supplied context.
- Direct and indirect injection cases expect refusal of the unsafe instruction
  while preserving the legitimate learning task.
- No case includes real personal data, credentials, private source content, or
  production data.
- The fingerprint printed by a fresh structure validation exactly matches the
  value above.

The owner explicitly approved the full fingerprint above on 2026-08-28. The
draft was promoted to `v1.jsonl`, and `v1.approval.json` records the matching
decision metadata. Any semantic dataset change requires a new fingerprint and
a new explicit owner/admin approval.
