# ADR-0005: Strict Black-and-White Brutalist Design

Status: Accepted  
Date: 2026-08-05

## Context

Existing design instructions disagree about grayscale colors, fonts, shadows, and the mandatory use of generic UI components.

## Decision

- The product uses a strict black-and-white brutalist visual language.
- Status is communicated through text, symbols, icons, border style/weight, layout, and accessible names rather than color.
- Fonts are stored locally and loaded through the Next.js font API.
- Remote font dependencies are prohibited.
- Existing components are reused when semantics and behavior match.
- Domain components are allowed when generic Shadcn styling or behavior does not express the required semantics.
- Visual regression covers critical desktop and mobile states.

## Consequences

- A design-token whitelist must distinguish intentional black/white tokens from legacy colors.
- Error and warning states must remain understandable without color.
- Component reuse is semantic rather than unconditional.

## Supersession

This ADR supersedes guidance permitting gray palettes, remote font links, or requiring Shadcn controls when their semantics do not fit.

