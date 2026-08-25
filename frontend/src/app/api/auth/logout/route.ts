import { NextRequest, NextResponse } from "next/server";

import { getBackendUrl } from "@/lib/backend-url";
import {
  clearAuthCookies,
  REFRESH_COOKIE,
  requestIdFor,
  validateBffMutation,
} from "@/lib/server-auth";
import { canonicalErrorResponse, REQUEST_ID_HEADER } from "@/lib/server-errors";

export async function POST(request: NextRequest) {
  const rejection = validateBffMutation(request);
  if (rejection) return rejection;
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  let backendRevoked = true;
  if (refreshToken) {
    try {
      const backendResponse = await fetch(`${getBackendUrl()}/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          [REQUEST_ID_HEADER]: requestIdFor(request),
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      backendRevoked = backendResponse.ok;
    } catch {
      backendRevoked = false;
    }
  }
  const res = backendRevoked
    ? NextResponse.json({ success: true })
    : canonicalErrorResponse({
        request,
        status: 502,
        errorCode: "LOGOUT_FAILED",
      });
  if (backendRevoked) clearAuthCookies(res);
  return res;
}
