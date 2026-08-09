export type BackendErrorDetails = Record<string, unknown>;

export interface BackendErrorPayload {
  error_code: string;
  details: BackendErrorDetails;
  request_id: string | null;
}

export const UNKNOWN_ERROR_MESSAGE = "Something went wrong. Please try again.";

const REQUEST_ID_PATTERN =
  /^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-7][0-9A-HJKMNP-TV-Z]{25})$/i;

export const ERROR_MESSAGES: Readonly<Record<string, string>> = {
  // Authentication and users
  USER_ALREADY_EXISTS: "This email address is already in use.",
  INVALID_CREDENTIALS: "The email address or password is incorrect.",
  USER_NOT_FOUND: "The requested user could not be found.",
  INVALID_ROLE: "The selected role is invalid.",
  NOT_ENOUGH_PERMISSIONS: "You do not have permission to perform this action.",
  FORBIDDEN: "You do not have permission to perform this action.",
  UNAUTHORIZED: "Your session is missing, invalid, or expired.",
  INCORRECT_OLD_PASSWORD: "The current password is incorrect.",
  INVALID_OR_EXPIRED_TOKEN: "This link is invalid or has expired.",

  // Content and submissions
  RESOURCE_NOT_FOUND: "The requested resource could not be found.",
  TOPIC_NOT_FOUND: "The requested topic could not be found.",
  TOPIC_IN_USE: "This topic is still in use and cannot be deleted.",
  EXAM_NOT_FOUND: "The requested exam could not be found or is unavailable.",
  QUESTION_NOT_FOUND: "The requested question could not be found.",
  SUBMISSION_NOT_FOUND: "The requested submission could not be found.",
  MATERIAL_NOT_FOUND: "The requested material could not be found.",
  MATERIAL_DELETE_REQUIRES_CASCADE: "This material has linked resources.",
  DECK_NOT_FOUND: "The requested flashcard deck could not be found.",
  DECK_MISMATCH: "The flashcard does not belong to the selected deck.",
  ALREADY_SUBMITTED: "This exam has already been submitted.",
  NOT_STARTED_YET: "Start the exam before submitting it.",
  NOT_SUBMITTED: "This exam has not been submitted yet.",
  TIME_LIMIT_EXCEEDED: "The submission was received after the time limit.",

  // Files and validation
  VALIDATION_ERROR: "Some submitted fields are invalid. Check the form and try again.",
  INVALID_FILENAME: "The file name is invalid.",
  UNSUPPORTED_FILE_TYPE: "This file type is not supported.",
  INVALID_FILE_CONTENT_TYPE: "The file type does not match its declared format.",
  INVALID_FILE_CONTENT: "The file content is invalid or corrupted.",
  INVALID_IMAGE_FORMAT: "The image must be a valid PNG or JPEG file.",
  FILE_TOO_LARGE: "The selected file is too large.",
  NO_CHUNKS_FOUND: "No processed document content is available yet.",

  // AI and dependencies
  AI_PROVIDER_UNAVAILABLE: "The AI service is currently unavailable. Try again later.",
  AI_REQUEST_TIMEOUT: "The AI request timed out. Try again.",
  AI_OUTPUT_INVALID: "The AI returned an invalid response. Try again.",
  AI_CONTENT_REQUIRES_REVIEW: "This AI-generated content requires review before use.",
  AI_PARSE_ERROR: "The AI returned an invalid response. Try again.",
  AI_GENERATION_FAILED: "The AI could not generate the requested content.",
  AI_SERVICE_UNAVAILABLE: "The AI service is currently unavailable. Try again later.",
  AI_RATE_LIMIT_EXCEEDED: "The AI service is busy. Try again later.",
  AI_TIMEOUT: "The AI request timed out. Try again.",
  AI_AUTHENTICATION_FAILED: "The AI service is currently unavailable. Try again later.",
  AI_INTERNAL_ERROR: "The AI request could not be completed.",

  // Generic transport errors
  BAD_REQUEST: "The request is invalid.",
  METHOD_NOT_ALLOWED: "This action is not allowed for the requested resource.",
  RATE_LIMIT_EXCEEDED: "Too many requests were made. Try again later.",
  STATE_CONFLICT: "The resource is not in the required state for this action.",
  PROXY_ERROR: "The application could not reach the server. Try again later.",
  HTTP_ERROR: UNKNOWN_ERROR_MESSAGE,
  INTERNAL_ERROR: UNKNOWN_ERROR_MESSAGE,
  UNKNOWN_ERROR: UNKNOWN_ERROR_MESSAGE,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function unwrapResponseData(value: unknown): unknown {
  if (!isRecord(value)) return value;

  const response = value.response;
  if (isRecord(response) && "data" in response) {
    return response.data;
  }

  return value;
}

/**
 * Extract the canonical backend error fields from either a response body or an
 * Axios-style rejection. Legacy/malformed fields are normalized safely and raw
 * backend messages are deliberately ignored.
 */
export function parseBackendError(value: unknown): BackendErrorPayload | null {
  const candidate = unwrapResponseData(value);
  if (!isRecord(candidate) || typeof candidate.error_code !== "string") {
    return null;
  }

  const errorCode = candidate.error_code.trim();
  if (!/^[A-Z][A-Z0-9_]*$/.test(errorCode)) {
    return null;
  }

  return {
    error_code: errorCode,
    details: isRecord(candidate.details) ? candidate.details : {},
    request_id:
      typeof candidate.request_id === "string" &&
      REQUEST_ID_PATTERN.test(candidate.request_id)
        ? candidate.request_id
        : null,
  };
}

export function getErrorMessage(code: string | null | undefined): string {
  if (!code) return UNKNOWN_ERROR_MESSAGE;
  return ERROR_MESSAGES[code] ?? UNKNOWN_ERROR_MESSAGE;
}

/**
 * Return only an application-owned English message. Neither `message`,
 * `detail`, provider output, nor a native Error message is ever surfaced.
 */
export function getBackendErrorMessage(
  error: unknown,
  safeFallback: string = UNKNOWN_ERROR_MESSAGE,
): string {
  const backendError = parseBackendError(error);
  if (!backendError) return safeFallback;
  return getErrorMessage(backendError.error_code);
}

function safeLinkedCount(value: unknown): number | null {
  return Number.isSafeInteger(value) && (value as number) >= 0
    ? (value as number)
    : null;
}

export function getMaterialDeleteConfirmation(error: unknown): string {
  const fallback =
    "This material has linked resources. Delete it and all linked resources?";
  const linkedCounts = parseBackendError(error)?.details.linked_counts;
  if (!isRecord(linkedCounts)) return fallback;

  const questions = safeLinkedCount(linkedCounts.questions);
  const decks = safeLinkedCount(linkedCounts.flashcard_decks);
  const briefs = safeLinkedCount(linkedCounts.topic_briefs);
  if (questions === null || decks === null || briefs === null) return fallback;

  return (
    `This material is linked to ${questions} question(s), ${decks} ` +
    `flashcard deck(s), and ${briefs} topic brief(s). ` +
    "Delete it and all linked resources?"
  );
}

/** Log only stable, application-owned identifiers; never serialize the error. */
export function logBackendError(context: string, error: unknown): void {
  const backendError = parseBackendError(error);
  const errorCode = backendError?.error_code ?? "UNKNOWN_ERROR";
  const requestId = backendError?.request_id ?? "unavailable";
  const safeContext = /^[A-Za-z][A-Za-z0-9 ]{0,63}$/.test(context)
    ? context
    : "Frontend request failed";
  console.error(`${safeContext} error_code=${errorCode} request_id=${requestId}`);
}
