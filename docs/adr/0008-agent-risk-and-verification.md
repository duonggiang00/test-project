# ADR-0008: Risk-Based Agent Autonomy and Verification

Status: Accepted  
Date: 2026-08-05

## Context

A mandatory multi-agent/full-E2E pipeline for every change is slow and encourages ceremonial or unverifiable completion reports. High-risk changes still need stronger separation and approval.

## Decision

- Ordinary scoped tasks may be planned, implemented, and verified by one primary agent.
- Subagents are reserved for large or high-risk work.
- Authentication, migrations, tenant isolation, breaking APIs, and major architecture require approval before implementation.
- Cross-layer features require independent diff review; security/data changes require specialist review.
- Verification is risk-based: targeted tests first, then static, integration, build, E2E, or visual gates as applicable.
- A task cannot be marked complete without exact relevant output and disclosure of unverified items.
- Test assertions may not be weakened merely to make a gate pass.

## Consequences

- Small changes receive faster feedback.
- High-risk changes retain approval and reviewer separation.
- Completion status represents executed evidence, not intended verification.

## Supersession

This ADR supersedes workflows requiring three sequential subagents and full Playwright execution for every code change.

