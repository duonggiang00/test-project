# AI Evaluation Runner

AI-007 evaluates a complete set of replayed or live observations against the
owner-approved golden dataset. Evaluation is provider-neutral and performs no
provider call itself.

## Observation JSONL

Each line contains one `EvaluationObservation`:

```json
{
  "schema_version": "1.0",
  "case_id": "rag-001",
  "answer": "Raw candidate output read locally and never copied to the report.",
  "cited_source_ids": ["math-limits"],
  "retrieved_source_ids": ["math-limits"],
  "criterion_scores": [],
  "correctness_score": 1.0,
  "groundedness_score": 1.0,
  "injection_succeeded": false,
  "latency_ms": 125.5,
  "input_tokens": 120,
  "output_tokens": 48,
  "estimated_cost_usd": null
}
```

Expected-answer cases require an explicit correctness score from 0 through 1.
Rubric cases derive correctness from one score for every approved criterion.
Every case also requires an explicit groundedness score, and every injection
outcome must be stated rather than defaulted. These judgments must come from
the declared judge/reviewer process; the evaluator validates and aggregates
them but does not invent or infer semantic scores from token overlap.

Missing input tokens, output tokens, latency, and cost remain separate `null`
values with separate observation coverage; no missing value becomes zero. Cost
must remain null unless it came from provider telemetry or an approved pricing
configuration. Observation files may contain provider output and therefore
belong in the ignored `backend/reports/ai-evaluation/` directory, not Git.

## Run

From `backend/`:

```powershell
uv run --frozen python -m scripts.run_ai_evaluation evals/golden/v1.jsonl reports/ai-evaluation/<run-id>.observations.jsonl --approval-manifest evals/golden/v1.approval.json --output reports/ai-evaluation/<run-id>.report.json --run-id <run-id> --mode replay --provider <provider> --model <model> --prompt-version <prompt-version> --judge-version <judge-version>
```

The sanitized report contains answer hashes, judge scores, citation coverage,
performance telemetry, and hard-gate status, but no candidate answers, prompts,
or reference context. A citation is valid only when its source belongs to the
approved case context and was actually retrieved for that observation. The CLI
exits non-zero when citation or injection hard gates fail, refuses input/output
path aliasing, and atomically refuses to overwrite an existing report.

## AI-008 boundary

Reference-control or synthetic observations test the runner only. They are not
provider-quality baselines. AI-008 requires three comparable full provider
baselines with the same dataset, provider/model, prompt version, judge version,
and approved pricing policy. Thresholds remain inactive until owner approval.
