# Change Contract: TEST-008 and TEST-009 — Visual and Interaction States

Risk level: L1
Owner: Primary Codex agent
Approval required: No

## Intent

- Review and commit deterministic brutalist visual baselines for Chromium, Firefox, WebKit, and mobile Chrome.
- Cover critical loading, empty, error, disabled, focus, and keyboard-activation states.

## Evidence

- Topic management page screenshot runs after mocked data settles, with animation/caret disabled.
- Featured exam list exposes explicit loading/error/empty semantics and component tests.
- Button component tests cover disabled and focus semantics.
- Mocked browser flow opens the topic dialog using keyboard Enter before completing the critical flow.

Snapshot updates require visual review and are not an automatic response to a failed regression.
