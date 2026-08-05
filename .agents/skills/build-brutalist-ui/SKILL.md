---
name: build-brutalist-ui
description: Build or review the project's strict black-and-white brutalist interface. Use for page layouts, visual components, design tokens, typography, interaction states, accessibility, responsive behavior, and visual regression tests.
---

# Build Brutalist UI

Create a text-first, high-contrast product interface while preserving domain semantics and accessibility.

## Establish context

1. Read the root and frontend `AGENTS.md` files.
2. Read `docs/spec/CANONICAL_PROJECT_SPEC.md` and `docs/adr/ADR-0005-BRUTALIST-BLACK-WHITE-UI.md`.
3. Inspect existing tokens, shared primitives, nearby screens, and current screenshots before introducing a new visual pattern.
4. Use `frontend-architecture` as well when the work changes data fetching, cache behavior, BFF communication, or client state.

## Apply the visual system

- Use absolute black and white for the product UI. Do not introduce gray scales, colored accents, gradients, translucent color, or color-coded status.
- Communicate success, warning, and error through text, symbols, borders, patterns, and placement; never through color alone.
- Use the project's local font through `next/font/local`. Do not add remote font dependencies.
- Prefer hard edges, visible borders, direct hierarchy, deliberate spacing, and content-first layouts.
- Reuse a component when semantics match. Create a domain-specific component when meaning or interaction differs, even if it shares visual primitives.
- Keep decoration subordinate to comprehension. Do not imitate generic dashboard chrome when the task needs a focused domain workflow.

## Design complete behavior

- Specify loading, empty, error, disabled, selected, focus, optimistic, and rollback states where applicable.
- Preserve readable line lengths, clear labels, predictable tab order, keyboard activation, visible black-and-white focus indicators, and sufficient target sizes.
- Use semantic HTML before ARIA. Add ARIA only when native semantics are insufficient.
- Ensure information remains understandable at mobile widths and high zoom without depending on hover.
- Render user-facing warnings and validation adjacent to the affected action or field.

## Verify the result

- Check desktop and mobile layouts in Chromium, Firefox, and WebKit for critical screens.
- Add or update visual regression coverage for intentional layout changes.
- Verify keyboard navigation and focus behavior manually.
- Capture a screenshot or Playwright trace for the handoff.
- Treat snapshot changes as evidence to review, not as automatic approval of the new UI.
