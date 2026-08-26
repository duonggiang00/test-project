import useSWR from "swr";

import {
  useAnalytics,
  useAnalyticsOverview,
  useCompletionStatus,
  useScoreStats,
  useTopicPerformance,
} from "@/hooks/useAnalytics";
import {
  createCard,
  createDeck,
  generateTopicKitAi,
  submitCardReview,
  updateTopicBrief,
  useDeckDetail,
  useStudyCards,
  useTopicDecks,
} from "@/hooks/useFlashcards";
import {
  createQuestion,
  deleteQuestion,
  updateQuestion,
  useQuestionDetail,
  useQuestions,
} from "@/hooks/useQuestions";
import {
  submitExam,
  useStudentExamResult,
  useStudentExams,
  useTakeExam,
} from "@/hooks/useStudentExams";
import {
  createTopic,
  deleteTopic,
  updateTopic,
  useTopicDetail,
  useTopicProgress,
  useTopics,
} from "@/hooks/useTopics";
import {
  deleteUser,
  updateUserRole,
  useUserDetail,
  useUsers,
} from "@/hooks/useUsers";
import api from "@/lib/api";

jest.mock("swr", () => ({
  __esModule: true,
  default: jest.fn(),
}));

jest.mock("../../src/lib/api", () => ({
  __esModule: true,
  default: {
    delete: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
  },
}));

const mockedUseSWR = jest.mocked(useSWR);
const mockedApi = jest.mocked(api);
const mutate = jest.fn();

function swrResult(data: unknown = undefined, error: unknown = undefined) {
  return { data, error, isLoading: false, mutate } as never;
}

describe("frontend data-hook contracts", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseSWR.mockReturnValue(swrResult());
  });

  test("builds topic keys and normalizes list, detail, and progress payloads", () => {
    const topics = [{ id: "topic-1", name: "Biology" }];
    mockedUseSWR.mockReturnValueOnce(swrResult(topics));
    expect(useTopics({ page: 2, size: 10, search: "cell biology" })).toMatchObject({
      topics,
      pagination: { total: 1, page: 1, size: 1, pages: 1 },
    });
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/topics?page=2&size=10&search=cell%20biology",
      expect.any(Function),
    );

    mockedUseSWR.mockReturnValueOnce(swrResult({
      items: topics,
      total: 11,
      page: 2,
      size: 10,
      pages: 2,
    }));
    expect(useTopics().pagination).toMatchObject({ total: 11, page: 2, size: 10, pages: 2 });

    mockedUseSWR.mockReturnValueOnce(swrResult(topics[0]));
    expect(useTopicDetail("topic-1").topic).toEqual(topics[0]);
    expect(mockedUseSWR).toHaveBeenLastCalledWith("/topics/topic-1", expect.any(Function));
    useTopicDetail(null);
    expect(mockedUseSWR).toHaveBeenLastCalledWith(null, expect.any(Function));

    mockedUseSWR.mockReturnValueOnce(swrResult({ progress: 72 }));
    expect(useTopicProgress("topic-1").progress).toBe(72);
    mockedUseSWR.mockReturnValueOnce(swrResult());
    expect(useTopicProgress(null).progress).toBe(0);
  });

  test("uses canonical topic, user, and question mutation endpoints", async () => {
    mockedApi.post.mockResolvedValue({ data: { id: "created" } });
    mockedApi.put.mockResolvedValue({ data: { id: "updated" } });
    mockedApi.delete.mockResolvedValue({ data: undefined });

    await expect(createTopic({ name: "Biology" })).resolves.toEqual({ id: "created" });
    await expect(updateTopic("topic-1", { name: "Cells" })).resolves.toEqual({ id: "updated" });
    await deleteTopic("topic-1");
    await expect(updateUserRole("user-1", "teacher assistant")).resolves.toEqual({ id: "updated" });
    await deleteUser("user-1");
    await expect(createQuestion({ content: "Question" } as never)).resolves.toEqual({ id: "created" });
    await expect(updateQuestion("question-1", { points: 2 })).resolves.toEqual({ id: "updated" });
    await deleteQuestion("question-1");

    expect(mockedApi.post).toHaveBeenCalledWith("/topics", { name: "Biology" });
    expect(mockedApi.put).toHaveBeenCalledWith("/topics/topic-1", { name: "Cells" });
    expect(mockedApi.delete).toHaveBeenCalledWith("/topics/topic-1");
    expect(mockedApi.put).toHaveBeenCalledWith(
      "/admin/users/user-1/role?new_role=teacher%20assistant",
    );
    expect(mockedApi.delete).toHaveBeenCalledWith("/admin/users/user-1");
    expect(mockedApi.post).toHaveBeenCalledWith("/questions", { content: "Question" });
    expect(mockedApi.put).toHaveBeenCalledWith("/questions/question-1", { points: 2 });
    expect(mockedApi.delete).toHaveBeenCalledWith("/questions/question-1");
  });

  test("normalizes user and question queries and disables missing detail keys", () => {
    mockedUseSWR.mockReturnValueOnce(swrResult({ items: [{ id: "user-1" }] }));
    expect(useUsers(3, 25).users).toEqual([{ id: "user-1" }]);
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/admin/users?page=3&size=25",
      expect.any(Function),
    );
    mockedUseSWR.mockReturnValueOnce(swrResult({ id: "user-1" }));
    expect(useUserDetail("user-1").user).toEqual({ id: "user-1" });
    useUserDetail(null);
    expect(mockedUseSWR).toHaveBeenLastCalledWith(null, expect.any(Function));

    const questions = [{ id: "question-1" }];
    mockedUseSWR.mockReturnValueOnce(swrResult(questions));
    expect(useQuestions({
      page: 2,
      size: 5,
      topic_id: "topic 1",
      difficulty: "hard",
      search: "cell wall",
      exam_id: "exam-1",
    }).questions).toEqual(questions);
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/questions?page=2&size=5&topic_id=topic+1&difficulty=hard&search=cell+wall&exam_id=exam-1",
      expect.any(Function),
    );
    mockedUseSWR.mockReturnValueOnce(swrResult({
      items: questions,
      total: 7,
      page: 2,
      size: 5,
      pages: 2,
    }));
    expect(useQuestions().pagination.total).toBe(7);
    mockedUseSWR.mockReturnValueOnce(swrResult(questions[0]));
    expect(useQuestionDetail("question-1").question).toEqual(questions[0]);
    useQuestionDetail(null);
    expect(mockedUseSWR).toHaveBeenLastCalledWith(null, expect.any(Function));
  });

  test("builds analytics keys and aggregates loading, errors, and revalidation", () => {
    useAnalyticsOverview("student 1");
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/analytics/overview?student_id=student%201",
      expect.any(Function),
    );
    useAnalyticsOverview("all");
    expect(mockedUseSWR).toHaveBeenLastCalledWith("/analytics/overview", expect.any(Function));
    useScoreStats({ exam_id: "exam 1", topic_id: "topic/1" });
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/analytics/score-stats?exam_id=exam%201&topic_id=topic%2F1",
      expect.any(Function),
    );
    useCompletionStatus("exam 1");
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/analytics/completion-status?exam_id=exam%201",
      expect.any(Function),
    );
    useCompletionStatus();
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/analytics/completion-status",
      expect.any(Function),
    );
    mockedUseSWR.mockReturnValueOnce(swrResult());
    expect(useTopicPerformance().topicPerformance).toEqual([]);

    const refreshers = [jest.fn(), jest.fn(), jest.fn(), jest.fn()];
    let call = 0;
    mockedUseSWR.mockImplementation(() => ({
      data: undefined,
      error: call === 2 ? new Error("completion unavailable") : undefined,
      isLoading: call === 0,
      mutate: refreshers[call++],
    } as never));
    const analytics = useAnalytics("student-1");
    expect(analytics.isLoading).toBe(true);
    expect(analytics.isError).toEqual(new Error("completion unavailable"));
    analytics.mutate();
    refreshers.forEach((refresh) => expect(refresh).toHaveBeenCalledTimes(1));
  });

  test("builds student exam keys and submits the complete answer payload", async () => {
    mockedUseSWR.mockReturnValueOnce(swrResult({
      items: [{ id: "exam-1" }],
      total: 1,
      page: 1,
      size: 4,
      pages: 1,
    }));
    expect(useStudentExams({
      page: 2,
      size: 8,
      search: "mid term",
      topic_id: "topic-1",
    }).exams).toEqual([{ id: "exam-1" }]);
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/student/exams?page=2&size=8&search=mid+term&topic_id=topic-1",
      expect.any(Function),
    );
    useTakeExam("exam-1");
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/student/exams/exam-1/start",
      expect.any(Function),
    );
    useTakeExam("");
    expect(mockedUseSWR).toHaveBeenLastCalledWith(null, expect.any(Function));
    useStudentExamResult("exam-1");
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/student/exams/exam-1/result",
      expect.any(Function),
    );

    mockedApi.post.mockResolvedValueOnce({ data: { status: "submitted" } });
    await expect(submitExam("exam-1", { answers: [{ question_id: "q1" }] })).resolves.toEqual({
      status: "submitted",
    });
    expect(mockedApi.post).toHaveBeenLastCalledWith(
      "/student/exams/exam-1/submit",
      { answers: [{ question_id: "q1" }] },
    );
  });

  test("builds flashcard keys and mutation payloads", async () => {
    mockedUseSWR.mockReturnValueOnce(swrResult([{ id: "deck-1" }]));
    expect(useTopicDecks("topic-1").decks).toEqual([{ id: "deck-1" }]);
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/flashcards/topics/topic-1/decks",
      expect.any(Function),
    );
    useTopicDecks(null);
    expect(mockedUseSWR).toHaveBeenLastCalledWith(null, expect.any(Function));
    useDeckDetail("deck-1");
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/flashcards/decks/deck-1",
      expect.any(Function),
    );
    useStudyCards("deck-1");
    expect(mockedUseSWR).toHaveBeenLastCalledWith(
      "/flashcards/student/decks/deck-1/study",
      expect.any(Function),
    );

    mockedApi.post.mockResolvedValue({ data: { id: "created" } });
    mockedApi.put.mockResolvedValue({ data: { id: "updated" } });
    await createDeck({ topic_id: "topic-1", title: "Cells" });
    await createCard("deck-1", { front_content: "A", back_content: "B" });
    await updateTopicBrief("topic-1", { brief_content: "Brief" });
    await generateTopicKitAi("material-1", "topic-1");
    await submitCardReview("card-1", { rating: "GOOD" });

    expect(mockedApi.post).toHaveBeenCalledWith(
      "/flashcards/decks",
      { topic_id: "topic-1", title: "Cells" },
    );
    expect(mockedApi.post).toHaveBeenCalledWith(
      "/flashcards/decks/deck-1/cards",
      { front_content: "A", back_content: "B" },
    );
    expect(mockedApi.put).toHaveBeenCalledWith(
      "/flashcards/topics/topic-1/brief",
      { brief_content: "Brief" },
    );
    expect(mockedApi.post).toHaveBeenCalledWith(
      "/flashcards/ai/generate-topic-kit",
      { material_id: "material-1", topic_id: "topic-1" },
    );
    expect(mockedApi.post).toHaveBeenCalledWith(
      "/flashcards/student/cards/card-1/review",
      { rating: "GOOD" },
    );
  });
});
