# Task Risk Classification

Use the highest applicable level. Risk level controls approval, review, and verification; it does not estimate effort alone.

## L0 — Documentation or non-behavioral maintenance

Examples: canonical documentation, typo corrections, comments, formatting, generated metadata refresh.

- Prior approval: No.
- Implementation: One agent.
- Review: Self-review.
- Minimum verification: Links, format/schema, consistency, and scoped diff.

## L1 — Local behavior with a narrow boundary

Examples: pure utility, isolated component, hook/service correction, non-breaking validation improvement.

- Prior approval: No.
- Implementation: One agent.
- Review: Self-review; optional lightweight independent review.
- Minimum verification: Targeted behavior test plus applicable lint/type checks.

Escalate if the change affects authentication, ownership, persistence schema, or a public contract.

## L2 — Cross-layer or public non-breaking behavior

Examples: endpoint plus frontend consumer, new user flow, new background job, material query change, non-breaking OpenAPI addition.

- Prior approval: Required only if the contract or plan changes materially.
- Implementation: One primary owner; subagent only if the work is independently separable.
- Review: Independent diff review.
- Minimum verification: Targeted tests, contract/integration tests, static checks, build, and affected E2E.

## L3 — Security, data, or governed AI behavior

Examples: authentication lifecycle, RBAC/ownership, tenant isolation, migration, soft delete/purge, audit storage, file-security boundary, AI grading or sensitive retrieval.

- Prior approval: Required before implementation.
- Implementation: Primary specialist owner; bounded supporting agents allowed.
- Review: Independent security/data/domain review as applicable.
- Minimum verification: Negative authorization/security tests, PostgreSQL integration, migration round trip when applicable, affected E2E, and rollback evidence.

## L4 — Breaking or high-impact architecture

Examples: breaking API, auth architecture replacement, destructive migration, provider/platform replacement, security incident remediation with broad impact.

- Prior approval: Accepted ADR and explicit implementation approval.
- Implementation: Staged plan with named ownership and rollback checkpoints.
- Review: Independent architecture plus security/data review.
- Minimum verification: Full affected regression set, migration/rollback rehearsal, contract compatibility analysis, and deployment/monitoring plan.

## Escalation rules

- Choose the higher level when uncertain.
- Discovery of a higher-risk impact pauses implementation until the change contract and approval are updated.
- A task may be split only when each child has an independently testable contract.
- Splitting work does not reduce the risk classification of a security/data boundary.

## Affected-behavior verification matrix

Apply every row that matches the change in addition to the minimum risk-level verification above.

| Changed behavior | Required verification |
|---|---|
| Pure backend or frontend logic | Focused unit tests |
| Backend use case or endpoint | Contract tests, including negative authorization where applicable |
| Query, constraint, or transaction behavior | PostgreSQL integration and a query-budget/concurrency test when relevant |
| Migration | Upgrade, downgrade, upgrade; model-drift check |
| Frontend component | Behavior and accessibility component tests |
| Server/client boundary or hydration | Focused test and production build |
| Routing, authentication UX, or user flow | Navigation E2E from the real entry point |
| Layout or styling | Desktop and mobile visual regression |
| Security, ownership, or tenant boundary | Adversarial/IDOR cases and independent specialist review |

During implementation, run the closest affected test after each coherent edit. Run the complete affected domain or cross-layer gate once after the code stabilizes. A prior passing result may be reused only when the verification manifest confirms an identical command and source/toolchain fingerprint; PostgreSQL integration, migration, coverage, and E2E results are never reused.
