import { NextRequest, NextResponse } from "next/server";

import { getBackendUrl } from "@/lib/backend-url";
import {
  ACCESS_COOKIE,
  clearAuthCookies,
  REFRESH_COOKIE,
  refreshBackendSession,
  requestIdFor,
  validateBffMutation,
} from "@/lib/server-auth";
import { canonicalErrorResponse, REQUEST_ID_HEADER } from "@/lib/server-errors";

export async function POST(request: NextRequest) {
  const rejection = validateBffMutation(request);
  if (rejection) return rejection;
  let accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  let backendRevoked = true;
  const revoke = (token: string) =>
    fetch(`${getBackendUrl()}/auth/logout-all`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        [REQUEST_ID_HEADER]: requestIdFor(request),
      },
    });
  try {
    if (!accessToken && refreshToken) {
      accessToken = (
        await refreshBackendSession(refreshToken, requestIdFor(request))
      ).access_token;
    }
    if (accessToken) {
      let backendResponse = await revoke(accessToken);
      if (backendResponse.status === 401 && refreshToken) {
        const refreshed = await refreshBackendSession(
          refreshToken,
          requestIdFor(request),
        );
        backendResponse = await revoke(refreshed.access_token);
      }
      backendRevoked = backendResponse.ok;
    }
  } catch {
    backendRevoked = false;
  }
  const response = backendRevoked
    ? NextResponse.json({ success: true })
    : canonicalErrorResponse({
        request,
        status: 502,
        errorCode: "LOGOUT_FAILED",
      });
  if (backendRevoked) clearAuthCookies(response);
  return response;
}
