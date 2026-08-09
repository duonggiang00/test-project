import type { ReactNode } from "react";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import TopicDetailPage from "@/app/(admin)/topics/[id]/page";
import { toast } from "@/components/ui/toast";
import { useExams } from "@/hooks/useExams";
import { useTopicDecks } from "@/hooks/useFlashcards";
import { useMaterials } from "@/hooks/useMaterials";
import { useTopicDetail } from "@/hooks/useTopics";
import { deleteMaterial } from "@/services/apiService";

const push = jest.fn();
const confirm = jest.fn<Promise<boolean>, [string]>();
const mutateMaterials = jest.fn();

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "topic-1" }),
  useRouter: () => ({ push }),
}));

jest.mock("../../src/hooks/useTopics", () => ({
  useTopicDetail: jest.fn(),
  updateTopic: jest.fn(),
}));

jest.mock("../../src/hooks/useFlashcards", () => ({
  useTopicDecks: jest.fn(),
  updateTopicBrief: jest.fn(),
  generateTopicKitAi: jest.fn(),
  createDeck: jest.fn(),
}));

jest.mock("../../src/hooks/useExams", () => ({
  useExams: jest.fn(),
}));

jest.mock("../../src/hooks/useMaterials", () => ({
  useMaterials: jest.fn(),
}));

jest.mock("../../src/services/apiService", () => ({
  deleteMaterial: jest.fn(),
}));

jest.mock("../../src/hooks/useConfirm", () => ({
  useConfirm: () => ({
    confirm,
    ConfirmDialog: () => null,
  }),
}));

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

jest.mock("../../src/components/ui/tabs", () => ({
  Tabs: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsList: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsTrigger: ({ children }: { children: ReactNode }) => (
    <button type="button">{children}</button>
  ),
  TabsContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

const mockedUseTopicDetail = jest.mocked(useTopicDetail);
const mockedUseTopicDecks = jest.mocked(useTopicDecks);
const mockedUseExams = jest.mocked(useExams);
const mockedUseMaterials = jest.mocked(useMaterials);
const mockedDeleteMaterial = jest.mocked(deleteMaterial);
const mockedToast = jest.mocked(toast.add);

const conflict = {
  response: {
    data: {
      error_code: "MATERIAL_DELETE_REQUIRES_CASCADE",
      details: {
        linked_counts: {
          questions: 2,
          flashcard_decks: 1,
          topic_briefs: 0,
        },
        require_cascade: true,
      },
      request_id: "8f37b4ca-2014-4cec-aa2d-3f967c27eb8e",
      detail: "canary raw cascade message",
    },
  },
};

describe("topic material cascade deletion", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseTopicDetail.mockReturnValue({
      topic: {
        id: "topic-1",
        name: "Contracts",
        description: "",
        brief_content: "",
      } as never,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUseTopicDecks.mockReturnValue({
      decks: [],
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUseExams.mockReturnValue({
      exams: [],
      pagination: {} as never,
      data: undefined,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUseMaterials.mockReturnValue({
      materials: [
        {
          id: "material-1",
          title: "Source material",
          ai_status: "completed",
        } as never,
      ],
      isLoading: false,
      isError: undefined,
      mutate: mutateMaterials,
    });
  });

  test("shows reviewed counts and cancels without a cascade call", async () => {
    mockedDeleteMaterial.mockRejectedValueOnce(conflict);
    confirm.mockResolvedValueOnce(false);

    render(<TopicDetailPage />);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(confirm).toHaveBeenCalledTimes(1));
    expect(confirm.mock.calls[0][0]).toContain(
      "2 question(s), 1 flashcard deck(s), and 0 topic brief(s)",
    );
    expect(mockedDeleteMaterial).toHaveBeenCalledTimes(1);
    expect(mutateMaterials).not.toHaveBeenCalled();
    expect(JSON.stringify(confirm.mock.calls)).not.toContain("canary");
  });

  test("retries with cascade only after confirmation", async () => {
    mockedDeleteMaterial
      .mockRejectedValueOnce(conflict)
      .mockResolvedValueOnce(undefined);
    confirm.mockResolvedValueOnce(true);

    render(<TopicDetailPage />);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(mockedDeleteMaterial).toHaveBeenCalledTimes(2));
    expect(mockedDeleteMaterial.mock.calls).toEqual([
      ["material-1"],
      ["material-1", true],
    ]);
    expect(mutateMaterials).toHaveBeenCalledTimes(1);
    expect(mockedToast).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Material deleted" }),
    );
  });

  test("localizes a failed cascade retry without raw text", async () => {
    mockedDeleteMaterial
      .mockRejectedValueOnce(conflict)
      .mockRejectedValueOnce({
        response: {
          data: {
            error_code: "STATE_CONFLICT",
            details: {},
            request_id: "7ed72743-18c3-44c6-a2fe-08dceacb8399",
            detail: "canary retry detail",
          },
        },
      });
    confirm.mockResolvedValueOnce(true);

    render(<TopicDetailPage />);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() =>
      expect(mockedToast).toHaveBeenCalledWith({
        title: "Delete failed",
        description: "The resource is not in the required state for this action.",
        type: "error",
      }),
    );
    expect(JSON.stringify(mockedToast.mock.calls)).not.toContain("canary");
  });
});
