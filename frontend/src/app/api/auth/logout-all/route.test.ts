/** @jest-environment node */

import { NextRequest } from "next/server";

import { POST } from "./route";

describe("logout-all BFF", () => {
  afterEach(() => jest.restoreAllMocks());

  test("reports failed backend revocation and preserves credentials for retry", async () => {
    jest.spyOn(global, "fetch").mockResolvedValue(new Response(null, { status: 503 }));
    const request = new NextRequest("http://frontend.test/api/auth/logout-all", {
      method: "POST",
      headers: {
        cookie: "access_token=access-secret; csrf_token=csrf-secret",
        origin: "http://frontend.test",
        "x-csrf-token": "csrf-secret",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error_code: "LOGOUT_FAILED" }),
    );
    expect(response.headers.getSetCookie()).toEqual([]);
  });
});
