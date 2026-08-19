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
  requested: "[...] ĐÃ TIẾP NHẬN YÊU CẦU",
  processing: "[...] ĐANG SINH NỘI DUNG",
  generated: "[...] ĐÃ SINH, ĐANG CHUYỂN DUYỆT",
  awaiting_review: "[WAIT] ĐANG CHỜ DUYỆT",
  approved: "[OK] ĐÃ DUYỆT",
  rejected: "[X] ĐÃ TỪ CHỐI",
  published: "[OK] ĐÃ XUẤT BẢN",
  failed: "[!] SINH NỘI DUNG THẤT BẠI",
};

/** Explains why no action is offered, so a dead-end state is never silent. */
export const REVIEW_STATUS_HINTS: Readonly<
  Record<AIGenerationJobStatus, string>
> = {
  requested: "Yêu cầu đang chờ hệ thống xử lý.",
  processing: "AI đang sinh nội dung cho phiên duyệt này.",
  generated: "Nội dung vừa được sinh và sẽ sớm chuyển sang trạng thái chờ duyệt.",
  awaiting_review: "Hãy duyệt hoặc từ chối bản nháp này trước khi xuất bản.",
  approved: "Bản nháp đã được duyệt và có thể xuất bản vào hệ thống.",
  rejected: "Bản nháp đã bị từ chối và không thể xuất bản.",
  published: "Nội dung đã được ghi vào hệ thống.",
  failed: "Không thể sinh nội dung. Hãy thử sinh lại từ tài liệu.",
};

export const REVIEW_ACTION_LABELS: Readonly<
  Record<AIGenerationReviewAction, string>
> = {
  approve: "Duyệt",
  reject: "Từ chối",
  publish: "Xuất bản",
};
