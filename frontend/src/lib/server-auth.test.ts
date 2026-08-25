/** @jest-environment node */

import { NextRequest, NextResponse } from "next/server";

import {
  clearAuthCookies,
  parseBackendTokenPayload,
  refreshBackendSession,
  setAuthCookies,
  validateBffMutation,
} from "./server-auth";

const TOKEN_PAYLOAD = {
  access_token: "access-token-with-sufficient-length",
  refresh_token: "refresh-token-with-sufficient-length-1234567890",
  access_expires_in: 900,
  refresh_expires_in: 604800,
  token_type: "bearer" as const,
  user: {
    id: "user-1",
    email: "student@example.test",
    role: "student",
    full_name: null,
    is_active: true,
  },
};

describe("BFF session security", () => {
  const originalBackendUrl = process.env.BACKEND_API_URL;

  afterEach(() => {
    process.env.BACKEND_API_URL = originalBackendUrl;
    jest.restoreAllMocks();
  });

  test("requires same-origin matching CSRF values", async () => {
    const accepted = new NextRequest("http://frontend.test/api/proxy/exams", {
      method: "POST",
      headers: {
        cookie: "csrf_token=csrf-token",
        origin: "http://frontend.test",
        "x-csrf-token": "csrf-token",
      },
    });
    expect(validateBffMutation(accepted)).toBeNull();

    const mismatched = new NextRequest("http://frontend.test/api/proxy/exams", {
      method: "POST",
      headers: {
        cookie: "csrf_token=csrf-token",
        origin: "http://frontend.test",
        "x-csrf-token": "different-token",
      },
    });
    const rejected = validateBffMutation(mismatched);
    expect(rejected?.status).toBe(403);
    await expect(rejected?.json()).resolves.toEqual(
      expect.objectContaining({ error_code: "CSRF_TOKEN_INVALID" }),
    );
  });

  test("uses the public Host header when Next has an internal request URL", () => {
    const request = new NextRequest("http://localhost:3000/api/auth/login", {
      method: "POST",
      headers: {
        cookie: "csrf_token=csrf-token",
        host: "127.0.0.1:3101",
        origin: "http://127.0.0.1:3101",
        "x-csrf-token": "csrf-token",
      },
    });

    expect(validateBffMutation(request)).toBeNull();
  });

  test("sets only HttpOnly token cookies and clears every session cookie", () => {
    const response = NextResponse.json({ ok: true });
    setAuthCookies(response, TOKEN_PAYLOAD);
    const setCookies = response.headers.getSetCookie().join(";");
    expect(setCookies).toContain("access_token=");
    expect(setCookies).toContain("refresh_token=");
    expect(setCookies).toContain("HttpOnly");
    expect(setCookies).not.toContain("role=");

    const cleared = NextResponse.json({ ok: true });
    clearAuthCookies(cleared);
    const clearedCookies = cleared.headers.getSetCookie().join(";");
    expect(clearedCookies).toContain("access_token=; Path=/; Expires=");
    expect(clearedCookies).toContain("refresh_token=; Path=/; Expires=");
    expect(clearedCookies).toContain("csrf_token=; Path=/; Expires=");
  });

  test("coalesces concurrent refresh calls for the same secret", async () => {
    process.env.BACKEND_API_URL = "https://backend.example.test";
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const backendFetch = jest.spyOn(global, "fetch").mockImplementation(async () => {
      await gate;
      return new Response(JSON.stringify(TOKEN_PAYLOAD), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });

    const first = refreshBackendSession("same-refresh-secret", "request-1");
    const second = refreshBackendSession("same-refresh-secret", "request-2");
    release?.();
    const [firstPayload, secondPayload] = await Promise.all([first, second]);

    expect(firstPayload).toEqual(TOKEN_PAYLOAD);
    expect(secondPayload).toEqual(TOKEN_PAYLOAD);
    expect(backendFetch).toHaveBeenCalledTimes(1);
  });

  test("rejects malformed or overlong token contracts", () => {
    expect(parseBackendTokenPayload(TOKEN_PAYLOAD)).toEqual(TOKEN_PAYLOAD);
    expect(
      parseBackendTokenPayload({ ...TOKEN_PAYLOAD, access_expires_in: 999999 }),
    ).toBeNull();
    expect(
      parseBackendTokenPayload({ ...TOKEN_PAYLOAD, refresh_token: "short" }),
    ).toBeNull();
    expect(
      parseBackendTokenPayload({
        ...TOKEN_PAYLOAD,
        user: { ...TOKEN_PAYLOAD.user, role: "owner" },
      }),
    ).toBeNull();
    expect(
      parseBackendTokenPayload({
        ...TOKEN_PAYLOAD,
        user: { ...TOKEN_PAYLOAD.user, is_active: "true" },
      }),
    ).toBeNull();
  });
});
