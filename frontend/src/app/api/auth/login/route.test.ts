/** @jest-environment node */

import { NextRequest } from "next/server";

import { POST } from "./route";

describe("login BFF error contract", () => {
  const originalBackendUrl = process.env.BACKEND_API_URL;

  afterEach(() => {
    process.env.BACKEND_API_URL = originalBackendUrl;
    jest.restoreAllMocks();
  });

  function csrfHeaders(requestId?: string) {
    return {
      "Content-Type": "application/json",
      Origin: "http://frontend.test",
      Cookie: "csrf_token=csrf-test-token",
      "X-CSRF-Token": "csrf-test-token",
      ...(requestId ? { "X-Request-ID": requestId } : {}),
    };
  }

  test("preserves a canonical backend failure and correlation headers", async () => {
    process.env.BACKEND_API_URL = "https://backend.example.test";
    const requestId = "8f37b4ca-2014-4cec-aa2d-3f967c27eb8e";
    jest.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error_code: "INVALID_CREDENTIALS",
          details: {},
          request_id: requestId,
          message: "canary raw backend message",
        }),
        {
          status: 401,
          headers: {
            "Content-Type": "application/json",
            "WWW-Authenticate": "Bearer",
            "X-Request-ID": requestId,
          },
        },
      ),
    );
    const request = new NextRequest("http://frontend.test/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: "teacher@example.test",
        password: "canary-password",
      }),
      headers: csrfHeaders(requestId),
    });

    const response = await POST(request);

    expect(response.status).toBe(401);
    expect(response.headers.get("X-Request-ID")).toBe(requestId);
    expect(response.headers.get("WWW-Authenticate")).toBe("Bearer");
    expect(jest.mocked(global.fetch).mock.calls[0][1]?.headers).toEqual(
      expect.objectContaining({ "X-Request-ID": requestId }),
    );
    await expect(response.json()).resolves.toEqual({
      error_code: "INVALID_CREDENTIALS",
      details: {},
      request_id: requestId,
    });
  });

  test("creates a canonical error without logging credentials", async () => {
    process.env.BACKEND_API_URL = "https://backend.example.test";
    jest
      .spyOn(global, "fetch")
      .mockRejectedValue(new Error("canary-password"));
    const consoleError = jest
      .spyOn(console, "error")
      .mockImplementation(() => undefined);
    const requestId = "7ed72743-18c3-44c6-a2fe-08dceacb8399";
    const request = new NextRequest("http://frontend.test/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: "teacher@example.test",
        password: "canary-password",
      }),
      headers: csrfHeaders(requestId),
    });

    const response = await POST(request);

    expect(response.status).toBe(500);
    expect(response.headers.get("X-Request-ID")).toBe(requestId);
    await expect(response.json()).resolves.toEqual({
      error_code: "INTERNAL_ERROR",
      details: {},
      request_id: requestId,
    });
    expect(JSON.stringify(consoleError.mock.calls)).not.toContain("canary");
  });

  test("generates and forwards one correlation ID when the caller omits it", async () => {
    process.env.BACKEND_API_URL = "https://backend.example.test";
    let forwardedRequestId: string | null = null;
    jest.spyOn(global, "fetch").mockImplementation(async (_input, init) => {
      forwardedRequestId = new Headers(init?.headers).get("X-Request-ID");
      return new Response(
        JSON.stringify({
          access_token: "backend-access-token-with-sufficient-length",
          refresh_token: "backend-refresh-token-with-sufficient-length-1234567890",
          access_expires_in: 900,
          refresh_expires_in: 604800,
          token_type: "bearer",
          user: {
            id: "teacher-1",
            email: "teacher@example.test",
            role: "teacher",
            full_name: null,
            is_active: true,
          },
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      );
    });
    const request = new NextRequest("http://frontend.test/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: "teacher@example.test",
        password: "test-password",
      }),
      headers: csrfHeaders(),
    });

    const response = await POST(request);
    const responseRequestId = response.headers.get("X-Request-ID");

    expect(response.status).toBe(200);
    expect(responseRequestId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
    );
    expect(forwardedRequestId).toBe(responseRequestId);
    await expect(response.json()).resolves.toEqual({
      user: {
        id: "teacher-1",
        email: "teacher@example.test",
        role: "teacher",
        full_name: null,
        is_active: true,
      },
    });
    const cookies = response.headers.getSetCookie().join(";");
    expect(cookies).toContain("access_token=backend-access-token");
    expect(cookies).toContain("refresh_token=backend-refresh-token");
    expect(cookies).not.toContain("role=");
  });

  test("rejects a login mutation without same-origin CSRF proof", async () => {
    const backendFetch = jest.spyOn(global, "fetch");
    const request = new NextRequest("http://frontend.test/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: "teacher@example.test",
        password: "test-password",
      }),
      headers: { "Content-Type": "application/json" },
    });

    const response = await POST(request);

    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error_code: "ORIGIN_NOT_ALLOWED" }),
    );
    expect(backendFetch).not.toHaveBeenCalled();
  });

  test("rejects malformed login input before contacting the backend", async () => {
    const backendFetch = jest.spyOn(global, "fetch");
    const request = new NextRequest("http://frontend.test/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: ["teacher@example.test"], password: 123 }),
      headers: csrfHeaders(),
    });

    const response = await POST(request);

    expect(response.status).toBe(422);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error_code: "VALIDATION_ERROR" }),
    );
    expect(backendFetch).not.toHaveBeenCalled();
  });
});
