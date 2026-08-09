import api from "../lib/api";
import {
  deleteMaterial,
  generateMaterialFlashcards,
  generateMaterialQuestions,
  generateMaterialTopicBrief,
  openAiChatStream,
  saveGeneratedFlashcards,
  saveGeneratedQuestions,
  saveGeneratedTopicBrief,
  uploadMaterial,
} from "./apiService";

jest.mock("../lib/api", () => ({
  __esModule: true,
  default: {
    delete: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
  },
}));

const mockedDelete = jest.mocked(api.delete);
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

  test("uses explicit contracts for all generated-content save operations", async () => {
    mockedPost.mockResolvedValue({ data: { saved: true } } as never);
    const questions = [{ content: "Question" }];
    const flashcards = [{ term: "Term", definition: "Definition" }];

    await saveGeneratedQuestions("material-1", questions);
    await saveGeneratedFlashcards("material-1", flashcards);
    await saveGeneratedTopicBrief("material-1", "Brief content");

    expect(mockedPost).toHaveBeenNthCalledWith(
      1,
      "/materials/material-1/save-questions",
      { questions },
    );
    expect(mockedPost).toHaveBeenNthCalledWith(
      2,
      "/materials/material-1/save-flashcards",
      {
        title: "AI-generated flashcards",
        topic_id: null,
        flashcards,
      },
    );
    expect(mockedPost).toHaveBeenNthCalledWith(
      3,
      "/materials/material-1/save-topic-brief",
      {
        title: "AI-generated topic brief",
        content: "Brief content",
        topic_id: null,
      },
    );
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
