import { randomUUID } from "node:crypto";

import { NextRequest, NextResponse } from "next/server";

import {
  type BackendErrorDetails,
  parseBackendError,
} from "@/lib/errors";

export const REQUEST_ID_HEADER = "X-Request-ID";

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ULID_PATTERN = /^[0-7][0-9A-HJKMNP-TV-Z]{25}$/i;
const ALLOW_PATTERN = /^[A-Z]+(?:,\s*[A-Z]+)*$/;
const RETRY_AFTER_PATTERN = /^[0-9]{1,10}$/;
const WWW_AUTHENTICATE_PATTERN =
  /^Bearer(?: realm="[A-Za-z0-9 ._-]{1,64}")?$/;

export function canonicalizeRequestId(value: string | null): string | null {
  const candidate = value?.trim();
  if (!candidate) return null;
  if (UUID_PATTERN.test(candidate)) return candidate.toLowerCase();
  if (ULID_PATTERN.test(candidate)) return candidate.toUpperCase();
  return null;
}

export function getOrCreateRequestId(request: NextRequest): string {
  return (
    canonicalizeRequestId(request.headers.get(REQUEST_ID_HEADER)) ?? randomUUID()
  );
}

function safeProtocolHeaders(source?: Headers): Headers {
  const headers = new Headers();
  const allow = source?.get("Allow");
  const retryAfter = source?.get("Retry-After");
  const challenge = source?.get("WWW-Authenticate");
  if (allow && ALLOW_PATTERN.test(allow)) headers.set("Allow", allow);
  if (retryAfter && RETRY_AFTER_PATTERN.test(retryAfter)) {
    headers.set("Retry-After", retryAfter);
  }
  if (challenge && WWW_AUTHENTICATE_PATTERN.test(challenge)) {
    headers.set("WWW-Authenticate", challenge);
  }
  return headers;
}

interface CanonicalErrorOptions {
  request: NextRequest;
  status: number;
  errorCode: string;
  details?: BackendErrorDetails;
  upstreamRequestId?: string | null;
  upstreamHeaders?: Headers;
}

export function canonicalErrorResponse({
  request,
  status,
  errorCode,
  details = {},
  upstreamRequestId,
  upstreamHeaders,
}: CanonicalErrorOptions): NextResponse {
  const requestId =
    canonicalizeRequestId(upstreamRequestId ?? null) ??
    getOrCreateRequestId(request);
  const headers = safeProtocolHeaders(upstreamHeaders);
  headers.set(REQUEST_ID_HEADER, requestId);
  return NextResponse.json(
    {
      error_code: errorCode,
      details,
      request_id: requestId,
    },
    { status, headers },
  );
}

export function forwardBackendError(
  request: NextRequest,
  backendResponse: Response,
  body: unknown,
  fallbackRequestId?: string,
): NextResponse {
  const parsed = parseBackendError(body);
  return canonicalErrorResponse({
    request,
    status: backendResponse.status,
    errorCode: parsed?.error_code ?? "HTTP_ERROR",
    details: parsed?.details ?? {},
    upstreamRequestId:
      canonicalizeRequestId(
        backendResponse.headers.get(REQUEST_ID_HEADER),
      ) ??
      canonicalizeRequestId(parsed?.request_id ?? null) ??
      canonicalizeRequestId(fallbackRequestId ?? null),
    upstreamHeaders: backendResponse.headers,
  });
}
