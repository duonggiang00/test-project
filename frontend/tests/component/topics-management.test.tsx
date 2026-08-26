import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import TopicsPage from "@/app/(admin)/topics/page";
import { toast } from "@/components/ui/toast";
import { useConfirm } from "@/hooks/useConfirm";
import {
  createTopic,
  deleteTopic,
  updateTopic,
  useTopics,
} from "@/hooks/useTopics";

jest.mock("../../src/hooks/useTopics", () => ({
  createTopic: jest.fn(),
  deleteTopic: jest.fn(),
  updateTopic: jest.fn(),
  useTopics: jest.fn(),
}));

jest.mock("../../src/hooks/useConfirm", () => ({
  useConfirm: jest.fn(),
}));

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

jest.mock("../../src/lib/errors", () => ({
  logBackendError: jest.fn(),
}));

const mockedCreateTopic = jest.mocked(createTopic);
const mockedDeleteTopic = jest.mocked(deleteTopic);
const mockedUpdateTopic = jest.mocked(updateTopic);
const mockedUseConfirm = jest.mocked(useConfirm);
const mockedUseTopics = jest.mocked(useTopics);
const mockedToastAdd = jest.mocked(toast.add);
const mutate = jest.fn();
const confirm = jest.fn();

function topicState(overrides: Record<string, unknown> = {}) {
  return {
    topics: [{ id: "topic-1", name: "Biology", description: "Cells" }],
    pagination: {
      items: [],
      total: 21,
      page: 1,
      size: 10,
      pages: 3,
    },
    data: undefined,
    isLoading: false,
    isError: undefined,
    mutate,
    ...overrides,
  } as never;
}

describe("Topics management", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    confirm.mockResolvedValue(true);
    mockedUseConfirm.mockReturnValue({
      confirm,
      ConfirmDialog: () => <div data-testid="confirm-dialog" />,
    });
    mockedUseTopics.mockImplementation((params) => topicState({
      pagination: {
        items: [],
        total: 21,
        page: params?.page ?? 1,
        size: 10,
        pages: 3,
      },
    }));
  });

  test("searches, paginates, and performs create, update, and confirmed delete", async () => {
    mockedCreateTopic.mockResolvedValue({} as never);
    mockedUpdateTopic.mockResolvedValue({} as never);
    mockedDeleteTopic.mockResolvedValue(undefined as never);
    render(<TopicsPage />);

    fireEvent.change(screen.getByTestId("search-topic-input"), {
      target: { value: "biology" },
    });
    fireEvent.click(screen.getByTestId("search-topic-button"));
    expect(mockedUseTopics).toHaveBeenLastCalledWith({
      page: 1,
      size: 10,
      search: "biology",
    });

    fireEvent.click(screen.getByRole("button", { name: "NEXT" }));
    expect(mockedUseTopics).toHaveBeenLastCalledWith({
      page: 2,
      size: 10,
      search: "biology",
    });
    fireEvent.click(screen.getByRole("button", { name: "PREV" }));

    fireEvent.click(screen.getByTestId("add-topic-button"));
    fireEvent.change(screen.getByTestId("topic-name-input"), {
      target: { value: "Chemistry" },
    });
    fireEvent.change(screen.getByTestId("topic-description-input"), {
      target: { value: "Matter" },
    });
    fireEvent.click(screen.getByTestId("save-topic-button"));
    await waitFor(() => expect(mockedCreateTopic).toHaveBeenCalledWith({
      name: "Chemistry",
      description: "Matter",
    }));

    fireEvent.click(screen.getByTestId("edit-topic-button"));
    expect(screen.getByTestId("topic-name-input")).toHaveValue("Biology");
    fireEvent.change(screen.getByTestId("topic-description-input"), {
      target: { value: "Living cells" },
    });
    fireEvent.click(screen.getByTestId("save-topic-button"));
    await waitFor(() => expect(mockedUpdateTopic).toHaveBeenCalledWith(
      "topic-1",
      { name: "Biology", description: "Living cells" },
    ));

    fireEvent.click(screen.getByTestId("delete-topic-button"));
    await waitFor(() => expect(confirm).toHaveBeenCalledWith(
      "Are you sure you want to delete this topic?",
    ));
    expect(mockedDeleteTopic).toHaveBeenCalledWith("topic-1");
    expect(mutate).toHaveBeenCalledTimes(3);
  });

  test.each([
    ["loading", { isLoading: true }, null],
    ["error", { isError: new Error("network") }, "Error loading topics."],
    ["empty", { topics: [] }, "No topics found."],
  ])("renders the %s state", (_name, overrides, expected) => {
    mockedUseTopics.mockReturnValue(topicState(overrides));
    render(<TopicsPage />);
    if (expected) expect(screen.getByText(expected)).toBeVisible();
    else expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  test("reports save and delete failures without closing the workflow", async () => {
    mockedCreateTopic.mockRejectedValue(new Error("save failed"));
    mockedDeleteTopic.mockRejectedValue(new Error("delete failed"));
    render(<TopicsPage />);

    fireEvent.click(screen.getByTestId("add-topic-button"));
    fireEvent.change(screen.getByTestId("topic-name-input"), {
      target: { value: "Chemistry" },
    });
    fireEvent.click(screen.getByTestId("save-topic-button"));
    await waitFor(() => expect(mockedToastAdd).toHaveBeenCalledWith({
      title: "Error",
      description: "An error occurred",
      type: "error",
    }));

    fireEvent.click(screen.getByRole("button", { name: "CANCEL" }));
    fireEvent.click(screen.getByTestId("delete-topic-button"));
    await waitFor(() => expect(mockedToastAdd).toHaveBeenCalledWith({
      title: "Error",
      description: "Failed to delete topic",
      type: "error",
    }));
  });

  test("does not delete when confirmation is declined", async () => {
    confirm.mockResolvedValue(false);
    render(<TopicsPage />);
    fireEvent.click(screen.getByTestId("delete-topic-button"));
    await waitFor(() => expect(confirm).toHaveBeenCalled());
    expect(mockedDeleteTopic).not.toHaveBeenCalled();
  });
});
