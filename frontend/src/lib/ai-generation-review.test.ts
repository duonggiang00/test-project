import {
  availableReviewActions,
  isTerminalStatus,
  REVIEW_STATUS_HINTS,
  REVIEW_STATUS_LABELS,
  type AIGenerationJobStatus,
} from "./ai-generation-review";

const ALL_STATUSES: AIGenerationJobStatus[] = [
  "requested",
  "processing",
  "generated",
  "awaiting_review",
  "approved",
  "rejected",
  "published",
  "failed",
];

describe("AI generation review policy", () => {
  test("offers approve and reject only while awaiting review", () => {
    expect(availableReviewActions("awaiting_review")).toEqual([
      "approve",
      "reject",
    ]);
  });

  test("offers publish only from approved", () => {
    expect(availableReviewActions("approved")).toEqual(["publish"]);
  });

  test("never offers publish before an explicit approval", () => {
    // The backend allowlist has no `generated -> published` pair. Offering it
    // here would produce a guaranteed 409 rather than a publish.
    for (const status of ALL_STATUSES) {
      if (status === "approved") continue;
      expect(availableReviewActions(status)).not.toContain("publish");
    }
  });

  test.each(["rejected", "published", "failed"] as AIGenerationJobStatus[])(
    "offers no action from the terminal status %s",
    (status) => {
      expect(availableReviewActions(status)).toEqual([]);
      expect(isTerminalStatus(status)).toBe(true);
    },
  );

  test.each(["requested", "processing", "generated"] as AIGenerationJobStatus[])(
    "offers no reviewer action from the pipeline status %s",
    (status) => {
      expect(availableReviewActions(status)).toEqual([]);
      expect(isTerminalStatus(status)).toBe(false);
    },
  );

  test("returns no actions for an unknown or absent status", () => {
    expect(availableReviewActions(null)).toEqual([]);
    expect(availableReviewActions(undefined)).toEqual([]);
    expect(
      availableReviewActions("bogus" as AIGenerationJobStatus),
    ).toEqual([]);
  });

  test("labels and explains every canonical status", () => {
    for (const status of ALL_STATUSES) {
      expect(REVIEW_STATUS_LABELS[status]).toBeTruthy();
      expect(REVIEW_STATUS_HINTS[status]).toBeTruthy();
    }
  });
});
