import api from "../lib/api";
import {
  approveGenerationJob,
  createExam,
  createQuestion,
  createTopic,
  deleteMaterial,
  generateMaterialFlashcards,
  generateMaterialQuestions,
  generateMaterialTopicBrief,
  getGenerationJob,
  listGenerationJobs,
  openAiChatStream,
  publishGenerationJob,
  rejectGenerationJob,
  uploadMaterial,
  updateStudentRole,
} from "./apiService";

jest.mock("../lib/api", () => ({
  __esModule: true,
  default: {
    delete: jest.fn(),
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
  },
}));

const mockedDelete = jest.mocked(api.delete);
const mockedGet = jest.mocked(api.get);
const mockedPost = jest.mocked(api.post);
const originalFetch = global.fetch;

describe("AI workspace transport services", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    if (originalFetch) {
      global.fetch = originalFetch;
    } else {
      Reflect.deleteProperty(global, "fetch");
    }
  });

  test("uploads a material with the expected multipart contract", async () => {
    const responseData = { id: "material-1" };
    mockedPost.mockResolvedValue({ data: responseData } as never);
    const file = new File(["source"], "source.txt", { type: "text/plain" });

    await expect(uploadMaterial(file, "topic-1")).resolves.toEqual(responseData);

    expect(mockedPost).toHaveBeenCalledTimes(1);
    const [url, body, config] = mockedPost.mock.calls[0];
    expect(url).toBe("/materials/upload");
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get("file")).toBe(file);
    expect((body as FormData).get("topic_id")).toBe("topic-1");
    expect(config).toEqual({
      headers: { "Content-Type": "multipart/form-data" },
    });
  });

  test("uses canonical no-trailing-slash create and role contracts", async () => {
    mockedPost.mockResolvedValue({ data: { id: "created" } } as never);
    jest.mocked(api.put).mockResolvedValue({ data: { role: "teacher" } } as never);

    await createTopic({ name: "Topic" });
    await createExam({ title: "Exam", duration_minutes: 30 });
    await createQuestion({ content: "Question", points: 1 });
    await updateStudentRole("user-1", "teacher");

    expect(mockedPost).toHaveBeenNthCalledWith(1, "/topics", {
      name: "Topic",
    });
    expect(mockedPost).toHaveBeenNthCalledWith(2, "/exams", {
      title: "Exam",
      duration_minutes: 30,
    });
    expect(mockedPost).toHaveBeenNthCalledWith(3, "/questions", {
      content: "Question",
      points: 1,
    });
    expect(api.put).toHaveBeenCalledWith(
      "/admin/users/user-1/role?new_role=teacher",
    );
  });

  test("serializes delete flags into the material endpoint", async () => {
    const responseData = { deleted: true };
    mockedDelete.mockResolvedValue({ data: responseData } as never);

    await expect(deleteMaterial("material-1", true, true)).resolves.toEqual(
      responseData,
    );

    expect(mockedDelete).toHaveBeenCalledWith(
      "/materials/material-1?cascade=true&keep_assets=true&",
    );
  });

  test("uses the approved question-generation payload", async () => {
    mockedPost.mockResolvedValue({ data: { questions: [] } } as never);

    await generateMaterialQuestions("material-1", 7);

    expect(mockedPost).toHaveBeenCalledWith(
      "/materials/material-1/generate-questions",
      {
        count: 7,
        difficulty: "MEDIUM",
        question_types: [
          "SINGLE_CHOICE",
          "MULTIPLE_CHOICE",
          "MATCHING",
          "FILL_IN_BLANK",
        ],
      },
    );
  });

  test("uses the approved flashcard and topic-brief endpoints", async () => {
    mockedPost.mockResolvedValue({ data: {} } as never);

    await generateMaterialFlashcards("material-1", 12);
    await generateMaterialTopicBrief("material-1");

    expect(mockedPost).toHaveBeenNthCalledWith(
      1,
      "/materials/material-1/generate-flashcards",
      { count: 12 },
    );
    expect(mockedPost).toHaveBeenNthCalledWith(
      2,
      "/materials/material-1/generate-topic-brief",
    );
  });

  test("reads generation jobs through the owner-scoped review endpoints", async () => {
    mockedGet.mockResolvedValue({ data: { items: [] } } as never);

    await listGenerationJobs({ status: "awaiting_review", material_id: "m1" });
    await getGenerationJob("job-1");

    expect(mockedGet).toHaveBeenNthCalledWith(1, "/ai/generation-jobs", {
      params: { status: "awaiting_review", material_id: "m1" },
    });
    expect(mockedGet).toHaveBeenNthCalledWith(2, "/ai/generation-jobs/job-1");
  });

  test("drives review decisions through the generation-job endpoints", async () => {
    mockedPost.mockResolvedValue({ data: { id: "job-1" } } as never);

    await approveGenerationJob("job-1", 3);
    await rejectGenerationJob("job-2", 4);

    expect(mockedPost).toHaveBeenNthCalledWith(
      1,
      "/ai/generation-jobs/job-1/approve",
      { expected_version: 3 },
    );
    expect(mockedPost).toHaveBeenNthCalledWith(
      2,
      "/ai/generation-jobs/job-2/reject",
      { expected_version: 4 },
    );
  });

  test("publishes with placement fields only and never generated content", async () => {
    mockedPost.mockResolvedValue({
      data: { job_id: "job-1", status: "published" },
    } as never);

    await publishGenerationJob(
      "job-1",
      { title: "Approved deck", topic_id: "topic-1" },
      7,
    );

    expect(mockedPost).toHaveBeenCalledTimes(1);
    const [url, body] = mockedPost.mock.calls[0];
    expect(url).toBe("/ai/generation-jobs/job-1/publish");
    expect(body).toEqual({
      title: "Approved deck",
      topic_id: "topic-1",
      expected_version: 7,
    });
    // The reviewed draft is the only content source; a publish request that
    // could carry questions/flashcards/content would reopen the bypass the
    // review queue exists to close.
    expect(Object.keys(body as object).sort()).toEqual([
      "expected_version",
      "title",
      "topic_id",
    ]);
  });

  test("defaults publish placement and concurrency guard to null", async () => {
    mockedPost.mockResolvedValue({
      data: { job_id: "job-1", status: "published" },
    } as never);

    await publishGenerationJob("job-1");

    expect(mockedPost).toHaveBeenCalledWith("/ai/generation-jobs/job-1/publish", {
      title: null,
      topic_id: null,
      expected_version: null,
    });
  });

  test("opens the AI stream through the BFF with the expected JSON contract", async () => {
    const response = { ok: true, status: 200 } as Response;
    const fetchSpy = jest.fn().mockResolvedValue(response);
    Object.defineProperty(global, "fetch", {
      configurable: true,
      value: fetchSpy,
      writable: true,
    });
    const messages = [{ role: "user" as const, content: "Create a quiz" }];

    await expect(openAiChatStream(messages, "material-1")).resolves.toBe(
      response,
    );

    expect(fetchSpy).toHaveBeenCalledWith("/api/proxy/ai/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages, material_id: "material-1" }),
    });
  });

  test.each([
    ["generation", () => generateMaterialQuestions("material-1", 5)],
    ["upload", () => uploadMaterial(new File(["x"], "source.txt"))],
    ["delete", () => deleteMaterial("material-1")],
  ])("propagates %s HTTP failures to the UI coordinator", async (_name, call) => {
    const failure = { response: { data: { error_code: "STATE_CONFLICT" } } };
    mockedPost.mockRejectedValue(failure);
    mockedDelete.mockRejectedValue(failure);

    await expect(call()).rejects.toBe(failure);
  });
});
