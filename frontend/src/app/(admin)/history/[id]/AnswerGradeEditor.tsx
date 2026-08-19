"use client";

import React, { useMemo, useState } from "react";
import { Loader2 } from "lucide-react";

import type { SubmissionAnswerDetail } from "@/types";

interface AnswerGradeEditorProps {
  answer: SubmissionAnswerDetail;
  /** True while this row's correction is in flight. */
  isSaving: boolean;
  /** True while any row's correction is in flight, including this one. */
  isLocked: boolean;
  onSave: (
    questionId: string,
    pointsAwarded: number,
    reason: string,
  ) => Promise<boolean>;
}

/** Backend `GradeOverrideRequest.reason` is `min_length=1, max_length=2000`. */
const REASON_MAX_LENGTH = 2000;

const FIELD_CLASS =
  "border-4 border-black bg-white text-black font-mono font-bold p-2 " +
  "focus-visible:outline focus-visible:outline-4 focus-visible:outline-black " +
  "disabled:opacity-50 disabled:cursor-not-allowed";

const BUTTON_CLASS =
  "px-3 py-2 border-4 border-black bg-black text-white font-mono font-bold " +
  "uppercase tracking-tight text-xs transition-none " +
  "shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:bg-white hover:text-black " +
  "disabled:opacity-50 disabled:cursor-not-allowed " +
  "focus-visible:outline focus-visible:outline-4 focus-visible:outline-black " +
  "flex items-center justify-center gap-2";

/**
 * One answer's score, editable by the exam's owner or an admin.
 *
 * The bounds mirror the server's, which is the only authority: `points_awarded`
 * must sit inside `[0, max_points]` and `reason` must be non-blank. Both are
 * pre-checked here so an obviously refusable correction is never sent, and the
 * button says why it is unavailable rather than failing silently. When the
 * backend omits `max_points` no upper bound is invented -- the server decides.
 */
export default function AnswerGradeEditor({
  answer,
  isSaving,
  isLocked,
  onSave,
}: AnswerGradeEditorProps) {
  const maxPoints =
    typeof answer.max_points === "number" && Number.isFinite(answer.max_points)
      ? answer.max_points
      : null;

  const [points, setPoints] = useState<string>(String(answer.points_awarded));
  const [reason, setReason] = useState<string>("");

  const parsedPoints = useMemo(() => {
    if (points.trim() === "") return Number.NaN;
    return Number(points);
  }, [points]);

  const trimmedReason = reason.trim();
  const pointsOutOfRange =
    !Number.isFinite(parsedPoints) ||
    parsedPoints < 0 ||
    (maxPoints !== null && parsedPoints > maxPoints);
  const reasonMissing = trimmedReason.length === 0;
  const reasonTooLong = trimmedReason.length > REASON_MAX_LENGTH;
  const canSave =
    !isLocked && !pointsOutOfRange && !reasonMissing && !reasonTooLong;

  const pointsFieldId = `grade-points-${answer.question_id}`;
  const reasonFieldId = `grade-reason-${answer.question_id}`;
  const hintId = `grade-hint-${answer.question_id}`;

  const hint = pointsOutOfRange
    ? maxPoints !== null
      ? `[!] Điểm phải nằm trong khoảng 0 đến ${maxPoints}.`
      : "[!] Điểm phải là một số không âm."
    : reasonTooLong
      ? `[!] Lý do tối đa ${REASON_MAX_LENGTH} ký tự.`
      : reasonMissing
        ? "[!] Bắt buộc nhập lý do điều chỉnh trước khi lưu."
        : null;

  const handleSave = async () => {
    if (!canSave) return;
    const accepted = await onSave(
      answer.question_id,
      parsedPoints,
      trimmedReason,
    );
    // Only a correction the server actually stored clears the reason box; a
    // refused one keeps the typed text so it can be retried.
    if (accepted) setReason("");
  };

  return (
    <div
      className="mt-6 border-4 border-black bg-white p-4 shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
      data-testid={`answer-grade-editor-${answer.question_id}`}
    >
      <p className="font-mono text-xs font-bold uppercase underline">
        Điều chỉnh điểm
      </p>

      {(answer.override_reason || answer.overridden_at) && (
        <p
          role="status"
          data-testid={`answer-grade-trail-${answer.question_id}`}
          className="font-mono text-xs mt-2 border-2 border-black p-2"
        >
          <span className="font-bold uppercase">[ĐÃ ĐIỀU CHỈNH]</span>
          {answer.overridden_at && (
            <span className="ml-2">
              {new Date(answer.overridden_at).toLocaleString("vi-VN")}
            </span>
          )}
          {answer.override_reason && (
            <span className="block mt-1">Lý do: {answer.override_reason}</span>
          )}
        </p>
      )}

      <div className="mt-3 flex flex-col gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label
              htmlFor={pointsFieldId}
              className="font-mono text-[10px] font-bold uppercase"
            >
              Điểm mới{maxPoints !== null ? ` (0 - ${maxPoints})` : ""}
            </label>
            <input
              id={pointsFieldId}
              type="number"
              inputMode="decimal"
              min={0}
              {...(maxPoints !== null ? { max: maxPoints } : {})}
              step="any"
              value={points}
              disabled={isLocked}
              aria-invalid={pointsOutOfRange}
              aria-describedby={hint ? hintId : undefined}
              onChange={(event) => setPoints(event.target.value)}
              className={`${FIELD_CLASS} w-32`}
            />
          </div>
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave}
            aria-busy={isSaving}
            className={BUTTON_CLASS}
          >
            {isSaving && (
              <Loader2 className="animate-spin w-4 h-4" aria-hidden="true" />
            )}
            Lưu điểm
          </button>
        </div>

        <div className="flex flex-col gap-1">
          <label
            htmlFor={reasonFieldId}
            className="font-mono text-[10px] font-bold uppercase"
          >
            Lý do điều chỉnh (bắt buộc)
          </label>
          <textarea
            id={reasonFieldId}
            rows={2}
            maxLength={REASON_MAX_LENGTH}
            value={reason}
            disabled={isLocked}
            required
            aria-invalid={reasonMissing || reasonTooLong}
            aria-describedby={hint ? hintId : undefined}
            onChange={(event) => setReason(event.target.value)}
            className={`${FIELD_CLASS} w-full text-sm`}
          />
        </div>

        {hint && (
          <p
            id={hintId}
            role="status"
            className="font-mono text-xs font-bold uppercase"
          >
            {hint}
          </p>
        )}
      </div>
    </div>
  );
}
