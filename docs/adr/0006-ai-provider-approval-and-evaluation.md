# ADR-0006: AI Provider Abstraction, Human Approval, and Evaluation

Status: Accepted  
Date: 2026-08-05

## Context

AI generation handles sensitive content and can affect exams, study material, and grading. Provider-specific code and unreviewed publishing increase reliability and governance risk.

## Decision

- AI access uses a provider abstraction.
- Model selection is configurable by use case.
- Provider errors are reported immediately; automatic fallback is not required.
- Generated exams/questions, flashcards, topic briefs, and grading suggestions require human approval before publication or final application.
- AI grading remains advisory.
- Audit metadata includes prompt version, provider/model, token usage, cost, latency, context sources, reviewer, and outcome.
- Evaluation covers correctness, groundedness/citation, context relevance, prompt-injection resistance, latency, and cost.
- Admin owns approval of the initial golden dataset.

## Consequences

- AI content needs an explicit review state machine.
- Sensitive prompt/context logs require redaction, access control, retention, and tenant isolation.
- Prompt/model changes become measurable governed changes.

## Supersession

Any future automatic publishing, fallback, or final AI grading policy requires a new approved ADR.

