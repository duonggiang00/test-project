# Engineering Handoff Template

```markdown
# Handoff: <task ID and title>

Status: DONE | REVIEW | BLOCKED
Risk level:

## Outcome
- Summary:
- Requirements/task IDs:

## Files changed
- `<path>` — purpose

## Verification
| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|

## Impact
- API/event/schema contract:
- Migration/data:
- Security/ownership/tenant:
- Dependency/toolchain:

## Manual evidence
- Scenario:
- Result:
- Screenshot/trace:

## Risks and follow-up
- Known risks:
- Unverified items:
- Follow-up tasks:

## Rollback
- Code:
- Data:
```

Use `DONE` only when every required verification item has direct evidence. Use `REVIEW` when implementation is ready but independent review or an executable gate remains. Use `BLOCKED` when a required condition cannot be satisfied.

