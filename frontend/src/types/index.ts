// Generic Paginated Response Container
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Topic Interface
export interface Topic {
  id: string;
  name: string;
  description?: string | null;
  parent_id?: string | null;
  brief_content?: string | null;
  brief_ai_generated?: boolean;
  created_at?: string;
}

// Flashcard Interfaces
export interface FlashcardDeck {
  id: string;
  topic_id: string;
  title: string;
  description?: string | null;
  created_at?: string;
  flashcards?: Flashcard[];
}

export interface Flashcard {
  id: string;
  deck_id: string;
  front_content: string;
  back_content: string;
  order_index?: number;
}

export interface FlashcardProgress {
  id: string;
  student_id: string;
  flashcard_id: string;
  box_level: number;
  next_review_at: string;
  last_reviewed_at?: string;
}

// Option / QuestionOption Interface
export interface Option {
  id: string;
  content: string;
  is_correct: boolean;
}

export type QuestionOption = Option;

export type QuestionType = "multiple_choice" | "single_choice" | "true_false" | "short_answer" | "SINGLE_CHOICE" | "MULTIPLE_CHOICE" | "FILL_IN_BLANK" | "MATCHING";
export type DifficultyLevel = "easy" | "medium" | "hard" | "EASY" | "MEDIUM" | "HARD";

// Question Interface
export interface Question {
  id: string;
  content: string;
  points: number;
  question_type?: QuestionType;
  difficulty?: DifficultyLevel;
  is_ai_generated?: boolean;
  topic_id?: string | null;
  exam_id?: string | null;
  material_id?: string | null;
  metadata_json?: Record<string, unknown> | null;
  options: Option[];
  created_at?: string;
}

// Exam Interface
export interface Exam {
  id: string;
  title: string;
  description?: string | null;
  duration_minutes: number;
  is_published: boolean;
  topic_id?: string | null;
  creator_id?: string | null;
  created_at?: string;
  questions?: Question[];
}

export interface ExamDetail extends Exam {
  questions: Question[];
}

// User / Student Interface
export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: "admin" | "teacher" | "student" | string;
  avatar_url?: string | null;
  phone_number?: string | null;
  date_of_birth?: string | null;
  bio?: string | null;
  created_at?: string;
}

export type StudentUser = User;

export interface StudentDetail extends StudentUser {
  total_exams_taken?: number;
  average_score?: number;
}

// Analytics Interfaces
export interface AnalyticsOverview {
  total_students: number;
  total_exams: number;
  total_questions: number;
  total_submissions: number;
  overall_avg_score: number;
  completion_rate: number;
  total_topics?: number;
  pass_rate?: number;
}

export interface ScoreDistributionBucket {
  range_label: string;
  count: number;
}

export interface ScoreStat {
  range: string;
  count: number;
  percentage?: number;
}

export interface ScoreStats {
  highest_score: number;
  lowest_score: number;
  average_score: number;
  median_score: number;
  distribution: ScoreDistributionBucket[];
}

export interface CompletionStatus {
  completed: number;
  in_progress: number;
  completed_count?: number;
  in_progress_count?: number;
  not_started_count?: number;
  total_assigned?: number;
}

export interface TopicPerformance {
  topic_id: string;
  topic_name: string;
  avg_score_percentage: number;
  total_attempts: number;
}

// Exam History & Submission Interfaces
export type SubmissionStatus = "submitted" | "in_progress" | "graded";

export interface Submission {
  id: string;
  exam_id: string;
  exam_title?: string | null;
  student_id: string;
  student_name?: string | null;
  student_email?: string | null;
  start_time?: string;
  end_time?: string | null;
  score?: number;
  total_score: number;
  max_score?: number;
  status: SubmissionStatus | string;
  started_at?: string;
  submitted_at?: string | null;
  time_taken_seconds?: number | null;
}

export type SubmissionHistoryItem = Submission;

export interface SubmissionAnswerDetail {
  question_id: string;
  question_content: string;
  answer_data?: Record<string, unknown> | unknown;
  is_correct?: boolean | null;
  points_awarded: number;
  /** The question's maximum. Bounds a manual correction (GRADE-001). */
  max_points?: number;
  /** Manual-correction trail. Both are null on an answer nobody corrected. */
  override_reason?: string | null;
  overridden_at?: string | null;
}

export interface SubmissionDetail extends Submission {
  answers: SubmissionAnswerDetail[];
}

// Legacy / Existing Student Types (Preserved for compatibility)
export interface Material {
  id: string;
  title: string;
  file_type: string;
  ai_status: "pending" | "processing" | "completed" | "failed";
}

export interface DashboardStats {
  total_materials: number;
  total_exams: number;
  total_questions: number;
  total_students: number;
}

export interface StudentExamList {
  id: string;
  title: string;
  description: string | null;
  duration_minutes: number;
  submission_status: string | null;
  total_score: number | null;
  topic_name?: string;
  question_count?: number;
}

export interface StudentExamDetail {
  id: string;
  title: string;
  description: string | null;
  duration_minutes: number;
  questions: Array<{
    id: string;
    content: string;
    points: number;
    question_type?: string;
    metadata_json?: Record<string, unknown> | null;
    options: Array<{
      id: string;
      content: string;
    }>;
  }>;
}

export interface StudentExamResultAnswer {
  question_id: string;
  content: string;
  question_type: string;
  metadata_json?: Record<string, unknown> | null;
  options: QuestionOption[];
  answer_data?: Record<string, unknown> | null;
  is_correct: boolean;
  points_awarded: number;
  points: number;
}

export interface StudentExamResultResponse {
  exam_id: string;
  title: string;
  total_score: number;
  max_score: number;
  correct_count: number;
  incorrect_count: number;
  time_taken_seconds: number;
  answers: StudentExamResultAnswer[];
}
