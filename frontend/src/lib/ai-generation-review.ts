/**
 * Review-state policy for AI generation jobs (AI-002).
 *
 * This module is a deliberate mirror of the backend transition allowlist in
 * `backend/app/services/ai_generation_service.py` (`ALLOWED_TRANSITIONS`),
 * restricted to the transitions a human reviewer can drive. The backend is
 * authoritative and refuses anything absent from its own allowlist with
 * `AI_JOB_INVALID_TRANSITION`; keeping the reviewer-facing subset here means
 * the UI never offers an action the server is guaranteed to reject.
 *
 * The absence of a `generated -> published` pair is load-bearing, not an
 * oversight: publication must pass through an explicit approval.
 */

export type AIGenerationJobStatus =
  | "requested"
  | "processing"
  | "generated"
  | "awaiting_review"
  | "approved"
  | "rejected"
  | "published"
  | "failed";

export type AIGenerationReviewAction = "approve" | "reject" | "publish";

/** The single legal source status for each reviewer-driven transition. */
const REVIEWER_TRANSITIONS: Readonly<
  Record<AIGenerationReviewAction, AIGenerationJobStatus>
> = {
  approve: "awaiting_review",
  reject: "awaiting_review",
  publish: "approved",
};

const REVIEW_ACTION_ORDER: readonly AIGenerationReviewAction[] = [
  "approve",
  "reject",
  "publish",
];

/**
 * The reviewer actions the backend would accept for `status`.
 *
 * `awaiting_review` yields approve/reject but never publish; `approved`
 * yields publish alone; every terminal or pipeline-owned status yields
 * nothing.
 */
export function availableReviewActions(
  status: AIGenerationJobStatus | null | undefined,
): AIGenerationReviewAction[] {
  if (!status) return [];
  return REVIEW_ACTION_ORDER.filter(
    (action) => REVIEWER_TRANSITIONS[action] === status,
  );
}

/** True when the job can no longer change state through any actor. */
export function isTerminalStatus(status: AIGenerationJobStatus): boolean {
  return status === "rejected" || status === "published" || status === "failed";
}

/**
 * Vietnamese reviewer-facing status labels, matching the AI workspace's
 * existing bracket-token convention (`[OK]`, `[...]`, `[WAIT]`). State is
 * carried by the text and token rather than by color, per the brutalist
 * black-and-white design rules.
 */
export const REVIEW_STATUS_LABELS: Readonly<
  Record<AIGenerationJobStatus, string>
> = {
  requested: "[...] REQUEST RECEIVED",
  processing: "[...] GENERATING CONTENT",
  generated: "[...] GENERATED, QUEUING REVIEW",
  awaiting_review: "[WAIT] AWAITING REVIEW",
  approved: "[OK] APPROVED",
  rejected: "[X] REJECTED",
  published: "[OK] PUBLISHED",
  failed: "[!] GENERATION FAILED",
};

/** Explains why no action is offered, so a dead-end state is never silent. */
export const REVIEW_STATUS_HINTS: Readonly<
  Record<AIGenerationJobStatus, string>
> = {
  requested: "The request is waiting for processing.",
  processing: "AI is generating content for this review session.",
  generated: "The content was generated and will move to review shortly.",
  awaiting_review: "Approve or reject this draft before publishing.",
  approved: "The draft is approved and can be published.",
  rejected: "The draft was rejected and cannot be published.",
  published: "The content was published to the system.",
  failed: "Content generation failed. Try generating again from the material.",
};

export const REVIEW_ACTION_LABELS: Readonly<
  Record<AIGenerationReviewAction, string>
> = {
  approve: "Approve",
  reject: "Reject",
  publish: "Publish",
};
