/** @jest-environment node */

import { NextRequest } from "next/server";

import { POST } from "./route";

describe("login BFF error contract", () => {
  const originalBackendUrl = process.env.BACKEND_API_URL;

  afterEach(() => {
    process.env.BACKEND_API_URL = originalBackendUrl;
    jest.restoreAllMocks();
  });

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
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": requestId,
      },
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
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": requestId,
      },
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
          access_token: "backend-token",
          user: { id: "teacher-1", role: "teacher" },
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
      headers: { "Content-Type": "application/json" },
    });

    const response = await POST(request);
    const responseRequestId = response.headers.get("X-Request-ID");

    expect(response.status).toBe(200);
    expect(responseRequestId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
    );
    expect(forwardedRequestId).toBe(responseRequestId);
    await expect(response.json()).resolves.toEqual({
      user: { id: "teacher-1", role: "teacher" },
    });
  });
});
