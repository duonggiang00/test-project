import { NextRequest, NextResponse } from "next/server";

import {
  clearAuthCookies,
  REFRESH_COOKIE,
  refreshBackendSession,
  requestIdFor,
  setAuthCookies,
  validateBffMutation,
} from "@/lib/server-auth";
import { canonicalErrorResponse } from "@/lib/server-errors";

export async function POST(request: NextRequest) {
  const rejection = validateBffMutation(request);
  if (rejection) return rejection;
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) {
    return canonicalErrorResponse({
      request,
      status: 401,
      errorCode: "UNAUTHORIZED",
    });
  }
  try {
    const payload = await refreshBackendSession(
      refreshToken,
      requestIdFor(request),
    );
    const response = NextResponse.json({ user: payload.user });
    setAuthCookies(response, payload);
    return response;
  } catch {
    const response = canonicalErrorResponse({
      request,
      status: 401,
      errorCode: "UNAUTHORIZED",
    });
    clearAuthCookies(response);
    return response;
  }
}
