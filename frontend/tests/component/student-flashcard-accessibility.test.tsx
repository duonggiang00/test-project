import { Suspense, useState } from "react";
import { act, fireEvent, render, screen, within } from "@testing-library/react";

import StudyDeckPage from "@/app/student/topics/[id]/decks/[deck_id]/study/page";
import BrutalistMatchingUI from "@/components/features/student/BrutalistMatchingUI";
import { useStudyCards } from "@/hooks/useFlashcards";

const push = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("../../src/hooks/useFlashcards", () => ({
  useStudyCards: jest.fn(),
  submitCardReview: jest.fn(),
}));

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

const mockedUseStudyCards = jest.mocked(useStudyCards);

describe("Student flashcard accessibility", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseStudyCards.mockReturnValue({
      cards: [
        {
          id: "card-1",
          deck_id: "deck-1",
          front_content: "Question",
          back_content: "Answer",
        },
      ],
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
  });

  test("uses a native button to reveal the card answer", async () => {
    const params = Promise.resolve({ id: "topic-1", deck_id: "deck-1" });
    await act(async () => {
      render(
        <Suspense fallback={<div>Loading</div>}>
          <StudyDeckPage params={params} />
        </Suspense>,
      );
      await params;
    });

    fireEvent.click(screen.getByRole("button", { name: "Reveal card answer" }));

    expect(screen.getByRole("button", { name: "Card answer revealed" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "[GOOD]" })).toBeVisible();
  });

  test("exposes both matching columns as pressed-state buttons", () => {
    const onChange = jest.fn();
    render(
      <BrutalistMatchingUI
        pairs={[{ left: "One", right: "Một" }]}
        currentMatches={[]}
        onChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Left option: One" }));
    fireEvent.click(screen.getByRole("button", { name: "Right option: Một" }));

    expect(onChange).toHaveBeenCalledWith([{ left: "One", right: "Một" }]);
  });

  test("renders safe matching metadata as equal-width vertical option groups", () => {
    const onChange = jest.fn();
    function MatchingHarness() {
      const [matches, setMatches] = useState<Array<{ left: string; right: string }>>([]);
      return (
        <BrutalistMatchingUI
          leftOptions={["Short", "A much longer left option"]}
          rightOptions={["Second", "First"]}
          currentMatches={matches}
          onChange={(nextMatches) => {
            onChange(nextMatches);
            setMatches(nextMatches);
          }}
        />
      );
    }

    render(
      <MatchingHarness />,
    );

    const leftGroup = screen.getByRole("group", { name: "Left options" });
    const rightGroup = screen.getByRole("group", { name: "Right options" });
    for (const option of [
      ...within(leftGroup).getAllByRole("button"),
      ...within(rightGroup).getAllByRole("button"),
    ]) {
      expect(option).toHaveClass("w-full");
      expect(option).toHaveClass("text-left");
    }

    fireEvent.click(screen.getByRole("button", { name: "Left option: Short" }));
    fireEvent.click(screen.getByRole("button", { name: "Right option: First" }));

    expect(onChange).toHaveBeenCalledWith([{ left: "Short", right: "First" }]);
    expect(screen.getByTestId("mobile-matching-summary")).toHaveTextContent(
      "Short→First",
    );
  });

  test("shows the correct pairs in the mobile result summary", () => {
    render(
      <BrutalistMatchingUI
        pairs={[
          { left: "One", right: "Một" },
          { left: "Two", right: "Hai" },
        ]}
        currentMatches={[{ left: "One", right: "Hai" }]}
        correctMatches={[
          { left: "One", right: "Một" },
          { left: "Two", right: "Hai" },
        ]}
        onChange={jest.fn()}
        readOnly
      />,
    );

    const summary = screen.getByTestId("mobile-matching-summary");
    expect(summary).toHaveTextContent("Matched pairs");
    expect(summary).toHaveTextContent("One→Hai");

    const correctMatches = screen.getByTestId("mobile-correct-matches");
    expect(correctMatches).toHaveTextContent("Correct answer");
    expect(correctMatches).toHaveTextContent("One→Một");
    expect(correctMatches).toHaveTextContent("Two→Hai");
  });
});
