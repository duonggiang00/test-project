import type { DifficultyLevel, QuestionType } from "@/types";

export type CanonicalQuestionType = Extract<
  QuestionType,
  "SINGLE_CHOICE" | "MULTIPLE_CHOICE" | "MATCHING" | "FILL_IN_BLANK"
>;
export type CanonicalDifficultyLevel = Extract<
  DifficultyLevel,
  "EASY" | "MEDIUM" | "HARD"
>;

const QUESTION_TYPE_ALIASES: Record<QuestionType, CanonicalQuestionType> = {
  SINGLE_CHOICE: "SINGLE_CHOICE",
  MULTIPLE_CHOICE: "MULTIPLE_CHOICE",
  MATCHING: "MATCHING",
  FILL_IN_BLANK: "FILL_IN_BLANK",
  single_choice: "SINGLE_CHOICE",
  multiple_choice: "MULTIPLE_CHOICE",
  true_false: "SINGLE_CHOICE",
  short_answer: "FILL_IN_BLANK",
};

const DIFFICULTY_ALIASES: Record<DifficultyLevel, CanonicalDifficultyLevel> = {
  EASY: "EASY",
  MEDIUM: "MEDIUM",
  HARD: "HARD",
  easy: "EASY",
  medium: "MEDIUM",
  hard: "HARD",
};

export function toCanonicalQuestionType(
  value: QuestionType = "SINGLE_CHOICE",
): CanonicalQuestionType {
  return QUESTION_TYPE_ALIASES[value];
}

export function toCanonicalDifficulty(
  value: DifficultyLevel = "MEDIUM",
): CanonicalDifficultyLevel {
  return DIFFICULTY_ALIASES[value];
}
