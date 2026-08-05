# Change Contract: GUARD-009 — OpenAPI Contract Diff

Risk level: L1 gate; API breaking changes remain approval-gated
Owner: Primary Codex agent
Approval required: No for the gate

## Intent

Generate the complete registered FastAPI OpenAPI document deterministically and fail fast verification whenever the committed contract differs from runtime.

## Review boundary

Regeneration is never an automatic green fix. Review the JSON diff for paths, methods, request/response schemas, security, and status contracts. Breaking changes require project-owner approval before the generated contract is updated.
