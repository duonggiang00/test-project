import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { getBackendUrl } from '@/lib/backend-url';
import {
  canonicalErrorResponse,
  canonicalizeRequestId,
  forwardBackendError,
  getOrCreateRequestId,
  REQUEST_ID_HEADER,
} from '@/lib/server-errors';
import {
  parseBackendTokenPayload,
  setAuthCookies,
  setCsrfCookie,
  newCsrfToken,
  validateBffMutation,
} from '@/lib/server-auth';

export async function POST(request: NextRequest) {
  const rejection = validateBffMutation(request);
  if (rejection) return rejection;
  const requestId = getOrCreateRequestId(request);
  try {
    const body: unknown = await request.json();
    if (typeof body !== "object" || body === null || Array.isArray(body)) {
      return canonicalErrorResponse({
        request,
        status: 422,
        errorCode: "VALIDATION_ERROR",
      });
    }
    const { email, password, rememberMe } = body as Record<string, unknown>;
    if (
      typeof email !== "string" ||
      typeof password !== "string" ||
      (rememberMe !== undefined && typeof rememberMe !== "boolean")
    ) {
      return canonicalErrorResponse({
        request,
        status: 422,
        errorCode: "VALIDATION_ERROR",
      });
    }

    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);
    formData.append("remember_me", rememberMe ? "true" : "false");

    const apiUrl = getBackendUrl();
    
    const response = await fetch(`${apiUrl}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        [REQUEST_ID_HEADER]: requestId,
      },
      body: formData.toString(),
    });

    const data: unknown = await response.json();

    if (!response.ok) {
      return forwardBackendError(request, response, data, requestId);
    }

    const tokens = parseBackendTokenPayload(data);
    if (!tokens) {
      return canonicalErrorResponse({
        request,
        status: 502,
        errorCode: "AUTH_RESPONSE_INVALID",
        upstreamRequestId: response.headers.get(REQUEST_ID_HEADER),
      });
    }

    const res = NextResponse.json({ user: tokens.user });
    const backendRequestId = canonicalizeRequestId(
      response.headers.get(REQUEST_ID_HEADER),
    ) ?? requestId;
    res.headers.set(REQUEST_ID_HEADER, backendRequestId);
    
    setAuthCookies(res, tokens);
    setCsrfCookie(res, newCsrfToken());

    return res;
  } catch {
    const response = canonicalErrorResponse({
      request,
      status: 500,
      errorCode: "INTERNAL_ERROR",
      upstreamRequestId: requestId,
    });
    console.error(
      `Login route failed request_id=${response.headers.get(REQUEST_ID_HEADER)}`,
    );
    return response;
  }
}
