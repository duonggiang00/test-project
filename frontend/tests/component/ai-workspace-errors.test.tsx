import { TextDecoder, TextEncoder } from "node:util";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import AIWorkspacePage from "@/app/(admin)/ai-workspace/page";
import { toast } from "@/components/ui/toast";
import { useMaterials } from "@/hooks/useMaterials";
import { useTopics } from "@/hooks/useTopics";
import {
  generateMaterialFlashcards,
  generateMaterialQuestions,
  generateMaterialTopicBrief,
  openAiChatStream,
  uploadMaterial,
} from "@/services/apiService";

jest.mock("../../src/hooks/useMaterials", () => ({
  useMaterials: jest.fn(),
}));

jest.mock("../../src/hooks/useTopics", () => ({
  useTopics: jest.fn(),
}));

jest.mock("../../src/lib/store", () => ({
  useUserStore: () => ({ user: { id: "teacher-1", role: "teacher" } }),
}));

jest.mock("../../src/services/apiService", () => ({
  deleteMaterial: jest.fn(),
  generateMaterialFlashcards: jest.fn(),
  generateMaterialQuestions: jest.fn(),
  generateMaterialTopicBrief: jest.fn(),
  openAiChatStream: jest.fn(),
  uploadMaterial: jest.fn(),
}));

jest.mock(
  "../../src/app/(admin)/ai-workspace/GenerativePreview",
  () => () => null,
);

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

const mockedUseMaterials = jest.mocked(useMaterials);
const mockedUseTopics = jest.mocked(useTopics);
const mockedGenerateFlashcards = jest.mocked(generateMaterialFlashcards);
const mockedGenerateQuestions = jest.mocked(generateMaterialQuestions);
const mockedGenerateTopicBrief = jest.mocked(generateMaterialTopicBrief);
const mockedOpenAiChatStream = jest.mocked(openAiChatStream);
const mockedToastAdd = jest.mocked(toast.add);
const mockedUploadMaterial = jest.mocked(uploadMaterial);

function mockSelectableMaterial(): void {
  mockedUseMaterials.mockReturnValue({
    materials: [
      {
        id: "material-1",
        title: "Source material",
        file_type: "pdf",
        ai_status: "completed",
      },
    ],
    isLoading: false,
    isError: undefined,
    mutate: jest.fn(),
  });
}

describe("AI workspace RAG availability and stream failures", () => {
  const originalRagEnabled = process.env.NEXT_PUBLIC_RAG_ENABLED;

  beforeAll(() => {
    Object.assign(globalThis, { TextDecoder, TextEncoder });
    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      value: jest.fn(),
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
    process.env.NEXT_PUBLIC_RAG_ENABLED = "false";
    mockedUseMaterials.mockReturnValue({
      materials: [],
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUseTopics.mockReturnValue({
      topics: [],
      pagination: {
        items: [],
        total: 0,
        page: 1,
        size: 100,
        pages: 1,
      },
      data: undefined,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
  });

  afterAll(() => {
    if (originalRagEnabled === undefined) {
      delete process.env.NEXT_PUBLIC_RAG_ENABLED;
    } else {
      process.env.NEXT_PUBLIC_RAG_ENABLED = originalRagEnabled;
    }
  });

  test("hides material chat while preserving content generation", () => {
    mockSelectableMaterial();
    render(<AIWorkspacePage />);

    expect(screen.getByText("Content Studio")).toBeVisible();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Send material question/i })).not.toBeInTheDocument();
    expect(mockedOpenAiChatStream).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Source material"));
    expect(screen.getByRole("button", { name: /Generate Questions/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Generate Flashcards/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Generate Outline/i })).toBeVisible();
  });

  test("shows material chat by default when the presentation flag is unset", () => {
    delete process.env.NEXT_PUBLIC_RAG_ENABLED;
    mockSelectableMaterial();
    render(<AIWorkspacePage />);

    expect(screen.getByRole("textbox")).toBeVisible();
    expect(screen.getByText(/Select a material before starting material chat/i)).toBeVisible();
    fireEvent.click(screen.getByText("Source material"));
    const input = screen.getByPlaceholderText("Enter a material question...");
    const sendButton = screen.getByRole("button", { name: /Send material question/i });
    expect(input).toBeEnabled();
    expect(sendButton).toBeDisabled();
    fireEvent.change(input, { target: { value: "Summarize this material" } });
    expect(sendButton).toBeEnabled();
    expect(mockedOpenAiChatStream).not.toHaveBeenCalled();
  });

  test("reports a sanitized provider error event immediately", async () => {
    process.env.NEXT_PUBLIC_RAG_ENABLED = "true";
    mockSelectableMaterial();
    const bytes = new TextEncoder().encode(
      'data: {"error":"AI_PROVIDER_UNAVAILABLE",' +
        '"text":"canary provider detail"}\n\n' +
        'data: {"text":"canary content after failure"}\n\n',
    );
    const read = jest
      .fn()
      .mockResolvedValueOnce({ done: false, value: bytes })
      .mockResolvedValueOnce({ done: true, value: undefined });
    mockedOpenAiChatStream.mockResolvedValue({
      ok: true,
      body: { getReader: () => ({ read }) },
    } as unknown as Response);

    render(<AIWorkspacePage />);
    fireEvent.click(screen.getByText("Source material"));
    const input = screen.getByPlaceholderText("Enter a material question...");
    fireEvent.change(input, { target: { value: "Create a quiz" } });
    fireEvent.submit(input.closest("form") as HTMLFormElement);

    await waitFor(() =>
      expect(screen.getByText(/The AI service is currently unavailable/)).toBeVisible(),
    );
    expect(mockedOpenAiChatStream).toHaveBeenCalledTimes(1);
    expect(mockedOpenAiChatStream.mock.calls[0][1]).toBe("material-1");
    expect(document.body.textContent).not.toContain("canary");
  });

  test("requires a selected material before sending chat", () => {
    process.env.NEXT_PUBLIC_RAG_ENABLED = "true";
    render(<AIWorkspacePage />);

    const input = screen.getByRole("textbox");
    const form = input.closest("form") as HTMLFormElement;

    expect(
      screen.getByText(/Select a material before starting material chat/i),
    ).toBeVisible();
    expect(input).toBeDisabled();
    expect(form.querySelector('button[type="submit"]')).toBeDisabled();

    fireEvent.submit(form);

    expect(mockedOpenAiChatStream).not.toHaveBeenCalled();
  });

  test("localizes upload failures without exposing backend details", async () => {
    mockedUseTopics.mockReturnValue({
      topics: [{ id: "topic-1", name: "Topic" }] as never,
      pagination: {
        items: [{ id: "topic-1", name: "Topic" }] as never,
        total: 1,
        page: 1,
        size: 100,
        pages: 1,
      },
      data: undefined,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUploadMaterial.mockRejectedValue({
      response: {
        data: {
          error_code: "FILE_TOO_LARGE",
          details: { provider_output: "canary-provider-secret" },
          detail: "canary-backend-detail",
        },
      },
    });
    render(<AIWorkspacePage />);

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "topic-1" },
    });
    const fileInput = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    const file = new File(["source"], "source.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() =>
      expect(mockedToastAdd).toHaveBeenCalledWith({
        title: "Upload failed",
        description: "The selected file is too large.",
        type: "error",
      }),
    );
    expect(mockedUploadMaterial).toHaveBeenCalledWith(file, "topic-1");
    expect(JSON.stringify(mockedToastAdd.mock.calls)).not.toContain("canary");
  });

  test("localizes question-generation failures and clears the preview", async () => {
    mockSelectableMaterial();
    mockedGenerateQuestions.mockRejectedValue({
      response: {
        data: {
          error_code: "AI_PROVIDER_UNAVAILABLE",
          details: { raw_prompt: "canary-prompt" },
        },
      },
    });
    render(<AIWorkspacePage />);

    fireEvent.click(screen.getByText("Source material"));
    fireEvent.click(screen.getByRole("button", { name: /Generate Questions/i }));

    await waitFor(() =>
      expect(mockedToastAdd).toHaveBeenCalledWith({
        title: "Question generation failed",
        description: "The AI service is currently unavailable. Try again later.",
        type: "error",
      }),
    );
    expect(mockedGenerateQuestions).toHaveBeenCalledWith("material-1", 5);
    expect(JSON.stringify(mockedToastAdd.mock.calls)).not.toContain("canary");
  });

  test.each([
    {
      buttonName: /Generate Questions/i,
      service: () => mockedGenerateQuestions,
      result: { questions: [] },
    },
    {
      buttonName: /Generate Flashcards/i,
      service: () => mockedGenerateFlashcards,
      result: { flashcards: [] },
    },
    {
      buttonName: /Generate Outline/i,
      service: () => mockedGenerateTopicBrief,
      result: { content: "Brief" },
    },
  ])("coordinates a successful quick generation", async ({
    buttonName,
    service,
    result,
  }) => {
    mockSelectableMaterial();
    service().mockResolvedValue(result as never);
    render(<AIWorkspacePage />);

    fireEvent.click(screen.getByText("Source material"));
    fireEvent.click(screen.getByRole("button", { name: buttonName }));

    await waitFor(() => expect(service()).toHaveBeenCalled());
    expect(document.body.textContent).not.toContain("canary");
  });
});
