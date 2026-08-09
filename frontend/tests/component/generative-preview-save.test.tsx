import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import GenerativePreview from "@/app/(admin)/ai-workspace/GenerativePreview";
import { toast } from "@/components/ui/toast";
import {
  saveGeneratedFlashcards,
  saveGeneratedQuestions,
  saveGeneratedTopicBrief,
} from "@/services/apiService";

jest.mock("../../src/services/apiService", () => ({
  saveGeneratedFlashcards: jest.fn(),
  saveGeneratedQuestions: jest.fn(),
  saveGeneratedTopicBrief: jest.fn(),
}));

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

const mockedSaveFlashcards = jest.mocked(saveGeneratedFlashcards);
const mockedSaveQuestions = jest.mocked(saveGeneratedQuestions);
const mockedSaveTopicBrief = jest.mocked(saveGeneratedTopicBrief);
const mockedToastAdd = jest.mocked(toast.add);

describe("generated content save coordination", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedSaveFlashcards.mockResolvedValue({});
    mockedSaveQuestions.mockResolvedValue({});
    mockedSaveTopicBrief.mockResolvedValue({});
  });

  test.each([
    {
      toolName: "draft_exam",
      toolArgs: { questions: [{ content: "Question" }] },
      expectedCall: () =>
        expect(mockedSaveQuestions).toHaveBeenCalledWith("material-1", [
          { content: "Question" },
        ]),
    },
    {
      toolName: "draft_flashcards",
      toolArgs: { flashcards: [{ term: "Term", definition: "Definition" }] },
      expectedCall: () =>
        expect(mockedSaveFlashcards).toHaveBeenCalledWith("material-1", [
          { term: "Term", definition: "Definition" },
        ]),
    },
    {
      toolName: "draft_topic_brief",
      toolArgs: { content: "Brief content" },
      expectedCall: () =>
        expect(mockedSaveTopicBrief).toHaveBeenCalledWith(
          "material-1",
          "Brief content",
        ),
    },
  ])("routes $toolName saves through its service", async ({
    toolName,
    toolArgs,
    expectedCall,
  }) => {
    render(
      <GenerativePreview
        toolName={toolName}
        toolArgs={toolArgs}
        isStreaming={false}
        materialId="material-1"
      />,
    );

    fireEvent.click(screen.getByRole("button"));

    await waitFor(expectedCall);
    expect(mockedToastAdd).toHaveBeenCalledWith(
      expect.objectContaining({ type: "success" }),
    );
  });

  test("shows only a localized stable error when saving fails", async () => {
    const consoleError = jest
      .spyOn(console, "error")
      .mockImplementation(() => undefined);
    mockedSaveQuestions.mockRejectedValue({
      response: {
        data: {
          error_code: "STATE_CONFLICT",
          details: { provider_output: "canary-provider-secret" },
          detail: "canary-backend-detail",
          request_id: "01936ZQX9X0W7AZ2MR4BTHN5J8",
        },
      },
    });

    render(
      <GenerativePreview
        toolName="draft_exam"
        toolArgs={{ questions: [] }}
        isStreaming={false}
        materialId="material-1"
      />,
    );
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() =>
      expect(mockedToastAdd).toHaveBeenCalledWith({
        title: "Save failed",
        description: "The resource is not in the required state for this action.",
        type: "error",
      }),
    );
    expect(consoleError).toHaveBeenCalledWith(
      "Generated content save failed error_code=STATE_CONFLICT request_id=01936ZQX9X0W7AZ2MR4BTHN5J8",
    );
    expect(JSON.stringify(mockedToastAdd.mock.calls)).not.toContain("canary");
    expect(JSON.stringify(consoleError.mock.calls)).not.toContain("canary");
    consoleError.mockRestore();
  });
});
