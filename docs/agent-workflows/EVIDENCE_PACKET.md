# Evidence Packet Template

Use for non-trivial work before writing the change contract. Keep it concise and link to live source.

```markdown
# Evidence Packet: <task ID and title>

## Scope inspected
- Relevant root/scoped rules:
- Canonical spec/requirements:
- Accepted ADRs:

## Live implementation
- Models/schemas:
- Routes/contracts:
- Services/repositories:
- Frontend consumers:
- Existing tests:
- Relevant configuration/dependencies:

## Baseline
- Command:
- Exit code:
- Relevant output/counts:
- Pre-existing failures:

## Findings
- Current behavior:
- Ownership/security boundary:
- Similar implementation available for reuse:
- SPEC_DRIFT or contradictions:
- Unknowns requiring approval:
```

Do not copy large source files into the packet. Use paths, symbols, and exact command evidence.

