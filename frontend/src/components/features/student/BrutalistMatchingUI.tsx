"use client";

import React, { useState } from "react";

export interface MatchPair {
  left: string;
  right: string;
}

interface BrutalistMatchingUIProps {
  pairs?: MatchPair[];
  leftOptions?: string[];
  rightOptions?: string[];
  currentMatches: MatchPair[];
  onChange: (newMatches: MatchPair[]) => void;
  /** Khi true: không cho click, hiển thị đúng/sai qua màu line */
  readOnly?: boolean;
  /** Danh sách cặp đáp án đúng — dùng khi readOnly=true để vẽ line gợi ý */
  correctMatches?: MatchPair[];
}

type LineData = { x1: number; y1: number; x2: number; y2: number };
const EMPTY_MATCHES: MatchPair[] = [];

export default function BrutalistMatchingUI({
  pairs = EMPTY_MATCHES,
  leftOptions: providedLeftOptions,
  rightOptions: providedRightOptions,
  currentMatches,
  onChange,
  readOnly = false,
  correctMatches = EMPTY_MATCHES,
}: BrutalistMatchingUIProps) {
  const [selectedItem, setSelectedItem] = useState<{
    side: "left" | "right";
    text: string;
  } | null>(null);

  const containerRef = React.useRef<HTMLDivElement>(null);
  const leftRefs = React.useRef<Array<HTMLElement | null>>([]);
  const rightRefs = React.useRef<Array<HTMLElement | null>>([]);

  const [studentLines, setStudentLines] = useState<LineData[]>([]);
  const [correctLines, setCorrectLines] = useState<LineData[]>([]);

  const leftOptions = React.useMemo(
    () => providedLeftOptions ?? pairs.map((pair) => pair.left),
    [pairs, providedLeftOptions],
  );
  const rightOptions = React.useMemo(() => {
    const options = providedRightOptions ?? pairs.map((pair) => pair.right);
    return [...options].sort((a, b) => a.localeCompare(b));
  }, [pairs, providedRightOptions]);

  /** Tính toán line dựa trên danh sách matches */
  const computeLines = React.useCallback(
    (matches: MatchPair[]): LineData[] => {
      if (!containerRef.current) return [];
      const containerRect = containerRef.current.getBoundingClientRect();
      return matches
        .map((match) => {
          const leftIndex = leftOptions.indexOf(match.left);
          const rightIndex = rightOptions.indexOf(match.right);
          const leftEl = leftRefs.current[leftIndex];
          const rightEl = rightRefs.current[rightIndex];
          if (leftEl && rightEl) {
            const lRect = leftEl.getBoundingClientRect();
            const rRect = rightEl.getBoundingClientRect();
            return {
              x1: lRect.right - containerRect.left,
              y1: lRect.top + lRect.height / 2 - containerRect.top,
              x2: rRect.left - containerRect.left,
              y2: rRect.top + rRect.height / 2 - containerRect.top,
            };
          }
          return null;
        })
        .filter(Boolean) as LineData[];
    },
    [leftOptions, rightOptions]
  );

  const updateLines = React.useCallback(() => {
    setStudentLines(computeLines(currentMatches));

    if (readOnly && correctMatches.length > 0) {
      // Chỉ vẽ correct-line khi student nối SAI hoặc chưa nối
      const wrongPairs = correctMatches.filter((correct) => {
        const studentAnswer = currentMatches.find(
          (m) => m.left === correct.left
        );
        return !studentAnswer || studentAnswer.right !== correct.right;
      });
      setCorrectLines(computeLines(wrongPairs));
    } else {
      setCorrectLines([]);
    }
  }, [currentMatches, correctMatches, readOnly, computeLines]);

  React.useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    updateLines();
    window.addEventListener("resize", updateLines);
    const resizeObserver = typeof ResizeObserver === "undefined"
      ? null
      : new ResizeObserver(updateLines);
    if (containerRef.current) resizeObserver?.observe(containerRef.current);
    return () => {
      window.removeEventListener("resize", updateLines);
      resizeObserver?.disconnect();
    };
  }, [updateLines]);

  React.useEffect(() => {
    const timeout = setTimeout(updateLines, 50);
    return () => clearTimeout(timeout);
  }, [selectedItem, updateLines]);

  // ── Interactive handlers (chỉ dùng khi không readOnly) ──────────────────
  const handleItemClick = (side: "left" | "right", text: string) => {
    if (readOnly) return;

    if (!selectedItem) {
      setSelectedItem({ side, text });
      return;
    }

    if (selectedItem.side === side) {
      setSelectedItem(selectedItem.text === text ? null : { side, text });
      return;
    }

    const leftText = side === "left" ? text : selectedItem.text;
    const rightText = side === "right" ? text : selectedItem.text;

    const existingMatch = currentMatches.find(
      (m) => m.left === leftText && m.right === rightText
    );
    if (existingMatch) {
      onChange(
        currentMatches.filter(
          (m) => !(m.left === leftText && m.right === rightText)
        )
      );
    } else {
      const filtered = currentMatches.filter(
        (m) => m.left !== leftText && m.right !== rightText
      );
      onChange([...filtered, { left: leftText, right: rightText }]);
    }
    setSelectedItem(null);
  };

  /** Tìm đáp án đúng của left theo correctMatches */
  const getCorrectRight = (left: string): string | undefined =>
    correctMatches.find((m) => m.left === left)?.right;

  /** Với ô bên phải: đúng = ✓, sai = ✗, chưa nối = trống */
  const getRightIcon = (rightText: string): "correct" | "wrong" | null => {
    if (!readOnly) return null;
    // Tìm xem left nào map đến rightText này theo student
    const studentMatch = currentMatches.find((m) => m.right === rightText);
    if (!studentMatch) return null;
    const correct = getCorrectRight(studentMatch.left);
    return correct === rightText ? "correct" : "wrong";
  };

  // ── Stroke style cho từng student-line ───────────────────────────────────
  // Tất cả line của student đều đen nét liền — đúng/sai chỉ phân biệt qua icon ✓/✗
  const getStudentLineStyle = () => ({
    stroke: "black",
    strokeDasharray: "none",
  });

  return (
    <div className="relative w-full" ref={containerRef}>
      {/* SVG overlay */}
      <svg
        aria-hidden="true"
        className="absolute inset-0 hidden h-full w-full pointer-events-none z-10 md:block"
        style={{ overflow: "visible" }}
      >
        {/* Lines đáp án đúng (khi student sai) — vẽ trước để student line đè lên */}
        {correctLines.map((l, idx) => (
          <line
            key={`correct-${idx}`}
            x1={l.x1}
            y1={l.y1}
            x2={l.x2}
            y2={l.y2}
            stroke="black"
            strokeWidth="3"
            strokeDasharray="6 3"
            className="transition-all duration-300"
          />
        ))}

        {/* Lines của student */}
        {studentLines.map((l, idx) => {
          const match = currentMatches[idx];
          const style = match
            ? getStudentLineStyle()
            : { stroke: "black", strokeDasharray: "none" };
          return (
            <line
              key={`student-${idx}`}
              x1={l.x1}
              y1={l.y1}
              x2={l.x2}
              y2={l.y2}
              stroke={style.stroke}
              strokeWidth="4"
              strokeDasharray={style.strokeDasharray}
              className="transition-all duration-300"
            />
          );
        })}
      </svg>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2 md:gap-24 relative z-20">
        {/* Left Column */}
        <div
          aria-label="Left options"
          className="flex min-w-0 flex-col gap-4"
          role="group"
        >
          <p className="border-b-4 border-black pb-2 font-mono text-sm font-black uppercase tracking-widest">
            Vế trái
          </p>
          {leftOptions.map((text, i) => {
            const isSelected =
              selectedItem?.side === "left" && selectedItem.text === text;
            const isMatched = currentMatches.some((m) => m.left === text);

            let className =
              "min-h-14 w-full p-4 text-left border-4 border-black font-bold font-mono text-lg transition-colors duration-200 focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-black";
            if (readOnly) {
              className += " cursor-default select-none";
              className += isMatched
                ? " bg-white text-black border-dashed"
                : " bg-white text-black";
            } else {
              className += " cursor-pointer";
              if (isSelected) className += " bg-black text-white";
              else if (isMatched)
                className += " bg-white text-black border-dashed";
              else className += " bg-white text-black hover:border-dashed";
            }

            return (
              <button
                type="button"
                key={`left-${i}`}
                ref={(el) => {
                  leftRefs.current[i] = el;
                }}
                onClick={() => handleItemClick("left", text)}
                disabled={readOnly}
                aria-pressed={isSelected}
                aria-label={`Left option: ${text}${isMatched ? ", matched" : ""}`}
                className={className}
              >
                {text}
              </button>
            );
          })}
        </div>

        {/* Right Column */}
        <div
          aria-label="Right options"
          className="flex min-w-0 flex-col gap-4"
          role="group"
        >
          <p className="border-b-4 border-black pb-2 font-mono text-sm font-black uppercase tracking-widest">
            Vế phải
          </p>
          {rightOptions.map((text, i) => {
            const isSelected =
              selectedItem?.side === "right" && selectedItem.text === text;
            const isMatched = currentMatches.some((m) => m.right === text);
            const icon = getRightIcon(text);

            let className =
              "relative min-h-14 w-full p-4 text-left border-4 border-black font-bold font-mono text-lg transition-colors duration-200 focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-black";
            if (readOnly) {
              className += " cursor-default select-none pr-10";
              if (icon === "correct") className += " bg-black text-white";
              else if (icon === "wrong")
                className += " bg-white text-black border-dashed";
              else className += " bg-white text-black";
            } else {
              className += " cursor-pointer";
              if (isSelected) className += " bg-black text-white";
              else if (isMatched)
                className += " bg-white text-black border-dashed";
              else className += " bg-white text-black hover:border-dashed";
            }

            return (
              <button
                type="button"
                key={`right-${i}`}
                ref={(el) => {
                  rightRefs.current[i] = el;
                }}
                onClick={() => handleItemClick("right", text)}
                disabled={readOnly}
                aria-pressed={isSelected}
                aria-label={`Right option: ${text}${isMatched ? ", matched" : ""}`}
                className={className}
              >
                {text}
                {/* Icon đúng/sai ở góc phải */}
                {icon === "correct" && (
                  <span className="absolute top-1/2 right-3 -translate-y-1/2 text-white font-black text-xl leading-none">
                    ✓
                  </span>
                )}
                {icon === "wrong" && (
                  <span className="absolute top-1/2 right-3 -translate-y-1/2 text-black font-black text-xl leading-none">
                    ✗
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div
        aria-live="polite"
        className="mt-6 border-4 border-black p-4 font-mono md:hidden"
        data-testid="mobile-matching-summary"
      >
        <p className="border-b-2 border-black pb-2 text-sm font-black uppercase tracking-widest">
          Các cặp đã nối
        </p>
        {currentMatches.length === 0 ? (
          <p className="pt-3 text-sm font-bold">Chưa có cặp nào.</p>
        ) : (
          <ul className="space-y-2 pt-3">
            {currentMatches.map((match, index) => (
              <li
                className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 border-2 border-black p-2 text-sm font-bold"
                key={`${match.left}-${match.right}-${index}`}
              >
                <span className="break-words">{match.left}</span>
                <span aria-hidden="true">→</span>
                <span className="break-words text-right">{match.right}</span>
              </li>
            ))}
          </ul>
        )}
        {readOnly && correctMatches.length > 0 && (
          <div
            className="mt-4 border-t-4 border-black pt-4"
            data-testid="mobile-correct-matches"
          >
            <p className="border-b-2 border-black pb-2 text-sm font-black uppercase tracking-widest">
              Đáp án đúng
            </p>
            <ul className="space-y-2 pt-3">
              {correctMatches.map((match, index) => (
                <li
                  className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 border-2 border-dashed border-black p-2 text-sm font-bold"
                  key={`correct-${match.left}-${match.right}-${index}`}
                >
                  <span className="break-words">{match.left}</span>
                  <span aria-hidden="true">→</span>
                  <span className="break-words text-right">{match.right}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Help text — chỉ hiện khi đang làm bài */}
      {!readOnly && (
        <div className="mt-6 text-center text-sm text-black">
          <p>Bấm chọn một ô ở bên này và bấm tiếp một ô ở bên kia để nối.</p>
          <p>
            Bấm vào ô đang chọn để hủy chọn, hoặc nối lại một ô mới để tự động
            thay thế đường nối cũ.
          </p>
        </div>
      )}

      {/* Legend — chỉ hiện khi readOnly */}
      {readOnly && (
        <div className="mt-6 flex flex-wrap gap-6 text-xs font-mono font-bold uppercase border-t-2 border-black pt-4">
          <span className="flex items-center gap-2">
            <svg width="32" height="8">
              <line x1="0" y1="4" x2="32" y2="4" stroke="black" strokeWidth="3" />
            </svg>
            Câu trả lời của bạn
          </span>
          <span className="flex items-center gap-2">
            <svg width="32" height="8">
              <line x1="0" y1="4" x2="32" y2="4" stroke="black" strokeWidth="2" strokeDasharray="4 2" />
            </svg>
            Đáp án đúng (gợi ý)
          </span>
          <span className="flex items-center gap-2 font-black">✓ Đúng</span>
          <span className="flex items-center gap-2 font-black">✗ Sai</span>
        </div>
      )}
    </div>
  );
}
