import { createHash, randomBytes, timingSafeEqual } from "node:crypto";

import { NextRequest, NextResponse } from "next/server";

import { getBackendUrl } from "@/lib/backend-url";
export {
  ACCESS_COOKIE,
  CSRF_COOKIE,
  CSRF_HEADER,
  REFRESH_COOKIE,
} from "@/lib/auth-contract";
import {
  ACCESS_COOKIE,
  CSRF_COOKIE,
  CSRF_HEADER,
  REFRESH_COOKIE,
} from "@/lib/auth-contract";
import {
  canonicalErrorResponse,
  getOrCreateRequestId,
  REQUEST_ID_HEADER,
} from "@/lib/server-errors";

const MAX_ACCESS_SECONDS = 60 * 60;
const MAX_REFRESH_SECONDS = 31 * 24 * 60 * 60;
const refreshFlights = new Map<string, Promise<BackendTokenPayload>>();

export interface BackendTokenPayload {
  access_token: string;
  refresh_token: string;
  access_expires_in: number;
  refresh_expires_in: number;
  token_type: "bearer";
  user: {
    id: string;
    email: string;
    role: "admin" | "teacher" | "student";
    full_name: string | null;
    is_active: boolean;
  };
}

function isPositiveInteger(value: unknown, maximum: number): value is number {
  return Number.isInteger(value) && Number(value) > 0 && Number(value) <= maximum;
}

export function parseBackendTokenPayload(value: unknown): BackendTokenPayload | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const payload = value as Record<string, unknown>;
  const user = payload.user as Record<string, unknown> | null;
  if (
    typeof payload.access_token !== "string" ||
    payload.access_token.length < 16 ||
    typeof payload.refresh_token !== "string" ||
    payload.refresh_token.length < 32 ||
    payload.token_type !== "bearer" ||
    !isPositiveInteger(payload.access_expires_in, MAX_ACCESS_SECONDS) ||
    !isPositiveInteger(payload.refresh_expires_in, MAX_REFRESH_SECONDS) ||
    typeof payload.user !== "object" ||
    payload.user === null ||
    Array.isArray(payload.user) ||
    typeof user?.id !== "string" ||
    typeof user.email !== "string" ||
    !["admin", "teacher", "student"].includes(String(user.role)) ||
    (user.full_name !== null && typeof user.full_name !== "string") ||
    typeof user.is_active !== "boolean"
  ) {
    return null;
  }
  return payload as unknown as BackendTokenPayload;
}

export function newCsrfToken(): string {
  return randomBytes(32).toString("base64url");
}

function equalSecret(left: string, right: string): boolean {
  const leftBytes = Buffer.from(left);
  const rightBytes = Buffer.from(right);
  return (
    leftBytes.length === rightBytes.length &&
    timingSafeEqual(leftBytes, rightBytes)
  );
}

export function validateBffMutation(request: NextRequest): NextResponse | null {
  const origin = request.headers.get("origin");
  let sameOrigin = false;
  if (origin) {
    try {
      const parsedOrigin = new URL(origin);
      const requestHost = request.headers.get("host") ?? request.nextUrl.host;
      sameOrigin =
        parsedOrigin.protocol === request.nextUrl.protocol &&
        parsedOrigin.host === requestHost;
    } catch {
      sameOrigin = false;
    }
  }
  if (!sameOrigin) {
    return canonicalErrorResponse({
      request,
      status: 403,
      errorCode: "ORIGIN_NOT_ALLOWED",
    });
  }
  const cookieToken = request.cookies.get(CSRF_COOKIE)?.value ?? "";
  const headerToken = request.headers.get(CSRF_HEADER) ?? "";
  if (!cookieToken || !headerToken || !equalSecret(cookieToken, headerToken)) {
    return canonicalErrorResponse({
      request,
      status: 403,
      errorCode: "CSRF_TOKEN_INVALID",
    });
  }
  return null;
}

export function setCsrfCookie(response: NextResponse, token: string): void {
  response.cookies.set({
    name: CSRF_COOKIE,
    value: token,
    httpOnly: false,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: MAX_REFRESH_SECONDS,
  });
}

export function setAuthCookies(
  response: NextResponse,
  payload: BackendTokenPayload,
): void {
  const common = {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    priority: "high" as const,
  };
  response.cookies.set({
    name: ACCESS_COOKIE,
    value: payload.access_token,
    ...common,
    maxAge: payload.access_expires_in,
  });
  response.cookies.set({
    name: REFRESH_COOKIE,
    value: payload.refresh_token,
    ...common,
    maxAge: payload.refresh_expires_in,
  });
}

export function clearAuthCookies(response: NextResponse): void {
  for (const name of [ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE]) {
    response.cookies.set({
      name,
      value: "",
      httpOnly: name !== CSRF_COOKIE,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      expires: new Date(0),
    });
  }
}

async function requestRefresh(
  refreshToken: string,
  requestId: string,
): Promise<BackendTokenPayload> {
  const response = await fetch(`${getBackendUrl()}/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      [REQUEST_ID_HEADER]: requestId,
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  const body: unknown = await response.json().catch(() => null);
  const payload = response.ok ? parseBackendTokenPayload(body) : null;
  if (!payload) throw new Error("REFRESH_FAILED");
  return payload;
}

export function refreshBackendSession(
  refreshToken: string,
  requestId: string,
): Promise<BackendTokenPayload> {
  const key = createHash("sha256").update(refreshToken).digest("hex");
  const existing = refreshFlights.get(key);
  if (existing) return existing;

  const pending = requestRefresh(refreshToken, requestId).finally(() => {
    refreshFlights.delete(key);
  });
  refreshFlights.set(key, pending);
  return pending;
}

export function requestIdFor(request: NextRequest): string {
  return getOrCreateRequestId(request);
}
