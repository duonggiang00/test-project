import useSWR from "swr";
import { fetcher } from "./useFetch";
import api from "@/lib/api";

export function useMaterialDetail(materialId: string) {
  const { data, isLoading, mutate } = useSWR(
    materialId ? `/materials/${materialId}` : null,
    fetcher
  );
  return { material: data, isLoading, mutate };
}

export function useMaterialQuestions(materialId: string) {
  const { data, isLoading, mutate } = useSWR(
    materialId ? `/materials/${materialId}/questions` : null,
    fetcher
  );
  return { questions: (data ?? []) as QuestionPreview[], isLoading, mutate };
}

export interface OptionPreview {
  content: string;
  is_correct: boolean;
}

export interface QuestionPreview {
  type: string;
  content: string;
  points: number;
  source_reference?: string;
  options: OptionPreview[];
  metadata_json?: Record<string, unknown>;
}

export interface FlashcardPreview {
  term: string;
  definition: string;
}

export async function generateQuestions(
  materialId: string,
  payload: { question_types: string[]; count: number; difficulty: string }
): Promise<{ questions: QuestionPreview[] }> {
  const res = await api.post(`/materials/${materialId}/generate-questions`, payload);
  return res.data;
}

export async function saveQuestions(
  materialId: string,
  questions: QuestionPreview[]
): Promise<{ saved_count: number; question_ids: string[] }> {
  const res = await api.post(`/materials/${materialId}/save-questions`, { questions });
  return res.data;
}

export async function generateFlashcards(
  materialId: string,
  count: number
): Promise<{ flashcards: FlashcardPreview[] }> {
  const res = await api.post(`/materials/${materialId}/generate-flashcards`, { count });
  return res.data;
}

export async function saveFlashcards(
  materialId: string,
  payload: { title: string; topic_id?: string; flashcards: FlashcardPreview[] }
): Promise<{ deck_id: string; saved_count: number }> {
  const res = await api.post(`/materials/${materialId}/save-flashcards`, payload);
  return res.data;
}
