import { getBackendUrl } from "./backend-url";

describe("getBackendUrl", () => {
  it("prefers the canonical server-only setting", () => {
    expect(
      getBackendUrl({
        BACKEND_API_URL: "https://backend.example.test/",
        NEXT_PUBLIC_API_URL: "https://legacy.example.test",
      }),
    ).toBe("https://backend.example.test");
  });

  it("keeps the legacy public-prefixed setting as a compatibility fallback", () => {
    expect(
      getBackendUrl({ NEXT_PUBLIC_API_URL: "http://legacy.example.test:8000" }),
    ).toBe("http://legacy.example.test:8000");
  });

  it("uses the local backend when no setting is supplied", () => {
    expect(getBackendUrl({})).toBe("http://127.0.0.1:8000");
  });

  it.each([
    "file:///tmp/backend",
    "https://user:password@example.test",
    "https://example.test/api",
  ])("rejects an unsafe backend URL: %s", (configuredUrl) => {
    expect(() => getBackendUrl({ BACKEND_API_URL: configuredUrl })).toThrow();
  });
});
