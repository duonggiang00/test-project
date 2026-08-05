import api from "@/lib/api";

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
  const res = await api.post("/topics/", payload);
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
  const res = await api.post("/exams/", payload);
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
  const res = await api.post("/questions/", payload);
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
  const res = await api.put(`/admin/users/${userId}/role`, { role: newRole });
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
