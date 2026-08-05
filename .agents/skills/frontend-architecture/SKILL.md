---
name: frontend-architecture
description: Implement or review frontend features in this Next.js App Router project. Use for React components, routes, server rendering, BFF handlers, API transport, SWR hooks, Zustand state, authentication flows, authorization presentation, forms, and frontend tests.
---

# Frontend Architecture

Build frontend changes with explicit server, transport, cache, and UI-state boundaries.

## Establish context

1. Read the root `AGENTS.md` and the nearest frontend `AGENTS.md`.
2. Read `docs/spec/CANONICAL_PROJECT_SPEC.md` and relevant ADRs.
3. Inspect the current route, component, service, hook, store, BFF handler, and tests before editing.
4. Consult the installed Next.js version's documentation when framework behavior is material.
5. Use `build-brutalist-ui` as well when changing visual layout, styling, or interaction states.

## Choose the correct data boundary

- Fetch initial server-rendered data in Server Components when possible.
- Route every browser-to-backend request through the Next.js BFF/proxy. Do not call the backend directly from browser code.
- Keep transport and serialization in service modules.
- Use SWR hooks to coordinate client server-state, cache keys, invalidation, optimistic updates, rollback, and revalidation.
- Use Zustand only for genuine client/UI state that is not authoritative server data.
- Use `useEffect` for external side effects, subscriptions, or synchronization. Do not use it as the routine data-fetching mechanism.
- Avoid duplicating the same server state across component state, Zustand, and SWR.
- Do not use full-page reloads to repair cache consistency.

## Preserve application contracts

- Let the backend enforce authentication, role, tenant, and ownership rules. Frontend guards only redirect or hide unavailable controls.
- Send unauthenticated users to `/login`, admin/teacher users to `/dashboard`, and students to `/student/home`.
- Consume the backend's structured `error_code` and details, then localize messages in the frontend.
- Keep access and refresh tokens in HttpOnly cookies; never expose them through browser-readable state or storage.
- Use non-trailing-slash application API paths and cover the convention with tests or linting.
- Reuse existing components when their semantics match. Create a domain component when semantics or behavior genuinely differ.

## Model complete interaction states

Implement and test the relevant loading, empty, success, error, disabled, optimistic, and rollback states. Surface AI failures immediately to the user. Preserve keyboard operation, focus management, accessible names, and semantic HTML.

## Verify the change

- Test services and hooks independently where useful.
- Add component tests for state transitions and user-visible errors.
- Add BFF contract tests for cookie forwarding, status mapping, and structured errors.
- Use Playwright for critical role, route, browser, and mobile flows across Chromium, Firefox, and WebKit.
- Include a screenshot or trace for material UI work.
- Do not weaken an assertion merely to obtain a green build; first prove that the contract or test is wrong.
