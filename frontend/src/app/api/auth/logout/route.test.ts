/** @jest-environment node */

import { NextRequest } from "next/server";

import { POST } from "./route";

function request(): NextRequest {
  return new NextRequest("http://frontend.test/api/auth/logout", {
    method: "POST",
    headers: {
      cookie: "refresh_token=refresh-secret; csrf_token=csrf-secret",
      origin: "http://frontend.test",
      "x-csrf-token": "csrf-secret",
    },
  });
}

describe("logout BFF", () => {
  afterEach(() => jest.restoreAllMocks());

  test("reports failed backend revocation and preserves credentials for retry", async () => {
    jest.spyOn(global, "fetch").mockResolvedValue(new Response(null, { status: 503 }));

    const response = await POST(request());

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error_code: "LOGOUT_FAILED" }),
    );
    expect(response.headers.getSetCookie()).toEqual([]);
  });

  test("clears local cookies after backend revocation succeeds", async () => {
    jest.spyOn(global, "fetch").mockResolvedValue(new Response(null, { status: 200 }));

    const response = await POST(request());

    expect(response.status).toBe(200);
    const cookies = response.headers.getSetCookie().join(";");
    expect(cookies).toContain("access_token=; Path=/; Expires=");
    expect(cookies).toContain("refresh_token=; Path=/; Expires=");
    expect(cookies).toContain("csrf_token=; Path=/; Expires=");
  });
});
