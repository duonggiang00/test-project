import api from "@/lib/api";
import type { AIGenerationJobStatus } from "@/lib/ai-generation-review";
import type { PaginatedResponse, SubmissionDetail } from "@/types";

// ==========================================
// 1. TOPICS MUTATIONS
// ==========================================
export interface CreateTopicPayload {
  name: string;
  description?: string | null;
  parent_id?: string | null;
}

export interface UpdateTopicPayload {
  name?: string;
  description?: string | null;
  parent_id?: string | null;
}

export const createTopic = async (payload: CreateTopicPayload) => {
  const res = await api.post("/topics", payload);
  return res.data;
};

export const updateTopic = async (topicId: string, payload: UpdateTopicPayload) => {
  const res = await api.put(`/topics/${topicId}`, payload);
  return res.data;
};

export const deleteTopic = async (topicId: string) => {
  const res = await api.delete(`/topics/${topicId}`);
  return res.data;
};

// ==========================================
// 2. EXAMS MUTATIONS
// ==========================================
export interface CreateExamPayload {
  title: string;
  description?: string | null;
  duration_minutes: number;
  is_published?: boolean;
  topic_id?: string | null;
}

export interface UpdateExamPayload {
  title?: string;
  description?: string | null;
  duration_minutes?: number;
  is_published?: boolean;
  topic_id?: string | null;
}

export const createExam = async (payload: CreateExamPayload) => {
  const res = await api.post("/exams", payload);
  return res.data;
};

export const updateExam = async (examId: string, payload: UpdateExamPayload) => {
  const res = await api.put(`/exams/${examId}`, payload);
  return res.data;
};

export const deleteExam = async (examId: string) => {
  const res = await api.delete(`/exams/${examId}`);
  return res.data;
};

export const addQuestionToExam = async (examId: string, questionPayload: CreateQuestionPayload) => {
  const res = await api.post(`/exams/${examId}/questions`, questionPayload);
  return res.data;
};

export const bulkAddQuestionsToExam = async (examId: string, questionIds: string[]) => {
  const res = await api.post(`/exams/${examId}/questions/bulk`, { question_ids: questionIds });
  return res.data;
};

// ==========================================
// 3. QUESTIONS MUTATIONS
// ==========================================
export interface CreateQuestionPayload {
  content: string;
  points: number;
  question_type?: string;
  difficulty?: string;
  topic_id?: string | null;
  exam_id?: string | null;
  options?: Array<{ content: string; is_correct: boolean }>;
}

export interface UpdateQuestionPayload {
  content?: string;
  points?: number;
  question_type?: string;
  difficulty?: string;
  topic_id?: string | null;
  options?: Array<{ id?: string; content: string; is_correct: boolean }>;
}

export const createQuestion = async (payload: CreateQuestionPayload) => {
  const res = await api.post("/questions", payload);
  return res.data;
};

export const updateQuestion = async (questionId: string, payload: UpdateQuestionPayload) => {
  const res = await api.put(`/questions/${questionId}`, payload);
  return res.data;
};

export const deleteQuestion = async (questionId: string) => {
  const res = await api.delete(`/questions/${questionId}`);
  return res.data;
};

// ==========================================
// 4. STUDENTS / USER MANAGEMENT MUTATIONS
// ==========================================
export const updateStudentRole = async (userId: string, newRole: string) => {
  const res = await api.put(
    `/admin/users/${userId}/role?new_role=${encodeURIComponent(newRole)}`,
  );
  return res.data;
};

export const deleteStudent = async (userId: string) => {
  const res = await api.delete(`/admin/users/${userId}`);
  return res.data;
};

// ==========================================
// 5. MATERIALS, AUTH & STUDENT EXAM SUBMISSION
// ==========================================
export const uploadMaterial = async (file: File, topicId?: string) => {
  const formData = new FormData();
  formData.append("file", file);
  if (topicId) {
    formData.append("topic_id", topicId);
  }
  const res = await api.post("/materials/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export const deleteMaterial = async (materialId: string, cascade?: boolean, keepAssets?: boolean) => {
  let url = `/materials/${materialId}?`;
  if (cascade) url += 'cascade=true&';
  if (keepAssets) url += 'keep_assets=true&';
  const res = await api.delete(url);
  return res.data;
};

export const generateMaterialQuestions = async (
  materialId: string,
  count: number,
) => {
  const response = await api.post(
    `/materials/${materialId}/generate-questions`,
    {
      count,
      question_types: [
        "SINGLE_CHOICE",
        "MULTIPLE_CHOICE",
        "MATCHING",
        "FILL_IN_BLANK",
      ],
      difficulty: "MEDIUM",
    },
  );
  return response.data;
};

export const generateMaterialFlashcards = async (
  materialId: string,
  count: number,
) => {
  const response = await api.post(
    `/materials/${materialId}/generate-flashcards`,
    { count },
  );
  return response.data;
};

export const generateMaterialTopicBrief = async (materialId: string) => {
  const response = await api.post(
    `/materials/${materialId}/generate-topic-brief`,
  );
  return response.data;
};

// ==========================================
// AI GENERATION REVIEW QUEUE (AI-002)
// ==========================================
// The `/materials/{id}/save-*` routes these replaced were removed with the
// review state machine. Publishing is the only writer of AI-generated rows
// and it reads its content from the job's reviewed `draft_payload`, so no
// publish request here carries generated content -- only placement and the
// optimistic-concurrency guard. `updateGenerationJobDraft` below is the one
// deliberate exception: it edits `draft_payload` itself, and the backend
// only accepts it while the job is still `awaiting_review`, so publish's
// "content always comes from the reviewed draft" guarantee still holds.

export interface AIGenerationJob {
  id: string;
  owner_id: string;
  material_id: string;
  use_case: string;
  status: AIGenerationJobStatus;
  version: number;
  draft_payload?: Record<string, unknown> | null;
  failure_code?: string | null;
  reviewer_id?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  published_at?: string | null;
}

export interface ListGenerationJobsParams {
  status?: AIGenerationJobStatus;
  material_id?: string;
  page?: number;
  size?: number;
}

/** Placement only. Content is never accepted from the client. */
export interface PublishGenerationJobPayload {
  title?: string | null;
  topic_id?: string | null;
}

export interface PublishGenerationJobResult {
  job_id: string;
  status: "published";
  [key: string]: unknown;
}

export const listGenerationJobs = async (
  params: ListGenerationJobsParams = {},
): Promise<PaginatedResponse<AIGenerationJob>> => {
  const response = await api.get("/ai/generation-jobs", { params });
  return response.data;
};

export const getGenerationJob = async (
  jobId: string,
): Promise<AIGenerationJob> => {
  const response = await api.get(`/ai/generation-jobs/${jobId}`);
  return response.data;
};

export const approveGenerationJob = async (
  jobId: string,
  expectedVersion?: number,
): Promise<AIGenerationJob> => {
  const response = await api.post(`/ai/generation-jobs/${jobId}/approve`, {
    expected_version: expectedVersion ?? null,
  });
  return response.data;
};

export const rejectGenerationJob = async (
  jobId: string,
  expectedVersion?: number,
): Promise<AIGenerationJob> => {
  const response = await api.post(`/ai/generation-jobs/${jobId}/reject`, {
    expected_version: expectedVersion ?? null,
  });
  return response.data;
};

export const publishGenerationJob = async (
  jobId: string,
  payload: PublishGenerationJobPayload = {},
  expectedVersion?: number,
): Promise<PublishGenerationJobResult> => {
  const response = await api.post(`/ai/generation-jobs/${jobId}/publish`, {
    title: payload.title ?? null,
    topic_id: payload.topic_id ?? null,
    expected_version: expectedVersion ?? null,
  });
  return response.data;
};

/** One question inside an edited `question_generation` draft. */
export interface QuestionDraftPayload {
  type: string;
  content: string;
  points: number;
  difficulty?: string | null;
  source_reference?: string | null;
  explanation?: string | null;
  options: { content: string; is_correct: boolean }[];
  metadata_json?: Record<string, unknown> | null;
}

/** One flashcard inside an edited `flashcard_generation` draft. */
export interface FlashcardDraftPayload {
  term: string;
  definition: string;
  source_reference?: string | null;
  explanation?: string | null;
}

/**
 * A reviewer's edit to one job's `draft_payload`. Exactly one of
 * `questions`/`flashcards`/`content` is sent, matching the job's
 * `use_case` -- the backend rejects any other combination.
 */
export type UpdateGenerationJobDraftPayload =
  | { questions: QuestionDraftPayload[] }
  | { flashcards: FlashcardDraftPayload[] }
  | { content: string; title?: string | null };

export const updateGenerationJobDraft = async (
  jobId: string,
  payload: UpdateGenerationJobDraftPayload,
  expectedVersion?: number,
): Promise<AIGenerationJob> => {
  const response = await api.patch(`/ai/generation-jobs/${jobId}/draft`, {
    ...payload,
    expected_version: expectedVersion ?? null,
  });
  return response.data;
};

// ==========================================
// SUBMISSION GRADE CORRECTION (GRADE-001)
// ==========================================
// The first write on `/history/*`. `is_correct` and `total_score` are absent
// on purpose: the backend derives the first with the same rule the automatic
// grader uses and recomputes the second from the answers, so a client can
// neither assert a total nor desynchronise it from its parts. The response is
// the full updated submission, which lets the caller write it straight into
// the SWR cache instead of inventing a shape.

export interface UpdateSubmissionGradePayload {
  /** Bounded server-side by the question's own `points`. */
  points_awarded: number;
  /** Non-blank, at most 2000 characters. Stored as the correction trail. */
  reason: string;
}

export const updateSubmissionGrade = async (
  submissionId: string,
  questionId: string,
  payload: UpdateSubmissionGradePayload,
): Promise<SubmissionDetail> => {
  const response = await api.put(
    `/history/submissions/${submissionId}/answers/${questionId}/grade`,
    { points_awarded: payload.points_awarded, reason: payload.reason },
  );
  return response.data;
};

export interface AiChatTransportMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export const openAiChatStream = async (
  messages: AiChatTransportMessage[],
  materialId: string,
): Promise<Response> =>
  fetch("/api/proxy/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, material_id: materialId }),
  });

export const registerUser = async (payload: { email: string; password: string; full_name: string }) => {
  const res = await api.post("/auth/register", payload);
  return res.data;
};

export const login = async (email: string, password: string, rememberMe: boolean = false) => {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password, rememberMe }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw { response: { data } };
  }
  return data;
};

export const logoutUser = async () => {
  await fetch("/api/auth/logout", { method: "POST" });
};

export const forgotPassword = async (email: string) => {
  const res = await api.post("/auth/forgot-password", { email });
  return res.data;
};

export const resetPassword = async (payload: { token: string; new_password: string }) => {
  const res = await api.post("/auth/reset-password", payload);
  return res.data;
};

export const submitExam = async (
  examId: string,
  payload: { answers: { question_id: string; selected_option_id: string }[] }
) => {
  const res = await api.post(`/student/exams/${examId}/submit`, payload);
  return res.data;
};
