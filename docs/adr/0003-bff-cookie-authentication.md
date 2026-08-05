# ADR-0003: BFF-Only HttpOnly Cookie Authentication

Status: Accepted  
Date: 2026-08-05

## Context

Browser-managed bearer tokens increase exposure to script access, while mixed direct-backend and proxy calls create inconsistent security and redirect behavior.

## Decision

- Authentication uses access and refresh tokens in HttpOnly cookies.
- The Next.js BFF/proxy is the only browser-to-backend request path.
- Browser code must not call the backend origin directly.
- Backend authorization remains the security boundary.
- The auth lifecycle must cover refresh rotation, replay protection, revocation, logout, CSRF protection, and expiry.
- Canonical redirects are `/dashboard`, `/student/home`, and `/login`.

## Consequences

- Zustand and local storage cannot contain authentication tokens.
- Frontend route guards are user-experience controls, not authorization controls.
- Static checks and integration tests must verify the BFF-only boundary.

## Supersession

This ADR supersedes prior guidance that stores JWTs in Zustand persistence or local storage. A later ADR is required to adopt a different authentication architecture.

