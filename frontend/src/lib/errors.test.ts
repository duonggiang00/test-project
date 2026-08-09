import {
  getBackendErrorMessage,
  getErrorMessage,
  getMaterialDeleteConfirmation,
  logBackendError,
  parseBackendError,
  UNKNOWN_ERROR_MESSAGE,
} from "./errors";

describe("canonical backend errors", () => {
  test("parses direct and Axios-shaped canonical payloads", () => {
    const payload = {
      error_code: "STATE_CONFLICT",
      details: { state: "published" },
      request_id: "8f37b4ca-2014-4cec-aa2d-3f967c27eb8e",
    };

    expect(parseBackendError(payload)).toEqual(payload);
    expect(parseBackendError({ response: { data: payload } })).toEqual(payload);
  });

  test("localizes known codes and uses a safe English fallback", () => {
    expect(getErrorMessage("NO_CHUNKS_FOUND")).toBe(
      "No processed document content is available yet.",
    );
    expect(getErrorMessage("UNRECOGNIZED_CODE")).toBe(UNKNOWN_ERROR_MESSAGE);
    expect(getBackendErrorMessage({
      error_code: "UNRECOGNIZED_CODE",
      details: {},
      request_id: "8f37b4ca-2014-4cec-aa2d-3f967c27eb8e",
    })).toBe(UNKNOWN_ERROR_MESSAGE);
  });

  test("never surfaces raw backend, provider, or native error messages", () => {
    const fallback = "The request could not be completed.";
    const malformedBackendError = {
      message: "canary backend secret",
      detail: "canary provider failure",
    };

    expect(getBackendErrorMessage(malformedBackendError, fallback)).toBe(fallback);
    expect(getBackendErrorMessage(new Error("canary native error"), fallback)).toBe(
      fallback,
    );
    expect(
      getBackendErrorMessage(
        {
          response: {
            data: {
              error_code: "not-a-canonical-code",
              message: "canary transport error",
            },
          },
        },
        fallback,
      ),
    ).toBe(fallback);
  });

  test("normalizes malformed optional fields without trusting them", () => {
    expect(
      parseBackendError({
        error_code: "VALIDATION_ERROR",
        details: "canary raw details",
        request_id: 123,
      }),
    ).toEqual({
      error_code: "VALIDATION_ERROR",
      details: {},
      request_id: null,
    });
  });

  test("formats only validated material link counts", () => {
    const error = {
      error_code: "MATERIAL_DELETE_REQUIRES_CASCADE",
      details: {
        linked_counts: {
          questions: 2,
          flashcard_decks: 1,
          topic_briefs: 0,
        },
      },
      request_id: "8f37b4ca-2014-4cec-aa2d-3f967c27eb8e",
    };

    expect(getMaterialDeleteConfirmation(error)).toContain(
      "2 question(s), 1 flashcard deck(s), and 0 topic brief(s)",
    );
    expect(
      getMaterialDeleteConfirmation({
        ...error,
        details: { linked_counts: { questions: "canary" } },
      }),
    ).toBe(
      "This material has linked resources. Delete it and all linked resources?",
    );
  });

  test("logs only a canonical code and request ID", () => {
    const consoleError = jest
      .spyOn(console, "error")
      .mockImplementation(() => undefined);

    logBackendError("Profile update failed", {
      response: {
        data: {
          error_code: "STATE_CONFLICT",
          details: {},
          request_id: "8f37b4ca-2014-4cec-aa2d-3f967c27eb8e",
        },
        config: { data: "canary-password" },
      },
    });

    expect(consoleError).toHaveBeenCalledWith(
      "Profile update failed error_code=STATE_CONFLICT " +
        "request_id=8f37b4ca-2014-4cec-aa2d-3f967c27eb8e",
    );
    expect(JSON.stringify(consoleError.mock.calls)).not.toContain("canary");
    consoleError.mockRestore();
  });
});
