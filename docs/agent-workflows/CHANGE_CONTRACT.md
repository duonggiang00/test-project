# Change Contract Template

Create before non-trivial implementation and update when assumptions change.

```markdown
# Change Contract: <task ID and title>

Risk level: L0 | L1 | L2 | L3 | L4
Owner:
Approval required: Yes | No
Approval evidence:

## Scope
- In scope:
- Out of scope:

## Behavior
- Before:
- After:
- Preserved invariants:

## Expected files and contracts
- Files/modules:
- API/event/schema impact:
- Migration/data impact:
- Security/ownership/tenant impact:

## Verification contract
- Targeted tests:
- Static/type checks:
- Integration/PostgreSQL checks:
- Build/E2E/visual checks:
- Manual verification:

## Rollback
- Code rollback:
- Data rollback:

## Assumptions and drift
- Verified assumptions:
- Unresolved assumptions:
- SPEC_DRIFT:
```

Do not use a change contract to authorize work that requires owner approval.

