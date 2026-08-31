"use client";

import React, { useCallback } from "react";
import { Loader2 } from "lucide-react";

import { toast } from "@/components/ui/toast";
import { getBackendErrorMessage, logBackendError } from "@/lib/errors";
import {
  REVIEW_ACTION_LABELS,
  REVIEW_STATUS_HINTS,
  REVIEW_STATUS_LABELS,
  type AIGenerationReviewAction,
} from "@/lib/ai-generation-review";
import { useGenerationJobReview } from "@/hooks/useMaterialWorkspace";

interface GenerationJobReviewProps {
  jobId: string | null;
  /** Placement for a publish. Content always comes from the reviewed draft. */
  title?: string | null;
  topicId?: string | null;
}

const ACTION_ERROR_TITLES: Record<AIGenerationReviewAction, string> = {
  approve: "Approval failed",
  reject: "Rejection failed",
  publish: "Publish failed",
};

const ACTION_ERROR_FALLBACKS: Record<AIGenerationReviewAction, string> = {
  approve: "The generated content could not be approved.",
  reject: "The generated content could not be rejected.",
  publish: "The approved content could not be published.",
};

const ACTION_SUCCESS_MESSAGES: Record<AIGenerationReviewAction, string> = {
  approve: "Draft approved. It can now be published.",
  reject: "Draft rejected. The content will not be published.",
  publish: "Approved content published to the system.",
};

const ACTION_LOG_CONTEXTS: Record<AIGenerationReviewAction, string> = {
  approve: "AI generation job approve failed",
  reject: "AI generation job reject failed",
  publish: "AI generation job publish failed",
};

const PANEL_CLASS =
  "border-4 border-black bg-white text-black p-3 shadow-[4px_4px_0_0_rgba(0,0,0,1)]";

const BUTTON_CLASS =
  "px-3 py-2 border-4 border-black font-mono font-bold uppercase tracking-tight " +
  "text-xs transition-none shadow-[2px_2px_0_0_rgba(0,0,0,1)] " +
  "disabled:opacity-50 disabled:cursor-not-allowed " +
  "focus-visible:outline focus-visible:outline-4 focus-visible:outline-black " +
  "flex items-center justify-center gap-2";

/**
 * State-aware review controls for one AI generation job.
 *
 * Actions are derived from the backend transition allowlist rather than
 * rendered unconditionally, so the panel never offers a decision the server
 * would refuse with `AI_JOB_INVALID_TRANSITION`. Publishing appears only once
 * the job is `approved`.
 */
export default function GenerationJobReview({
  jobId,
  title,
  topicId,
}: GenerationJobReviewProps) {
  const handleError = useCallback(
    (action: AIGenerationReviewAction, error: unknown) => {
      logBackendError(ACTION_LOG_CONTEXTS[action], error);
      toast.add({
        title: ACTION_ERROR_TITLES[action],
        description: getBackendErrorMessage(
          error,
          ACTION_ERROR_FALLBACKS[action],
        ),
        type: "error",
      });
    },
    [],
  );

  const {
    job,
    isLoading,
    isError,
    actions,
    pendingAction,
    approve,
    reject,
    publish,
  } = useGenerationJobReview(jobId, handleError);

  const runAction = useCallback(
    async (action: AIGenerationReviewAction) => {
      let accepted = false;
      if (action === "approve") accepted = await approve();
      else if (action === "reject") accepted = await reject();
      else {
        accepted = await publish({
          title: title ?? null,
          topic_id: topicId ?? null,
        });
      }
      // Failures are surfaced by `handleError`; only a decision the server
      // actually accepted is announced as a success.
      if (accepted) {
        toast.add({
          title: "Action completed",
          description: ACTION_SUCCESS_MESSAGES[action],
          type: "success",
        });
      }
    },
    [approve, publish, reject, title, topicId],
  );

  if (!jobId) {
    return (
      <div className={PANEL_CLASS} data-testid="generation-job-review">
        <p className="font-mono text-xs font-bold uppercase">
          [INFO] Preview
        </p>
        <p className="font-mono text-xs mt-1">
          This content is not attached to a review session and cannot be published.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={PANEL_CLASS} data-testid="generation-job-review">
        <p
          role="status"
          className="font-mono text-xs font-bold uppercase flex items-center gap-2"
        >
          <Loader2 className="animate-spin w-4 h-4" aria-hidden="true" />
          [...] LOADING REVIEW STATUS
        </p>
      </div>
    );
  }

  if (isError || !job) {
    return (
      <div
        className={`${PANEL_CLASS} border-dashed`}
        data-testid="generation-job-review"
      >
        <p role="status" className="font-mono text-xs font-bold uppercase">
          [!] REVIEW STATUS UNAVAILABLE
        </p>
        <p className="font-mono text-xs mt-1">
          The review session could not be loaded. Try again later.
        </p>
      </div>
    );
  }

  return (
    <div className={PANEL_CLASS} data-testid="generation-job-review">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-mono text-[10px] font-bold uppercase underline">
            Review status
          </p>
          <p
            role="status"
            data-testid="generation-job-status"
            data-status={job.status}
            className="font-mono text-xs font-bold uppercase mt-1"
          >
            {REVIEW_STATUS_LABELS[job.status] ?? `[?] ${job.status}`}
          </p>
        </div>
        {actions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
              <button
                key={action}
                type="button"
                onClick={() => runAction(action)}
                disabled={pendingAction !== null}
                aria-busy={pendingAction === action}
                className={`${BUTTON_CLASS} ${
                  action === "reject"
                    ? "bg-white text-black hover:bg-black hover:text-white"
                    : "bg-black text-white hover:bg-white hover:text-black"
                }`}
              >
                {pendingAction === action && (
                  <Loader2 className="animate-spin w-4 h-4" aria-hidden="true" />
                )}
                {REVIEW_ACTION_LABELS[action]}
              </button>
            ))}
          </div>
        )}
      </div>
      <p className="font-mono text-xs mt-2 border-t-2 border-black pt-2">
        {REVIEW_STATUS_HINTS[job.status] ??
          "No action is available for this status."}
      </p>
      {job.failure_code && (
        <p className="font-mono text-xs mt-1 font-bold uppercase">
          [!] Error code: {job.failure_code}
        </p>
      )}
    </div>
  );
}
