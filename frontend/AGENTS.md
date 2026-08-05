# Frontend Agent Rules

Apply this file to changes under `frontend/` together with the workspace `AGENTS.md`.

This repository uses Next.js 16 App Router. Before changing framework behavior, read the relevant installed guide under `node_modules/next/dist/docs/`; do not rely on training-memory conventions.

## Request and state boundaries

- The Next.js BFF/proxy is the only browser-to-backend request path. Never call the backend origin from browser code.
- Use Server Components for data required by server-rendered output.
- Use SWR for client-side server state, cache keys, revalidation, and mutations.
- Use Zustand only for client/UI state. Never store access or refresh tokens in Zustand or local storage.
- Put transport calls in the service layer and cache coordination in hooks.
- Do not fetch ordinary API data with `useEffect`.
- Do not refresh CRUD state with `window.location.reload()` or `window.location.href`.

## Routing and auth UX

- Backend authorization is authoritative; frontend checks only improve UX.
- Canonical redirects are `/dashboard` for admin/teacher, `/student/home` for student, and `/login` for unauthenticated users.
- Next.js route-group folder names do not appear in URLs.
- Survey existing pages and route groups before adding a route; do not create duplicate or orphan routes.
- A user-facing feature must be reachable through the intended navigation flow.
- Use `proxy.ts` rather than deprecated middleware conventions for the installed Next.js version.

## Components and design

- Use strict black and white; do not introduce gray or colored semantic states.
- Communicate error, warning, success, loading, and disabled states with English text, symbols/icons, border style/weight, layout, and accessible names.
- Use local fonts through the Next.js font API. Do not use remote font links or `next/font/google` network dependencies.
- Reuse existing controls when semantics and behavior match.
- Domain components are allowed when generic Shadcn semantics or styling do not fit the approved brutalist design.
- Keep interactive client boundaries as low in the tree as practical.
- Use semantic HTML, keyboard-operable controls, visible focus, and accessible names.
- Use `next/image` when optimization is appropriate; check installed framework guidance rather than applying a blanket image rule.

## Errors and mutations

- Translate backend `error_code` values into English user-facing messages.
- Provide a safe fallback for unknown error codes.
- Do not expose raw backend/provider error text.
- Mutations go through services and update/revalidate the relevant SWR cache.
- Treat loading, empty, error, disabled, optimistic, and rollback states as required behavior.

## Verification

- Pure service/hook logic: focused unit tests.
- Components: behavior and accessibility-oriented tests.
- Server/client boundary or hydration changes: build plus hydration-focused tests.
- Routing/auth/user-flow changes: navigation E2E from a real entry point.
- Layout/style changes: visual regression at desktop and mobile viewports.
- Critical flows must eventually cover Chromium, Firefox, WebKit, and mobile projects.

Read `frontend/tests/AGENTS.md` before changing frontend tests.
